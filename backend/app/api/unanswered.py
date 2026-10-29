from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_owner
from app.db.models import UnansweredQuestion
from app.facts.repo import latest_facts, save_facts
from app.facts.schema import FAQ, check_owner_answer

router = APIRouter(prefix="/api/unanswered", tags=["unanswered"])


class QuestionOut(BaseModel):
    id: int
    call_id: int | None
    question: str
    status: str
    answer: str | None
    created_at: datetime
    answered_at: datetime | None


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)
    # Owner may tidy up the question wording before it becomes a fact.
    question: str | None = Field(default=None, max_length=500)

    @field_validator("answer")
    @classmethod
    def answer_is_sentence(cls, v: str) -> str:
        return check_owner_answer(v)


@router.get("", response_model=list[QuestionOut], dependencies=[Depends(require_owner)])
async def list_questions(status: Literal["open", "answered", "dismissed", "all"] = "open",
                         db: AsyncSession = Depends(get_db)):
    q = select(UnansweredQuestion)
    if status != "all":
        q = q.where(UnansweredQuestion.status == status)
    return (await db.scalars(q.order_by(UnansweredQuestion.created_at.desc()).limit(500))).all()


async def _get(db: AsyncSession, qid: int) -> UnansweredQuestion:
    q = await db.get(UnansweredQuestion, qid)
    if q is None:
        raise HTTPException(404, "Question not found")
    return q


@router.post("/{qid}/answer", response_model=QuestionOut)
async def answer_question(qid: int, body: AnswerIn, db: AsyncSession = Depends(get_db),
                          owner: str = Depends(require_owner)):
    q = await _get(db, qid)
    question = (body.question or q.question).strip()
    answer = body.answer.strip()

    # The answer becomes a fact: save a new facts version with it in the FAQ list,
    # so the very next call can use it.
    _, facts = await latest_facts(db)
    facts.faqs = [f for f in facts.faqs if f.unanswered_id != q.id]
    facts.faqs.append(FAQ(question=question, answer=answer, unanswered_id=q.id))
    await save_facts(db, facts, f"Answered question #{q.id}", owner)

    q.status, q.answer, q.answered_at = "answered", answer, datetime.now(timezone.utc)
    await db.commit()
    return q


@router.post("/{qid}/dismiss", response_model=QuestionOut, dependencies=[Depends(require_owner)])
async def dismiss_question(qid: int, db: AsyncSession = Depends(get_db)):
    q = await _get(db, qid)
    q.status = "dismissed"
    await db.commit()
    return q
