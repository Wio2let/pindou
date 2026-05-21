"""Post query API endpoints."""

import json
import logging
import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, delete

from app.models.database import get_db, async_session
from app.models.post import Post
from app.models.comment import Comment
from app.models.task import MonitorTask
from app.utils.schemas import PostResponse, PostDetailResponse
from app.adapters.cdp_manager import CDPManager
from app.adapters.mediacrawler import MediaCrawlerAdapter
from app.analysis.scorer import CommentAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["posts"])


@router.get("/tasks/{task_id}/posts", response_model=List[PostResponse])
async def list_posts(
    task_id: int,
    sort: str = Query("crawled", pattern=r"^(crawled|likes|comments|collected|created)$"),
    min_likes: int = Query(0, ge=0),
    min_comments: int = Query(0, ge=0),
    min_collected: int = Query(0, ge=0),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    order_map = {
        "crawled": Post.crawled_at,
        "likes": Post.liked_count,
        "comments": Post.comment_count,
        "collected": Post.collected_count,
        "created": Post.created_at,
    }
    order_col = order_map.get(sort, Post.crawled_at)

    stmt = select(Post).where(Post.task_id == task_id)
    if min_likes:
        stmt = stmt.where(Post.liked_count >= min_likes)
    if min_comments:
        stmt = stmt.where(Post.comment_count >= min_comments)
    if min_collected:
        stmt = stmt.where(Post.collected_count >= min_collected)

    result = await db.execute(
        stmt.order_by(desc(order_col))
            .offset((page - 1) * per_page)
            .limit(per_page)
    )
    return result.scalars().all()


@router.get("/posts/{note_id}", response_model=PostDetailResponse)
async def get_post_detail(note_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).where(Post.note_id == note_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Aggregate comment stats
    useful_count = await db.execute(
        select(func.count(Comment.id)).where(
            Comment.note_id == note_id, Comment.usefulness_score >= 0.4
        )
    )
    avg_score = await db.execute(
        select(func.avg(Comment.usefulness_score)).where(Comment.note_id == note_id)
    )

    post_data = PostDetailResponse.model_validate(post)
    post_data.useful_comment_count = useful_count.scalar() or 0
    post_data.avg_usefulness = round(float(avg_score.scalar() or 0.0), 2)
    return post_data


@router.post("/posts/{note_id}/refresh-images")
async def refresh_post_images(note_id: str, db: AsyncSession = Depends(get_db)):
    """Live-fetch the note detail and update image_urls in DB.

    Used when the saved post has empty image_urls (older crawls or notes that
    XHS hides behind the QR-code wall).
    """
    result = await db.execute(select(Post).where(Post.note_id == note_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.xsec_token:
        raise HTTPException(
            status_code=409,
            detail="该帖子没有 xsec_token，无法刷新；重新跑一次任务即可",
        )

    cdp = CDPManager()
    crawler = MediaCrawlerAdapter()
    try:
        context = await cdp.connect()
        await crawler.initialize(context)
        if not await crawler.ensure_logged_in():
            raise HTTPException(
                status_code=503,
                detail="CDP Chrome 未登录小红书，先扫码登录再试",
            )
        detail = await crawler.get_post_detail(
            note_id=note_id,
            xsec_token=post.xsec_token,
            xsec_source=post.xsec_source or "pc_search",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("refresh_post_images failed")
        raise HTTPException(status_code=502, detail=f"刷新失败: {e}")
    finally:
        try: await crawler.close()
        except Exception: pass
        try: await cdp.disconnect()
        except Exception: pass

    if not detail:
        raise HTTPException(status_code=404, detail="未抓到笔记详情，可能已被删除或屏蔽")

    image_urls_json = detail.get("image_urls", "[]") or "[]"
    # Persist
    async with async_session() as s:
        p = (await s.execute(select(Post).where(Post.note_id == note_id))).scalar_one_or_none()
        if p:
            if image_urls_json and image_urls_json != "[]":
                p.image_urls = image_urls_json
            # Backfill title/desc/video_url if they were empty
            if not p.title and detail.get("title"):
                p.title = detail["title"]
            if not p.desc and detail.get("desc"):
                p.desc = detail["desc"]
            if detail.get("video_url"):
                p.video_url = detail["video_url"]
            await s.commit()

    try:
        images = json.loads(image_urls_json)
    except Exception:
        images = []
    return {"note_id": note_id, "images": images, "count": len(images)}


@router.post("/posts/{note_id}/refresh-comments")
async def refresh_post_comments(
    note_id: str,
    max_count: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Live-fetch comments for a single post and append to DB.

    Mirrors the orchestrator's per-post comment logic — but for one specific
    post the user picked, instead of the first 3 per keyword.
    """
    result = await db.execute(select(Post).where(Post.note_id == note_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.xsec_token:
        raise HTTPException(
            status_code=409,
            detail="该帖子缺 xsec_token，无法抓评论；重新跑一次任务即可",
        )

    task_result = await db.execute(
        select(MonitorTask).where(MonitorTask.id == post.task_id)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="关联任务不存在")

    comment_keywords = [
        k.strip() for k in (task.comment_keywords or "").split(",") if k.strip()
    ]
    fetch_cap = min(max_count, task.max_comments_per_post or max_count)

    cdp = CDPManager()
    crawler = MediaCrawlerAdapter()
    try:
        context = await cdp.connect()
        await crawler.initialize(context)
        if not await crawler.ensure_logged_in():
            raise HTTPException(
                status_code=503,
                detail="CDP Chrome 未登录小红书，先扫码登录再试",
            )
        comments = await crawler.get_comments(
            note_id=note_id,
            xsec_token=post.xsec_token,
            xsec_source=post.xsec_source or "pc_search",
            max_count=fetch_cap,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("refresh_post_comments failed")
        raise HTTPException(status_code=502, detail=f"抓评论失败: {e}")
    finally:
        try: await crawler.close()
        except Exception: pass
        try: await cdp.disconnect()
        except Exception: pass

    if not comments:
        return {"note_id": note_id, "fetched": 0, "saved": 0}

    analyzer = CommentAnalyzer()
    saved = 0
    async with async_session() as s:
        for c in comments:
            content = c.get("content", "") or ""
            score = analyzer.score(c, comment_keywords, task.min_comment_likes)
            matched = analyzer.extract_matched_keywords(content, comment_keywords)
            comment = Comment(
                comment_id=c.get("comment_id", ""),
                note_id=note_id,
                task_id=task.id,
                content=content,
                user_name=c.get("user_name", "") or "",
                user_id=c.get("user_id", "") or "",
                avatar=c.get("avatar"),
                liked_count=int(c.get("liked_count", 0)),
                sub_comment_count=int(c.get("sub_comment_count", 0)),
                ip_location=c.get("ip_location"),
                pictures=c.get("pictures", "[]") or "[]",
                usefulness_score=float(score),
                usefulness_label=analyzer.classify(score),
                matched_keywords=json.dumps(matched, ensure_ascii=False),
                is_actionable=bool(analyzer.is_actionable(content)),
                has_reply_threads=bool(c.get("sub_comment_count", 0) > 0),
                created_at=datetime.datetime.utcnow(),
                crawled_at=datetime.datetime.utcnow(),
            )
            s.add(comment)
            try:
                await s.commit()
                saved += 1
            except Exception:
                # duplicate comment_id — skip
                await s.rollback()
    return {"note_id": note_id, "fetched": len(comments), "saved": saved}


@router.post("/tasks/{task_id}/refresh-all-posts")
async def refresh_all_posts(
    task_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Batch-fetch images AND comments for every post in a task that's
    missing either. One shared CDP session walks them all sequentially —
    much faster than the user clicking refresh on each post."""
    task = (await db.execute(
        select(MonitorTask).where(MonitorTask.id == task_id)
    )).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    rows = (await db.execute(
        select(Post).where(Post.task_id == task_id)
    )).scalars().all()

    def needs_images(p: Post) -> bool:
        raw = p.image_urls or ""
        if not raw or raw == "[]":
            return True
        try:
            arr = json.loads(raw)
        except Exception:
            return True
        if not isinstance(arr, list):
            return True
        return not any(isinstance(u, str) and u.startswith("http") for u in arr)

    # Count existing comments per note in this task (single query, fast)
    counts_rows = (await db.execute(
        select(Comment.note_id, func.count(Comment.id))
        .where(Comment.task_id == task_id)
        .group_by(Comment.note_id)
    )).all()
    comment_counts = {nid: c for nid, c in counts_rows}

    def needs_comments(p: Post) -> bool:
        return comment_counts.get(p.note_id, 0) == 0

    todo = []
    skipped_no_token = 0
    for p in rows:
        if not (needs_images(p) or needs_comments(p)):
            continue
        if not p.xsec_token:
            skipped_no_token += 1
            continue
        todo.append(p)

    if not todo:
        return {
            "total": len(rows),
            "needed_refresh": 0,
            "processed": 0,
            "images_added": 0,
            "comments_added": 0,
            "failed": 0,
            "skipped_no_token": skipped_no_token,
        }

    todo = todo[:limit]

    comment_keywords = [
        k.strip() for k in (task.comment_keywords or "").split(",") if k.strip()
    ]
    comment_cap = task.max_comments_per_post or 50

    images_added = 0
    comments_added = 0
    failed = 0
    analyzer = CommentAnalyzer()

    cdp = CDPManager()
    crawler = MediaCrawlerAdapter()
    try:
        context = await cdp.connect()
        await crawler.initialize(context)
        if not await crawler.ensure_logged_in():
            raise HTTPException(
                status_code=503,
                detail="CDP Chrome 未登录小红书，先扫码登录再试",
            )

        for p in todo:
            had_image_success = False
            had_comment_success = False

            # ---- Step 1: detail (images + meta) ---------------------
            if needs_images(p):
                try:
                    detail = await crawler.get_post_detail(
                        note_id=p.note_id,
                        xsec_token=p.xsec_token,
                        xsec_source=p.xsec_source or "pc_search",
                    )
                except Exception as e:
                    logger.warning(f"refresh-all-posts detail {p.note_id}: {e}")
                    detail = None

                if detail and detail.get("image_urls"):
                    try:
                        imgs = json.loads(detail["image_urls"]) or []
                    except Exception:
                        imgs = []
                    if imgs:
                        async with async_session() as s:
                            rp = (await s.execute(
                                select(Post).where(Post.note_id == p.note_id)
                            )).scalar_one_or_none()
                            if rp:
                                rp.image_urls = detail["image_urls"]
                                if not rp.title and detail.get("title"):
                                    rp.title = detail["title"]
                                if not rp.desc and detail.get("desc"):
                                    rp.desc = detail["desc"]
                                if detail.get("video_url"):
                                    rp.video_url = detail["video_url"]
                                await s.commit()
                        images_added += 1
                        had_image_success = True

            # ---- Step 2: comments (if needed) ------------------------
            if needs_comments(p):
                try:
                    comments = await crawler.get_comments(
                        note_id=p.note_id,
                        xsec_token=p.xsec_token,
                        xsec_source=p.xsec_source or "pc_search",
                        max_count=comment_cap,
                    )
                except Exception as e:
                    logger.warning(f"refresh-all-posts comments {p.note_id}: {e}")
                    comments = []

                if comments:
                    saved_here = 0
                    async with async_session() as s:
                        for c in comments:
                            content = c.get("content", "") or ""
                            score = analyzer.score(c, comment_keywords, task.min_comment_likes)
                            matched = analyzer.extract_matched_keywords(content, comment_keywords)
                            comment = Comment(
                                comment_id=c.get("comment_id", ""),
                                note_id=p.note_id,
                                task_id=task.id,
                                content=content,
                                user_name=c.get("user_name", "") or "",
                                user_id=c.get("user_id", "") or "",
                                avatar=c.get("avatar"),
                                liked_count=int(c.get("liked_count", 0)),
                                sub_comment_count=int(c.get("sub_comment_count", 0)),
                                ip_location=c.get("ip_location"),
                                pictures=c.get("pictures", "[]") or "[]",
                                usefulness_score=float(score),
                                usefulness_label=analyzer.classify(score),
                                matched_keywords=json.dumps(matched, ensure_ascii=False),
                                is_actionable=bool(analyzer.is_actionable(content)),
                                has_reply_threads=bool(c.get("sub_comment_count", 0) > 0),
                                created_at=datetime.datetime.utcnow(),
                                crawled_at=datetime.datetime.utcnow(),
                            )
                            s.add(comment)
                            try:
                                await s.commit()
                                saved_here += 1
                            except Exception:
                                await s.rollback()
                    comments_added += saved_here
                    if saved_here > 0:
                        had_comment_success = True

            # Count failure only if BOTH needed-and-attempted operations missed
            attempted_image = needs_images(p)
            attempted_comment = needs_comments(p)
            if attempted_image and not had_image_success and attempted_comment and not had_comment_success:
                failed += 1
            elif attempted_image and not had_image_success and not attempted_comment:
                failed += 1
            elif attempted_comment and not had_comment_success and not attempted_image:
                failed += 1
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("refresh_all_posts failed")
        raise HTTPException(status_code=502, detail=f"批量抓取失败: {e}")
    finally:
        try: await crawler.close()
        except Exception: pass
        try: await cdp.disconnect()
        except Exception: pass

    return {
        "total": len(rows),
        "needed_refresh": len(todo) + skipped_no_token,
        "processed": len(todo),
        "images_added": images_added,
        "comments_added": comments_added,
        "failed": failed,
        "skipped_no_token": skipped_no_token,
    }


@router.post("/posts/{note_id}/refresh-all")
async def refresh_post_all(
    note_id: str,
    max_comments: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Live-fetch BOTH images and comments in a single CDP session.

    Combines `refresh-images` + `refresh-comments` so the user's debug Chrome
    only spawns one tab for both operations.
    """
    result = await db.execute(select(Post).where(Post.note_id == note_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not post.xsec_token:
        raise HTTPException(
            status_code=409,
            detail="该帖子缺 xsec_token，无法抓取；重新跑一次任务即可",
        )

    task_result = await db.execute(
        select(MonitorTask).where(MonitorTask.id == post.task_id)
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="关联任务不存在")

    comment_keywords = [
        k.strip() for k in (task.comment_keywords or "").split(",") if k.strip()
    ]
    fetch_cap = min(max_comments, task.max_comments_per_post or max_comments)

    detail: Optional[dict] = None
    comments: list = []
    cdp = CDPManager()
    crawler = MediaCrawlerAdapter()
    try:
        context = await cdp.connect()
        await crawler.initialize(context)
        if not await crawler.ensure_logged_in():
            raise HTTPException(
                status_code=503,
                detail="CDP Chrome 未登录小红书，先扫码登录再试",
            )
        # Step 1: detail (gets images + title + desc + video_url)
        try:
            detail = await crawler.get_post_detail(
                note_id=note_id,
                xsec_token=post.xsec_token,
                xsec_source=post.xsec_source or "pc_search",
            )
        except Exception as e:
            logger.warning(f"refresh-all detail step failed: {e}")
        # Step 2: comments (re-uses same browser context)
        try:
            comments = await crawler.get_comments(
                note_id=note_id,
                xsec_token=post.xsec_token,
                xsec_source=post.xsec_source or "pc_search",
                max_count=fetch_cap,
            )
        except Exception as e:
            logger.warning(f"refresh-all comments step failed: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("refresh_post_all failed")
        raise HTTPException(status_code=502, detail=f"抓取失败: {e}")
    finally:
        try: await crawler.close()
        except Exception: pass
        try: await cdp.disconnect()
        except Exception: pass

    # --- Persist images ---
    images: list = []
    if detail:
        image_urls_json = detail.get("image_urls", "[]") or "[]"
        async with async_session() as s:
            p = (await s.execute(select(Post).where(Post.note_id == note_id))).scalar_one_or_none()
            if p:
                if image_urls_json and image_urls_json != "[]":
                    p.image_urls = image_urls_json
                if not p.title and detail.get("title"):
                    p.title = detail["title"]
                if not p.desc and detail.get("desc"):
                    p.desc = detail["desc"]
                if detail.get("video_url"):
                    p.video_url = detail["video_url"]
                await s.commit()
        try:
            images = json.loads(image_urls_json) or []
        except Exception:
            images = []

    # --- Persist comments ---
    saved = 0
    if comments:
        analyzer = CommentAnalyzer()
        async with async_session() as s:
            for c in comments:
                content = c.get("content", "") or ""
                score = analyzer.score(c, comment_keywords, task.min_comment_likes)
                matched = analyzer.extract_matched_keywords(content, comment_keywords)
                comment = Comment(
                    comment_id=c.get("comment_id", ""),
                    note_id=note_id,
                    task_id=task.id,
                    content=content,
                    user_name=c.get("user_name", "") or "",
                    user_id=c.get("user_id", "") or "",
                    avatar=c.get("avatar"),
                    liked_count=int(c.get("liked_count", 0)),
                    sub_comment_count=int(c.get("sub_comment_count", 0)),
                    ip_location=c.get("ip_location"),
                    pictures=c.get("pictures", "[]") or "[]",
                    usefulness_score=float(score),
                    usefulness_label=analyzer.classify(score),
                    matched_keywords=json.dumps(matched, ensure_ascii=False),
                    is_actionable=bool(analyzer.is_actionable(content)),
                    has_reply_threads=bool(c.get("sub_comment_count", 0) > 0),
                    created_at=datetime.datetime.utcnow(),
                    crawled_at=datetime.datetime.utcnow(),
                )
                s.add(comment)
                try:
                    await s.commit()
                    saved += 1
                except Exception:
                    await s.rollback()

    return {
        "note_id": note_id,
        "images": images,
        "image_count": len(images),
        "comments_fetched": len(comments),
        "comments_saved": saved,
    }


@router.delete("/posts/{note_id}", status_code=204)
async def delete_post(note_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a post and all its comments."""
    result = await db.execute(select(Post).where(Post.note_id == note_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    await db.execute(delete(Comment).where(Comment.note_id == note_id))
    await db.execute(delete(Post).where(Post.note_id == note_id))
    await db.commit()


@router.post("/tasks/{task_id}/posts/bulk-delete", status_code=200)
async def bulk_delete_posts(
    task_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple posts by note_id (and their comments) under a task."""
    note_ids = payload.get("note_ids") or []
    if not isinstance(note_ids, list) or not note_ids:
        raise HTTPException(status_code=400, detail="note_ids required")

    await db.execute(
        delete(Comment).where(
            Comment.task_id == task_id, Comment.note_id.in_(note_ids)
        )
    )
    result = await db.execute(
        delete(Post).where(
            Post.task_id == task_id, Post.note_id.in_(note_ids)
        )
    )
    await db.commit()
    return {"deleted": result.rowcount or 0}
