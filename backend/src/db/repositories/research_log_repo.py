"""Repository for the research_log_entries table."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.session_tables import ResearchLogEntryTable
from src.db.repositories.base import GenericRepository


class ResearchLogRepository(GenericRepository[ResearchLogEntryTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResearchLogEntryTable, session)

    async def append(
        self,
        session_id: str,
        entry_type: str,
        phase: str | None,
        content_json: str,
    ) -> ResearchLogEntryTable:
        row = ResearchLogEntryTable(
            session_id=session_id,
            entry_type=entry_type,
            phase=phase,
            timestamp=datetime.now(UTC),
            content=content_json,
        )
        return await self.create(row)

    async def get_all(self, session_id: str) -> Sequence[ResearchLogEntryTable]:
        stmt = (
            select(ResearchLogEntryTable)
            .where(ResearchLogEntryTable.session_id == session_id)
            .order_by(ResearchLogEntryTable.timestamp)
        )
        result = await self._session.exec(stmt)
        return result.all()
