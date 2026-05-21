"""Analysis results API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.database import get_db
from app.models.analysis import AnalysisResult
from app.utils.schemas import AnalysisResponse

router = APIRouter(prefix="/api/tasks/{task_id}/analysis", tags=["analysis"])


@router.get("", response_model=AnalysisResponse)
async def get_latest_analysis(
    task_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.task_id == task_id, AnalysisResult.status == "completed")
        .order_by(desc(AnalysisResult.run_started_at))
        .limit(1)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="No completed analysis found")
    return analysis


@router.get("/history", response_model=List[AnalysisResponse])
async def get_analysis_history(
    task_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AnalysisResult)
        .where(AnalysisResult.task_id == task_id)
        .order_by(desc(AnalysisResult.run_started_at))
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    return result.scalars().all()
