from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_owner
from app.db.models import FactVersion
from app.facts.repo import save_facts
from app.facts.schema import Facts, check_owner_answer

router = APIRouter(prefix="/api/facts", tags=["facts"])


class FactsOut(BaseModel):
    version_id: int
    created_at: datetime
    created_by: str
    note: str | None
    data: Facts


class FactsIn(BaseModel):
    data: Facts
    note: str | None = Field(default=None, max_length=500)
    # The version the owner started editing from. If someone saved in between,
    # we refuse instead of silently overwriting their change.
    base_version_id: int

    @field_validator("data")
    @classmethod
    def owner_answers_are_sentences(cls, data: Facts) -> Facts:
        for faq in data.faqs:
            check_owner_answer(faq.answer)
        return data


class VersionOut(BaseModel):
    id: int
    created_at: datetime
    created_by: str
    note: str | None


async def _latest(db: AsyncSession) -> FactVersion:
    row = await db.scalar(select(FactVersion).order_by(FactVersion.id.desc()).limit(1))
    if row is None:
        raise HTTPException(500, "No facts saved")
    return row


def _out(row: FactVersion) -> FactsOut:
    return FactsOut(version_id=row.id, created_at=row.created_at, created_by=row.created_by,
                    note=row.note, data=Facts.model_validate(row.data))


@router.get("", response_model=FactsOut, dependencies=[Depends(require_owner)])
async def current_facts(db: AsyncSession = Depends(get_db)):
    return _out(await _latest(db))


@router.put("", response_model=FactsOut)
async def update_facts(body: FactsIn, db: AsyncSession = Depends(get_db), owner: str = Depends(require_owner)):
    latest = await _latest(db)
    if body.base_version_id != latest.id:
        raise HTTPException(409, f"Facts changed since you started editing (now version {latest.id}). Reload and try again.")
    row = await save_facts(db, body.data, body.note or "Edited in dashboard", owner)
    return _out(row)


@router.get("/versions", response_model=list[VersionOut], dependencies=[Depends(require_owner)])
async def list_versions(db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(FactVersion).order_by(FactVersion.id.desc()).limit(200))).all()
    return [VersionOut.model_validate(r, from_attributes=True) for r in rows]


@router.get("/versions/{version_id}", response_model=FactsOut, dependencies=[Depends(require_owner)])
async def get_version(version_id: int, db: AsyncSession = Depends(get_db)):
    row = await db.get(FactVersion, version_id)
    if row is None:
        raise HTTPException(404, "Version not found")
    return _out(row)


@router.post("/versions/{version_id}/restore", response_model=FactsOut)
async def restore_version(version_id: int, db: AsyncSession = Depends(get_db), owner: str = Depends(require_owner)):
    row = await db.get(FactVersion, version_id)
    if row is None:
        raise HTTPException(404, "Version not found")
    restored = await save_facts(db, Facts.model_validate(row.data), f"Restored version {version_id}", owner)
    return _out(restored)
