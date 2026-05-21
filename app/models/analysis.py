import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.models.database import Base


class AnalysisResult(Base):
    """Aggregated analysis snapshot per monitoring cycle."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(
        Integer, ForeignKey("monitor_tasks.id", ondelete="CASCADE"), nullable=False
    )
    run_started_at = Column(DateTime, default=datetime.datetime.utcnow)
    run_completed_at = Column(DateTime, nullable=True)
    posts_scraped = Column(Integer, default=0)
    comments_scraped = Column(Integer, default=0)
    useful_comments_found = Column(Integer, default=0)
    top_keywords = Column(
        Text, default="{}", comment="JSON: frequency map of comment keywords"
    )
    error_message = Column(Text, nullable=True)
    status = Column(
        String(20), default="running", comment="running|completed|failed"
    )
