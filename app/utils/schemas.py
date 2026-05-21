import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ===== Task Schemas =====

class TaskCreate(BaseModel):
    name: str = Field(..., max_length=255)
    keywords: str = Field(..., description="Comma-separated search keywords")
    search_sort: str = Field(default="general", pattern=r"^(general|popularity_descending|time_descending)$")
    note_type: int = Field(default=0, ge=0, le=2)
    interval_minutes: int = Field(default=30, ge=5, le=1440)
    max_posts_per_run: int = Field(default=20, ge=1, le=100)
    max_comments_per_post: int = Field(default=50, ge=0, le=500)
    min_post_likes: int = Field(default=0, ge=0, description="Skip posts below this like count")
    publish_time_type: int = Field(
        default=0, ge=0, le=4,
        description="Publish-time window: 0=any 1=24h 2=7d 3=30d 4=180d",
    )
    comment_keywords: str = Field(default="", description="Comma-separated keywords to find in comments")
    min_comment_likes: int = Field(default=1, ge=0)
    enabled: bool = True


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[str] = None
    search_sort: Optional[str] = None
    note_type: Optional[int] = None
    interval_minutes: Optional[int] = None
    max_posts_per_run: Optional[int] = None
    max_comments_per_post: Optional[int] = None
    min_post_likes: Optional[int] = None
    publish_time_type: Optional[int] = None
    comment_keywords: Optional[str] = None
    min_comment_likes: Optional[int] = None
    enabled: Optional[bool] = None


class TaskResponse(BaseModel):
    id: int
    name: str
    keywords: str
    search_sort: str
    note_type: int
    interval_minutes: int
    max_posts_per_run: int
    max_comments_per_post: int
    min_post_likes: int = 0
    publish_time_type: int = 0
    comment_keywords: str
    min_comment_likes: int
    enabled: bool
    status: str
    last_run_at: Optional[datetime.datetime] = None
    next_run_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


# ===== Post Schemas =====

class PostResponse(BaseModel):
    note_id: str
    task_id: int
    title: str
    desc: str
    type: str
    author_name: str
    author_id: str
    liked_count: int
    collected_count: int
    comment_count: int
    share_count: int
    image_urls: str = ""
    video_url: Optional[str] = None
    xsec_token: str = ""
    xsec_source: str = ""
    url: str
    crawled_at: datetime.datetime
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class PostDetailResponse(PostResponse):
    tag_list: str = "[]"
    # Aggregated from comments
    useful_comment_count: int = 0
    avg_usefulness: float = 0.0


# ===== Comment Schemas =====

class CommentResponse(BaseModel):
    id: int
    comment_id: str
    note_id: str
    task_id: int
    content: str
    user_name: str
    liked_count: int
    sub_comment_count: int
    ip_location: Optional[str] = None
    pictures: str = "[]"
    usefulness_score: float
    usefulness_label: str
    matched_keywords: str
    is_actionable: bool
    favorite: bool = False
    category: str = ""
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class CommentUpdate(BaseModel):
    favorite: Optional[bool] = None
    category: Optional[str] = Field(default=None, max_length=120)


class CommentSearchParams(BaseModel):
    q: str = Field(default="", description="Search query")
    min_score: float = Field(default=0.0, ge=0.0, le=1.0)
    min_likes: int = Field(default=0, ge=0)
    sort: str = Field(default="score", pattern=r"^(score|likes|date)$")
    actionable_only: bool = False
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=200)


# ===== Analysis Schemas =====

class AnalysisResponse(BaseModel):
    id: int
    task_id: int
    run_started_at: datetime.datetime
    run_completed_at: Optional[datetime.datetime] = None
    posts_scraped: int
    comments_scraped: int
    useful_comments_found: int
    top_keywords: str
    status: str
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


# ===== Dashboard Stats =====

class DashboardStats(BaseModel):
    active_tasks: int = 0
    total_posts: int = 0
    total_comments: int = 0
    total_useful_comments: int = 0
    posts_today: int = 0
    comments_today: int = 0


class TaskStats(BaseModel):
    task_id: int
    task_name: str
    total_posts: int
    total_comments: int
    useful_comments: int
    last_run_status: str
    last_run_time: Optional[datetime.datetime] = None
    is_enabled: bool


# ===== WebSocket =====

class WSMessage(BaseModel):
    type: str = Field(..., pattern=r"^(log|progress|complete|error|new_useful_comment)$")
    message: Optional[str] = None
    level: Optional[str] = "info"
    data: Optional[dict] = None
