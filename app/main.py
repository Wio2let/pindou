"""Xiaohongshu Monitor - FastAPI Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.api.tasks import router as tasks_router
from app.api.posts import router as posts_router
from app.api.comments import router as comments_router
from app.api.analysis import router as analysis_router
from app.api.stats import router as stats_router
from app.api.system import router as system_router
from app.api.ws import router as ws_router
from app.api.bilibili import router as bilibili_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="Xiaohongshu Monitor",
    description="小红书热门监控 + 评论区实用评论搜索",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(tasks_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(analysis_router)
app.include_router(stats_router)
app.include_router(system_router)
app.include_router(ws_router)
app.include_router(bilibili_router)


@app.get("/")
async def root():
    return {
        "app": "Xiaohongshu Monitor",
        "docs": "/docs",
        "status": "/api/system/health",
    }
