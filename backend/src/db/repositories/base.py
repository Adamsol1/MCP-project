"""Generic base repository with common CRUD operations."""

from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=SQLModel)


class GenericRepository(Generic[T]):
    """Thin async wrapper around SQLModel session for a single table type."""

    def __init__(self, model: type[T], session: AsyncSession):
        self._model = model
        self._session = session

    async def get(self, pk) -> T | None:
        return await self._session.get(self._model, pk)

    async def create(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()

    async def list_all(self) -> Sequence[T]:
        result = await self._session.exec(select(self._model))
        return result.all()
