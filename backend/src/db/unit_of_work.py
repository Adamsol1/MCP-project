"""Unit of Work — wraps an AsyncSession and exposes all repositories.

Usage in FastAPI endpoints::

    async def my_endpoint(uow: UnitOfWork = Depends(get_uow)):
        session = await uow.sessions.get(session_id)
        ...
        await uow.commit()
"""

from collections.abc import AsyncGenerator

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.engine import get_knowledge_session_factory, get_sessions_session_factory
from src.db.repositories.analysis_repo import AnalysisSessionRepository
from src.db.repositories.collection_repo import CollectionAttemptRepository
from src.db.repositories.knowledge_repo import KnowledgeRepository
from src.db.repositories.processing_repo import ProcessingAttemptRepository
from src.db.repositories.research_log_repo import ResearchLogRepository
from src.db.repositories.session_repo import SessionRepository
from src.db.repositories.upload_repo import UploadRepository


class UnitOfWork:
    """Groups all sessions.db repositories under a single transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self.sessions = SessionRepository(session)
        self.collection_attempts = CollectionAttemptRepository(session)
        self.processing_attempts = ProcessingAttemptRepository(session)
        self.uploads = UploadRepository(session)
        self.analysis_sessions = AnalysisSessionRepository(session)
        self.research_logs = ResearchLogRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()


class KnowledgeUnitOfWork:
    """Groups knowledge.db repositories under a single transaction."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self.knowledge = KnowledgeRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()


# ---------------------------------------------------------------------------
# FastAPI dependency providers
# ---------------------------------------------------------------------------


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """Yield a UnitOfWork backed by a fresh sessions.db AsyncSession."""
    factory = get_sessions_session_factory()
    async with factory() as session:
        uow = UnitOfWork(session)
        yield uow


async def get_knowledge_uow() -> AsyncGenerator[KnowledgeUnitOfWork, None]:
    """Yield a KnowledgeUnitOfWork backed by a fresh knowledge.db AsyncSession."""
    factory = get_knowledge_session_factory()
    async with factory() as session:
        uow = KnowledgeUnitOfWork(session)
        yield uow
