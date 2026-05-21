import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Index
from app.models.database import Base


class Comment(Base):
    """A comment on a Xiaohongshu post."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(String(100), nullable=False, comment="Xiaohongshu comment ID")
    note_id = Column(
        String(100), ForeignKey("posts.note_id", ondelete="CASCADE"), nullable=False
    )
    task_id = Column(
        Integer,
        ForeignKey("monitor_tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Denormalized for fast querying",
    )
    parent_comment_id = Column(String(100), nullable=True, comment="For sub-comments")

    content = Column(Text, default="", comment="Comment text")
    user_name = Column(String(255), default="")
    user_id = Column(String(100), default="")
    avatar = Column(String(500), nullable=True)
    liked_count = Column(Integer, default=0)
    sub_comment_count = Column(Integer, default=0)
    ip_location = Column(String(100), nullable=True)
    pictures = Column(Text, default="[]", comment="JSON list of comment image URLs")

    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="Comment timestamp")
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Analysis fields
    usefulness_score = Column(
        Float, default=0.0, comment="0.0-1.0 composite usefulness score"
    )
    usefulness_label = Column(
        String(20),
        default="unscored",
        comment="high|medium|low|unscored",
    )
    matched_keywords = Column(
        Text, default="[]", comment="JSON list of matched comment_keywords"
    )
    is_actionable = Column(Boolean, default=False, comment="Contains actionable info")
    has_reply_threads = Column(Boolean, default=False)

    # User-driven favorites + categorization
    favorite = Column(Boolean, default=False, comment="User-favorited comment")
    category = Column(
        String(120), default="",
        comment="User-assigned category for favorites (free text)",
    )

    __table_args__ = (
        Index("idx_comments_task_usefulness", "task_id", "usefulness_score"),
        Index("idx_comments_note_id", "note_id"),
        Index("idx_comments_task_likes", "task_id", "liked_count"),
    )
