"""Comment query and search API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.models.database import get_db
from app.models.comment import Comment
from app.utils.schemas import CommentResponse, CommentSearchParams, CommentUpdate
from app.utils.fts import search_comments_fts

router = APIRouter(prefix="/api", tags=["comments"])


@router.get("/posts/{note_id}/comments", response_model=List[CommentResponse])
async def list_comments(
    note_id: str,
    sort: str = Query("score", pattern=r"^(score|likes|date)$"),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    order_map = {
        "score": desc(Comment.usefulness_score),
        "likes": desc(Comment.liked_count),
        "date": desc(Comment.created_at),
    }
    order_col = order_map.get(sort, desc(Comment.usefulness_score))

    result = await db.execute(
        select(Comment)
        .where(Comment.note_id == note_id, Comment.usefulness_score >= min_score)
        .order_by(order_col)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return result.scalars().all()


@router.get("/tasks/{task_id}/comments/search")
async def search_comments(
    task_id: int,
    q: str = Query("", description="Search query"),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    min_likes: int = Query(0, ge=0),
    sort: str = Query("score", pattern=r"^(score|likes|date)$"),
    actionable_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across comments within a task."""
    rows, total = await search_comments_fts(
        db=db,
        task_id=task_id,
        query=q,
        min_score=min_score,
        min_likes=min_likes,
        actionable_only=actionable_only,
        sort=sort,
        page=page,
        per_page=per_page,
    )

    # Convert rows to dicts
    comments = []
    for row in rows:
        comment = {
            "id": row.id,
            "comment_id": row.comment_id,
            "note_id": row.note_id,
            "task_id": row.task_id,
            "content": row.content,
            "user_name": row.user_name,
            "liked_count": row.liked_count,
            "sub_comment_count": row.sub_comment_count,
            "ip_location": row.ip_location,
            "usefulness_score": row.usefulness_score,
            "usefulness_label": row.usefulness_label,
            "matched_keywords": row.matched_keywords,
            "is_actionable": row.is_actionable,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        comments.append(comment)

    return {
        "items": comments,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
    }


# ============================================================
# Favorites / categorization
# ============================================================

@router.patch("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: int,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Toggle favorite or set/clear category on a comment."""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    if data.favorite is not None:
        c.favorite = bool(data.favorite)
        # If unfavoriting, also clear category (or keep it? clear for clarity)
        if not c.favorite:
            c.category = ""
    if data.category is not None:
        c.category = (data.category or "").strip()[:120]
    await db.commit()
    await db.refresh(c)
    return c


@router.get("/comments/favorites", response_model=List[CommentResponse])
async def list_favorites(
    category: Optional[str] = Query(None, description="Filter by category (empty='all', 'uncategorized'=blank)"),
    task_id: Optional[int] = Query(None),
    sort: str = Query("recent", pattern=r"^(recent|score|likes)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Comment).where(Comment.favorite == True)  # noqa: E712
    if task_id is not None:
        stmt = stmt.where(Comment.task_id == task_id)
    if category is not None:
        if category == "uncategorized":
            stmt = stmt.where(Comment.category == "")
        elif category != "":
            stmt = stmt.where(Comment.category == category)

    order_map = {
        "recent": desc(Comment.id),
        "score":  desc(Comment.usefulness_score),
        "likes":  desc(Comment.liked_count),
    }
    stmt = stmt.order_by(order_map.get(sort, desc(Comment.id)))
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/comments/categories")
async def list_categories(
    task_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct categories of favorited comments with counts.

    Always includes synthetic buckets 'all' and 'uncategorized' for the UI.
    """
    base = select(Comment.category, func.count(Comment.id)).where(
        Comment.favorite == True  # noqa: E712
    )
    if task_id is not None:
        base = base.where(Comment.task_id == task_id)

    rows = (await db.execute(base.group_by(Comment.category))).all()

    total = 0
    uncategorized = 0
    named: list[dict] = []
    for cat, cnt in rows:
        total += cnt
        if not cat:
            uncategorized += cnt
        else:
            named.append({"category": cat, "count": cnt})

    named.sort(key=lambda x: (-x["count"], x["category"]))

    return {
        "total": total,
        "uncategorized": uncategorized,
        "categories": named,
    }
