import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.models.database import Base


class MonitorTask(Base):
    """A periodic monitoring task configuration."""

    __tablename__ = "monitor_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, comment="Human-readable task name")
    keywords = Column(Text, nullable=False, comment="Comma-separated search keywords")
    search_sort = Column(
        String(50),
        default="general",
        comment="general|popularity_descending|time_descending",
    )
    note_type = Column(
        Integer, default=0, comment="0=all, 1=video, 2=image"
    )
    interval_minutes = Column(
        Integer, default=30, comment="Polling interval in minutes"
    )
    max_posts_per_run = Column(Integer, default=20, comment="Max posts per cycle")
    max_comments_per_post = Column(
        Integer, default=50, comment="Max comments per post"
    )
    min_post_likes = Column(
        Integer, default=0, comment="Skip posts whose liked_count is below this"
    )
    publish_time_type = Column(
        Integer, default=0,
        comment="0=any 1=24h 2=7d 3=30d 4=180d (filter by note publish time)",
    )
    comment_keywords = Column(
        Text, default="", comment="Comma-separated keywords to search in comments"
    )
    min_comment_likes = Column(Integer, default=1, comment="Min likes for useful comment")

    enabled = Column(Boolean, default=True)
    status = Column(
        String(20),
        default="idle",
        comment="idle|running|paused|error",
    )
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
