"""Dashboard statistics API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import datetime

from app.models.database import get_db
from app.models.task import MonitorTask
from app.models.post import Post
from app.models.comment import Comment
from app.utils.schemas import DashboardStats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview", response_model=DashboardStats)
async def get_dashboard_overview(db: AsyncSession = Depends(get_db)):
    # Active tasks
    active = await db.execute(
        select(func.count(MonitorTask.id)).where(MonitorTask.enabled == True)
    )
    # Total posts
    posts = await db.execute(select(func.count(Post.note_id)))
    # Total comments
    comments = await db.execute(select(func.count(Comment.id)))
    # Useful comments (score >= 0.4)
    useful = await db.execute(
        select(func.count(Comment.id)).where(Comment.usefulness_score >= 0.4)
    )

    # Today's data
    today_start = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    posts_today = await db.execute(
        select(func.count(Post.note_id)).where(Post.crawled_at >= today_start)
    )
    comments_today = await db.execute(
        select(func.count(Comment.id)).where(Comment.crawled_at >= today_start)
    )

    return DashboardStats(
        active_tasks=active.scalar() or 0,
        total_posts=posts.scalar() or 0,
        total_comments=comments.scalar() or 0,
        total_useful_comments=useful.scalar() or 0,
        posts_today=posts_today.scalar() or 0,
        comments_today=comments_today.scalar() or 0,
    )
