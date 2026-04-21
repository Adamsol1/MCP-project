"""Repository for the knowledge_resources table."""

import json
from collections.abc import Sequence

from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.knowledge_tables import KnowledgeResourceTable
from src.db.repositories.base import GenericRepository


class KnowledgeRepository(GenericRepository[KnowledgeResourceTable]):
    def __init__(self, session: AsyncSession):
        super().__init__(KnowledgeResourceTable, session)

    async def search(
        self, scan_text: str, limit: int = 5
    ) -> Sequence[KnowledgeResourceTable]:
        """Match keywords in scan_text, return top matches sorted by priority."""
        all_resources = await self.list_all()
        text_lower = scan_text.lower()

        scored: list[tuple[int, KnowledgeResourceTable]] = []
        for resource in all_resources:
            keywords = json.loads(resource.keywords) if resource.keywords else []
            hits = sum(1 for kw in keywords if kw.lower() in text_lower)
            if hits > 0:
                scored.append((hits, resource))

        scored.sort(key=lambda x: (-x[0], x[1].priority))
        return [r for _, r in scored[:limit]]

    async def bulk_upsert(self, resources: list[KnowledgeResourceTable]) -> int:
        """Insert or update multiple knowledge resources. Returns count."""
        count = 0
        for resource in resources:
            existing = await self.get(resource.id)
            if existing:
                existing.category = resource.category
                existing.keywords = resource.keywords
                existing.priority = resource.priority
                existing.markdown_content = resource.markdown_content
                existing.citation = resource.citation
                existing.last_updated = resource.last_updated
                self._session.add(existing)
            else:
                self._session.add(resource)
            count += 1
        await self._session.flush()
        return count
