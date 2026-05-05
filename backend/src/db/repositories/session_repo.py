"""Repository for the sessions table."""

from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.session_tables import (
    AnalysisSessionTable,
    CollectionAttemptTable,
    CollectionStatusTable,
    ProcessingAttemptTable,
    ResearchLogEntryTable,
    SessionTable,
    UploadedFileTable,
)
from src.db.repositories.base import GenericRepository


class SessionRepository(GenericRepository[SessionTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(SessionTable, session)

    async def exists(self, session_id: str) -> bool:
        row = await self.get(session_id)
        return row is not None

    async def upsert(self, entity: SessionTable) -> SessionTable:
        entity.updated_at = datetime.now(UTC)
        existing = await self.get(entity.id)
        if existing is None:
            return await self.create(entity)
        # Preserve the original created_at timestamp
        entity.created_at = existing.created_at
        # Copy changed fields onto the existing (tracked) object
        for key in entity.model_fields:
            if key != "id":
                setattr(existing, key, getattr(entity, key))
        self._session.add(existing)
        await self._session.flush()
        return existing

    async def delete_cascade(self, session_id: str) -> bool:
        """Delete a session and all related rows across child tables.

        Returns:
            True if a session row existed and was deleted, False otherwise.
            Child rows are always cleaned up regardless of the return value.
        """
        # Delete children first (SQLite FK support varies)
        for model in (
            CollectionAttemptTable,
            ProcessingAttemptTable,
            UploadedFileTable,
            AnalysisSessionTable,
            ResearchLogEntryTable,
            CollectionStatusTable,
        ):
            stmt = select(model).where(model.session_id == session_id)
            results = await self._session.exec(stmt)
            for row in results.all():
                await self._session.delete(row)

        session_row = await self.get(session_id)
        existed = session_row is not None
        if session_row:
            await self._session.delete(session_row)
        await self._session.flush()
        return existed
