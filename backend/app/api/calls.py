from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_owner
from app.db.models import Call, CallbackRequest, TranscriptTurn, UnansweredQuestion

router = APIRouter(prefix="/api/calls", tags=["calls"], dependencies=[Depends(require_owner)])

OUTCOMES = {"answered", "callback_requested", "unanswered", "abandoned", "in_progress"}


class CallOut(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    duration_s: int | None
    outcome: str
    consent_declined: bool
    has_unanswered: bool
    facts_version_id: int | None
    turn_count: int = 0
    preview: str | None = None


class TurnOut(BaseModel):
    idx: int
    role: str
    text: str
    interrupted: bool
    created_at: datetime


class CallbackBrief(BaseModel):
    id: int
    first_name: str
    phone_e164: str
    reason: str
    status: str


class QuestionBrief(BaseModel):
    id: int
    question: str
    status: str


class CallDetail(CallOut):
    turns: list[TurnOut]
    callbacks: list[CallbackBrief]
    questions: list[QuestionBrief]


class CallPage(BaseModel):
    items: list[CallOut]
    total: int
    page: int
    page_size: int


def _call_out(call: Call, turn_count: int = 0, preview: str | None = None) -> dict:
    return {**{c: getattr(call, c) for c in CallOut.model_fields if hasattr(call, c)},
            "turn_count": turn_count, "preview": preview}


@router.get("", response_model=CallPage)
async def list_calls(
    outcome: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    q = select(Call)
    if outcome:
        if outcome not in OUTCOMES:
            raise HTTPException(400, f"Unknown outcome {outcome}")
        q = q.where(Call.outcome == outcome)
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    calls = (await db.scalars(q.order_by(Call.id.desc()).offset((page - 1) * page_size).limit(page_size))).all()

    ids = [c.id for c in calls]
    counts: dict[int, int] = {}
    previews: dict[int, str] = {}
    if ids:
        rows = await db.execute(
            select(TranscriptTurn.call_id, func.count()).where(TranscriptTurn.call_id.in_(ids))
            .group_by(TranscriptTurn.call_id)
        )
        counts = dict(rows.all())
        # First thing the caller said, as a one-line preview.
        first_user = (
            select(TranscriptTurn.call_id, func.min(TranscriptTurn.idx).label("idx"))
            .where(TranscriptTurn.call_id.in_(ids), TranscriptTurn.role == "user")
            .group_by(TranscriptTurn.call_id).subquery()
        )
        rows = await db.execute(
            select(TranscriptTurn.call_id, TranscriptTurn.text).join(
                first_user,
                (TranscriptTurn.call_id == first_user.c.call_id) & (TranscriptTurn.idx == first_user.c.idx),
            )
        )
        previews = dict(rows.all())
    return CallPage(
        items=[CallOut(**_call_out(c, counts.get(c.id, 0), previews.get(c.id))) for c in calls],
        total=total or 0, page=page, page_size=page_size,
    )


@router.get("/{call_id}", response_model=CallDetail)
async def get_call(call_id: int, db: AsyncSession = Depends(get_db)):
    call = await db.get(Call, call_id)
    if call is None:
        raise HTTPException(404, "Call not found")
    turns = (await db.scalars(select(TranscriptTurn).where(TranscriptTurn.call_id == call_id)
                              .order_by(TranscriptTurn.idx))).all()
    callbacks = (await db.scalars(select(CallbackRequest).where(CallbackRequest.call_id == call_id))).all()
    questions = (await db.scalars(select(UnansweredQuestion).where(UnansweredQuestion.call_id == call_id))).all()
    return CallDetail(
        **_call_out(call, len(turns)),
        turns=[TurnOut.model_validate(t, from_attributes=True) for t in turns],
        callbacks=[CallbackBrief.model_validate(c, from_attributes=True) for c in callbacks],
        questions=[QuestionBrief.model_validate(q, from_attributes=True) for q in questions],
    )
