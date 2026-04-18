"""Repository for the processing_attempts table."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.session_tables import ProcessingAttemptTable
from src.db.repositories.base import GenericRepository


class ProcessingAttemptRepository(GenericRepository[ProcessingAttemptTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(ProcessingAttemptTable, session)

    async def append(
        self, session_id: str, pir: str, raw_result: str
    ) -> ProcessingAttemptTable:
        """Append a new processing attempt, auto-numbering."""
        latest = await self.get_latest(session_id)
        next_num = (latest.attempt_number + 1) if latest else 1

        row = ProcessingAttemptTable(
            session_id=session_id,
            attempt_number=next_num,
            pir=pir,
            raw_result=raw_result,
            created_at=datetime.now(UTC),
        )
        return await self.create(row)

    async def get_all(self, session_id: str) -> Sequence[ProcessingAttemptTable]:
        stmt = (
            select(ProcessingAttemptTable)
            .where(ProcessingAttemptTable.session_id == session_id)
            .order_by(ProcessingAttemptTable.attempt_number)
        )
        result = await self._session.exec(stmt)
        return result.all()

    async def get_latest(self, session_id: str) -> ProcessingAttemptTable | None:
        stmt = (
            select(ProcessingAttemptTable)
            .where(ProcessingAttemptTable.session_id == session_id)
            .order_by(ProcessingAttemptTable.attempt_number.desc())
            .limit(1)
        )
        result = await self._session.exec(stmt)
        return result.first()
