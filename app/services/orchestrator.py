"""Scraping orchestration — coordinates the full scrape-analyze-store pipeline."""

import json
import datetime
from typing import Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session
from app.models.task import MonitorTask
from app.models.post import Post
from app.models.comment import Comment
from app.models.analysis import AnalysisResult
from app.adapters.mediacrawler import MediaCrawlerAdapter
from app.adapters.cdp_manager import CDPManager
from app.analysis.scorer import CommentAnalyzer


class XHSOrchestrator:
    """Orchestrates the full data collection pipeline.

    Flow:
        1. Ensure CDP browser connection and login state
        2. For each keyword in task: search posts → scrape comments
        3. Run comment analysis → save results to DB
        4. Create analysis summary
    """

    def __init__(
        self,
        cdp_manager: CDPManager,
        crawler: MediaCrawlerAdapter,
        analyzer: CommentAnalyzer,
        progress_callback: Optional[Callable] = None,
    ):
        self.cdp_manager = cdp_manager
        self.crawler = crawler
        self.analyzer = analyzer
        self.progress_callback = progress_callback

    async def _report(self, msg: str, level: str = "info"):
        if self.progress_callback:
            await self.progress_callback(msg, level)

    async def run_task(self, task: MonitorTask) -> AnalysisResult:
        """Execute one complete scrape-and-analyze cycle for a task.

        This is the main entry point called by the task runner.
        """
        await self._report(f"Starting scrape for task: {task.name}")

        # 1. Ensure browser connection
        context = await self.cdp_manager.ensure_connected()
        await self._report("Browser connected via CDP")

        # 2. Initialize crawler with default context (shares user's Chrome cookies)
        await self.crawler.initialize(context)

        # 3. Verify login state
        login_ok = await self.crawler.ensure_logged_in()
        if login_ok:
            await self._report("Xiaohongshu login verified")
        else:
            await self._report(
                "未检测到小红书登录态 (web_session/a1 cookie 缺失)。"
                "请在端口 9222 的 Chrome 中先扫码登录 xiaohongshu.com，"
                "然后再点击立即运行。",
                "error",
            )
            raise RuntimeError("Xiaohongshu not logged in in CDP browser")

        # 4. Create analysis result record
        analysis = AnalysisResult(
            task_id=task.id,
            run_started_at=datetime.datetime.utcnow(),
            status="running",
        )

        async with async_session() as db:
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)

        # 5. Parse keywords
        keywords = [k.strip() for k in task.keywords.split(",") if k.strip()]
        comment_keywords = [
            k.strip()
            for k in (task.comment_keywords or "").split(",")
            if k.strip()
        ]

        all_new_posts = []
        all_comments_scraped = 0
        useful_comments_found = 0

        try:
            for keyword in keywords:
                await self._report(f"Searching keyword: {keyword}")

                # 5a. Search posts
                posts = await self.crawler.search_posts(
                    keyword=keyword,
                    sort=task.search_sort,
                    note_type=task.note_type,
                    max_count=task.max_posts_per_run,
                    publish_time_type=getattr(task, "publish_time_type", 0) or 0,
                )

                if not posts:
                    await self._report(f"No posts found for: {keyword}", "warn")
                    continue

                await self._report(
                    f"Found {len(posts)} posts for '{keyword}', saving..."
                )

                # Apply min_post_likes filter BEFORE saving — we don't want
                # low-engagement noise polluting the DB or wasting comment fetches.
                min_likes = max(0, int(task.min_post_likes or 0))
                eligible = [
                    p for p in posts
                    if int(p.get("liked_count", 0)) >= min_likes
                ]
                skipped = len(posts) - len(eligible)
                if skipped:
                    await self._report(
                        f"Skipped {skipped} posts below {min_likes} likes",
                        "info",
                    )

                # Save eligible posts
                for post_data in eligible:
                    note_id = post_data.get("note_id", "")
                    if not note_id:
                        continue
                    post = await self._save_post(task.id, post_data)
                    if post:
                        all_new_posts.append(post)

                await self._report(
                    f"Saved {len(all_new_posts)} posts, now fetching comments..."
                )

                # Only fetch comments for the first few eligible posts
                max_comment_posts = min(3, len(eligible))
                for i, post_data in enumerate(eligible[:max_comment_posts]):
                    note_id = post_data.get("note_id", "")
                    xsec_token = post_data.get("xsec_token", "")
                    xsec_source = post_data.get("xsec_source", "pc_search")

                    if not note_id:
                        continue

                    if not xsec_token:
                        await self._report(
                            f"Skipping comments for {note_id}: missing xsec_token "
                            f"(search did not return signed link)",
                            "warn",
                        )
                        continue

                    await self._report(f"Fetching comments for post {i+1}/{max_comment_posts}...")
                    comments = await self.crawler.get_comments(
                        note_id=note_id,
                        xsec_token=xsec_token,
                        xsec_source=xsec_source,
                        max_count=task.max_comments_per_post,
                    )

                    for comment_data in comments:
                        comment_data["task_id"] = task.id
                        comment_data["note_id"] = note_id

                        score = self.analyzer.score(
                            comment_data, comment_keywords, task.min_comment_likes
                        )
                        comment_data["usefulness_score"] = score
                        comment_data["usefulness_label"] = self.analyzer.classify(score)
                        comment_data["matched_keywords"] = json.dumps(
                            self.analyzer.extract_matched_keywords(
                                comment_data.get("content", ""), comment_keywords
                            ),
                            ensure_ascii=False,
                        )
                        comment_data["is_actionable"] = self.analyzer.is_actionable(
                            comment_data.get("content", "")
                        )
                        comment_data["has_reply_threads"] = (
                            comment_data.get("sub_comment_count", 0) > 0
                        )
                        await self._save_comment(comment_data)

                        if score >= 0.4:
                            useful_comments_found += 1
                        all_comments_scraped += 1

                    await self._report(
                        f"Post {i+1}/{max_comment_posts}: got {len(comments)} comments",
                        "progress",
                    )

            # 6. Update analysis record
            analysis.posts_scraped = len(all_new_posts)
            analysis.comments_scraped = all_comments_scraped
            analysis.useful_comments_found = useful_comments_found
            analysis.status = "completed"
            analysis.run_completed_at = datetime.datetime.utcnow()

            async with async_session() as db:
                await db.merge(analysis)
                await db.commit()

            await self._report(
                f"Completed: {len(all_new_posts)} posts, "
                f"{all_comments_scraped} comments, "
                f"{useful_comments_found} useful"
            )

        except Exception as e:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.run_completed_at = datetime.datetime.utcnow()

            async with async_session() as db:
                await db.merge(analysis)
                await db.commit()

            await self._report(f"Error: {e}", "error")
            raise

        return analysis

    async def _save_post(self, task_id: int, post_data: dict) -> Optional[Post]:
        """Save or update a post record."""
        note_id = post_data.get("note_id", "")
        if not note_id:
            return None

        async with async_session() as db:
            post = Post(
                note_id=note_id,
                task_id=task_id,
                title=post_data.get("title", "") or "",
                desc=post_data.get("desc", "") or "",
                type=post_data.get("type", "normal"),
                author_name=post_data.get("author_name", "") or "",
                author_id=post_data.get("author_id", "") or "",
                author_avatar=post_data.get("author_avatar"),
                liked_count=int(post_data.get("liked_count", 0)),
                collected_count=int(post_data.get("collected_count", 0)),
                comment_count=int(post_data.get("comment_count", 0)),
                share_count=int(post_data.get("share_count", 0)),
                image_urls=json.dumps(
                    post_data.get("image_urls", []), ensure_ascii=False
                ),
                video_url=post_data.get("video_url"),
                tag_list=json.dumps(
                    post_data.get("tag_list", []), ensure_ascii=False
                ),
                xsec_token=post_data.get("xsec_token", ""),
                xsec_source=post_data.get("xsec_source", ""),
                url=post_data.get("url", ""),
                crawled_at=datetime.datetime.utcnow(),
            )
            db.add(post)
            try:
                await db.commit()
                return post
            except Exception:
                # Duplicate note_id — skip
                await db.rollback()
                return None

    async def _save_comment(self, comment_data: dict):
        """Save a comment record."""
        async with async_session() as db:
            comment = Comment(
                comment_id=comment_data.get("comment_id", ""),
                note_id=comment_data.get("note_id", ""),
                task_id=comment_data.get("task_id", 0),
                parent_comment_id=comment_data.get("parent_comment_id"),
                content=comment_data.get("content", "") or "",
                user_name=comment_data.get("user_name", "") or "",
                user_id=comment_data.get("user_id", "") or "",
                avatar=comment_data.get("avatar"),
                liked_count=int(comment_data.get("liked_count", 0)),
                sub_comment_count=int(comment_data.get("sub_comment_count", 0)),
                ip_location=comment_data.get("ip_location"),
                pictures=comment_data.get("pictures", "[]") or "[]",
                usefulness_score=float(comment_data.get("usefulness_score", 0.0)),
                usefulness_label=comment_data.get("usefulness_label", "unscored"),
                matched_keywords=comment_data.get("matched_keywords", "[]"),
                is_actionable=bool(comment_data.get("is_actionable", False)),
                has_reply_threads=bool(comment_data.get("has_reply_threads", False)),
                created_at=datetime.datetime.utcnow(),
                crawled_at=datetime.datetime.utcnow(),
            )
            db.add(comment)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
