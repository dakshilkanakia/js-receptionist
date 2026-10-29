from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_owner
from app.db.models import Call, CallbackRequest, UnansweredQuestion

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_owner)])

NY = ZoneInfo("America/New_York")


@router.get("")
async def stats(db: AsyncSession = Depends(get_db)) -> dict:
    now = datetime.now(NY)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=6)

    by_outcome = dict((await db.execute(
        select(Call.outcome, func.count()).where(Call.started_at >= week).group_by(Call.outcome)
    )).all())
    calls_today = await db.scalar(select(func.count()).where(Call.started_at >= today))
    avg_duration = await db.scalar(
        select(func.avg(Call.duration_s)).where(Call.started_at >= week, Call.duration_s.is_not(None))
    )
    pending = await db.scalar(select(func.count()).where(CallbackRequest.status == "pending"))
    open_q = await db.scalar(select(func.count()).where(UnansweredQuestion.status == "open"))
    return {
        "calls_today": calls_today or 0,
        "calls_7d": sum(by_outcome.values()),
        "outcomes_7d": by_outcome,
        "avg_duration_s_7d": round(float(avg_duration)) if avg_duration else None,
        "pending_callbacks": pending or 0,
        "open_questions": open_q or 0,
    }
