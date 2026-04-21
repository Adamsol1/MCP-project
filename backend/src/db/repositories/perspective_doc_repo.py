"""Repository for the perspective_documents table."""

from collections.abc import Sequence

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.knowledge_tables import PerspectiveDocumentTable
from src.db.repositories.base import GenericRepository


class PerspectiveDocRepository(GenericRepository[PerspectiveDocumentTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(PerspectiveDocumentTable, session)

    async def list_by_perspective(
        self, perspective: str
    ) -> Sequence[PerspectiveDocumentTable]:
        """Return all active documents for a given perspective, ordered by section."""
        stmt = (
            select(PerspectiveDocumentTable)
            .where(PerspectiveDocumentTable.perspective == perspective.lower())
            .where(PerspectiveDocumentTable.is_active == True)  # noqa: E712
            .order_by(PerspectiveDocumentTable.section)
        )
        result = await self._session.exec(stmt)
        return result.all()

    async def list_all_active(self) -> Sequence[PerspectiveDocumentTable]:
        """Return all active documents across all perspectives."""
        stmt = (
            select(PerspectiveDocumentTable)
            .where(PerspectiveDocumentTable.is_active == True)  # noqa: E712
            .order_by(PerspectiveDocumentTable.perspective, PerspectiveDocumentTable.section)
        )
        result = await self._session.exec(stmt)
        return result.all()
