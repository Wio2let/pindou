import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from app.models.database import Base


class Post(Base):
    """A scraped Xiaohongshu note/post."""

    __tablename__ = "posts"

    note_id = Column(String(100), primary_key=True, comment="Xiaohongshu's own ID")
    task_id = Column(
        Integer, ForeignKey("monitor_tasks.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(500), default="")
    desc = Column(Text, default="", comment="Post description/content text")
    type = Column(String(20), default="normal", comment="normal|video")
    author_name = Column(String(255), default="")
    author_id = Column(String(100), default="")
    author_avatar = Column(String(500), nullable=True)
    liked_count = Column(Integer, default=0)
    collected_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    image_urls = Column(Text, default="[]", comment="JSON list of URLs")
    video_url = Column(String(500), nullable=True)
    tag_list = Column(Text, default="[]", comment="JSON list of tags")
    xsec_token = Column(String(500), default="", comment="API access token")
    xsec_source = Column(String(50), default="", comment="API access source")
    url = Column(String(500), default="", comment="Full post URL")
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, comment="Post timestamp")

    __table_args__ = (
        Index("idx_posts_task_crawled", "task_id", "crawled_at"),
    )
