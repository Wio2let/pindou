"""Task management API endpoints."""

import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from app.models.database import get_db
from app.models.task import MonitorTask
from app.models.post import Post
from app.models.comment import Comment
from app.models.analysis import AnalysisResult
from app.utils.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskStats
from app.services.task_runner import start_task, stop_task, is_task_running

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MonitorTask).order_by(MonitorTask.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MonitorTask).where(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = MonitorTask(**data.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int, data: TaskUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MonitorTask).where(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    task.updated_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    # Delete associated data first
    await db.execute(delete(AnalysisResult).where(AnalysisResult.task_id == task_id))
    await db.execute(delete(Comment).where(Comment.task_id == task_id))
    await db.execute(delete(Post).where(Post.task_id == task_id))
    await db.execute(delete(MonitorTask).where(MonitorTask.id == task_id))
    await db.commit()


@router.get("/{task_id}/status")
async def get_task_status(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MonitorTask).where(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "id": task.id,
        "status": task.status,
        "enabled": task.enabled,
        "last_run_at": task.last_run_at,
        "next_run_at": task.next_run_at,
    }


@router.post("/{task_id}/run", status_code=202)
async def run_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger an immediate scrape run for a task."""
    result = await db.execute(select(MonitorTask).where(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "running" or is_task_running(task_id):
        raise HTTPException(status_code=409, detail="Task is already running")

    if not start_task(task_id):
        raise HTTPException(status_code=500, detail="Failed to start task")

    return {"message": f"Task {task_id} started", "task_id": task_id}


@router.post("/{task_id}/stop", status_code=200)
async def stop_task_endpoint(task_id: int, db: AsyncSession = Depends(get_db)):
    """Stop a running task."""
    result = await db.execute(select(MonitorTask).where(MonitorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if await stop_task(task_id):
        return {"message": f"Task {task_id} stopping", "task_id": task_id}

    raise HTTPException(status_code=409, detail="Task is not running")


@router.get("/stats/summary", response_model=List[TaskStats])
async def get_tasks_stats(db: AsyncSession = Depends(get_db)):
    """Get summary stats for all tasks."""
    result = await db.execute(select(MonitorTask).order_by(MonitorTask.created_at.desc()))
    tasks = result.scalars().all()

    stats = []
    for task in tasks:
        # Count posts
        post_count = await db.execute(
            select(func.count(Post.note_id)).where(Post.task_id == task.id)
        )
        # Count comments
        comment_count = await db.execute(
            select(func.count(Comment.id)).where(Comment.task_id == task.id)
        )
        # Count useful comments (score >= 0.4)
        useful_count = await db.execute(
            select(func.count(Comment.id)).where(
                Comment.task_id == task.id,
                Comment.usefulness_score >= 0.4,
            )
        )
        stats.append(
            TaskStats(
                task_id=task.id,
                task_name=task.name,
                total_posts=post_count.scalar() or 0,
                total_comments=comment_count.scalar() or 0,
                useful_comments=useful_count.scalar() or 0,
                last_run_status=task.status,
                last_run_time=task.last_run_at,
                is_enabled=task.enabled,
            )
        )
    return stats
