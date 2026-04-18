"""Repository for the collection_attempts table."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.session_tables import CollectionAttemptTable
from src.db.repositories.base import GenericRepository


class CollectionAttemptRepository(GenericRepository[CollectionAttemptTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(CollectionAttemptTable, session)

    async def append(
        self, session_id: str, pir: str, raw_response: str
    ) -> CollectionAttemptTable:
        """Append a new collection attempt, auto-numbering."""
        latest = await self.get_latest(session_id)
        next_num = (latest.attempt_number + 1) if latest else 1

        row = CollectionAttemptTable(
            session_id=session_id,
            attempt_number=next_num,
            pir=pir,
            raw_response=raw_response,
            created_at=datetime.now(UTC),
        )
        return await self.create(row)

    async def get_all(self, session_id: str) -> Sequence[CollectionAttemptTable]:
        stmt = (
            select(CollectionAttemptTable)
            .where(CollectionAttemptTable.session_id == session_id)
            .order_by(CollectionAttemptTable.attempt_number)
        )
        result = await self._session.exec(stmt)
        return result.all()

    async def get_latest(self, session_id: str) -> CollectionAttemptTable | None:
        stmt = (
            select(CollectionAttemptTable)
            .where(CollectionAttemptTable.session_id == session_id)
            .order_by(CollectionAttemptTable.attempt_number.desc())
            .limit(1)
        )
        result = await self._session.exec(stmt)
        return result.first()
