"""Repository for the analysis_sessions table."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.session_tables import AnalysisSessionTable
from src.db.repositories.base import GenericRepository


class AnalysisSessionRepository(GenericRepository[AnalysisSessionTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnalysisSessionTable, session)

    async def get_by_session(self, session_id: str) -> AnalysisSessionTable | None:
        stmt = select(AnalysisSessionTable).where(
            AnalysisSessionTable.session_id == session_id
        )
        result = await self._session.exec(stmt)
        return result.first()

    async def get_or_create(self, session_id: str) -> AnalysisSessionTable:
        existing = await self.get_by_session(session_id)
        if existing:
            return existing
        row = AnalysisSessionTable(session_id=session_id)
        return await self.create(row)

    async def save_draft(
        self, session_id: str, processing_result_json: str, analysis_draft_json: str
    ) -> AnalysisSessionTable:
        row = await self.get_or_create(session_id)
        row.processing_result = processing_result_json
        row.analysis_draft = analysis_draft_json
        return await self.update(row)

    async def save_council_note(
        self, session_id: str, council_note_json: str
    ) -> AnalysisSessionTable:
        row = await self.get_or_create(session_id)
        row.latest_council_note = council_note_json
        return await self.update(row)
