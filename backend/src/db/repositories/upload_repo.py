"""Repository for the uploaded_files table."""

from collections.abc import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.session_tables import UploadedFileTable
from src.db.repositories.base import GenericRepository


class UploadRepository(GenericRepository[UploadedFileTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(UploadedFileTable, session)

    async def list_by_session(self, session_id: str) -> Sequence[UploadedFileTable]:
        stmt = (
            select(UploadedFileTable)
            .where(UploadedFileTable.session_id == session_id)
            .order_by(UploadedFileTable.uploaded_at)
        )
        result = await self._session.exec(stmt)
        return result.all()

    async def delete_by_session(self, session_id: str) -> int:
        """Delete all uploads for a session. Returns count of deleted rows."""
        rows = await self.list_by_session(session_id)
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()
        return len(rows)
