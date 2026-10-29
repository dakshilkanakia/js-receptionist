from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FactVersion
from app.facts.schema import Facts
from app.facts.seed import SEED_FACTS


async def latest_facts(session: AsyncSession) -> tuple[int, Facts]:
    row = await session.scalar(select(FactVersion).order_by(FactVersion.id.desc()).limit(1))
    if row is None:
        raise RuntimeError("No facts saved yet; run the seed")
    return row.id, Facts.model_validate(row.data)


async def save_facts(
    session: AsyncSession, facts: Facts, note: str | None, created_by: str
) -> FactVersion:
    row = FactVersion(data=facts.model_dump(mode="json"), note=note, created_by=created_by)
    session.add(row)
    await session.commit()
    return row


async def seed_if_empty(session: AsyncSession) -> None:
    if await session.scalar(select(FactVersion.id).limit(1)) is None:
        await save_facts(session, Facts.model_validate(SEED_FACTS), "Initial facts from spec", "system")
