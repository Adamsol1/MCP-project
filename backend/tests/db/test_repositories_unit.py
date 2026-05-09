import json
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models.knowledge_tables import KnowledgeResourceTable, PerspectiveDocumentTable
from src.db.models.session_tables import (
    AnalysisSessionTable,
    CollectionAttemptTable,
    ProcessingAttemptTable,
    ResearchLogEntryTable,
    SessionTable,
    UploadedFileTable,
)
from src.db.repositories.analysis_repo import AnalysisSessionRepository
from src.db.repositories.base import GenericRepository
from src.db.repositories.collection_repo import CollectionAttemptRepository
from src.db.repositories import collection_status_repo as collection_status_module
from src.db.repositories.collection_status_repo import CollectionStatusRepository
from src.db.repositories.knowledge_repo import KnowledgeRepository
from src.db.repositories.perspective_doc_repo import PerspectiveDocRepository
from src.db.repositories.processing_repo import ProcessingAttemptRepository
from src.db.repositories.research_log_repo import ResearchLogRepository
from src.db.repositories.session_repo import SessionRepository
from src.db.repositories.upload_repo import UploadRepository


async def _make_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False)


def _create_collection_status_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE collection_status (
            session_id TEXT PRIMARY KEY,
            status TEXT,
            current_source TEXT,
            current_activity TEXT,
            sources TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()


@pytest.mark.asyncio
async def test_generic_repository_crud_and_list_all():
    async with await _make_session() as session:
        repo = GenericRepository(SessionTable, session)
        row = await repo.create(SessionTable(id="session-1"))

        assert await repo.get("session-1") == row

        row.direction_state = "gathering"
        updated = await repo.update(row)
        all_rows = await repo.list_all()

        assert updated.direction_state == "gathering"
        assert [r.id for r in all_rows] == ["session-1"]

        await repo.delete(row)

        assert await repo.get("session-1") is None


@pytest.mark.asyncio
async def test_collection_and_processing_repositories_auto_number_attempts():
    async with await _make_session() as session:
        await GenericRepository(SessionTable, session).create(SessionTable(id="session-1"))
        collection_repo = CollectionAttemptRepository(session)
        processing_repo = ProcessingAttemptRepository(session)

        first_collection = await collection_repo.append("session-1", "pir", "raw-1")
        second_collection = await collection_repo.append("session-1", "pir", "raw-2")
        first_processing = await processing_repo.append("session-1", "pir", "result-1")
        second_processing = await processing_repo.append("session-1", "pir", "result-2")

        assert first_collection.attempt_number == 1
        assert second_collection.attempt_number == 2
        assert first_processing.attempt_number == 1
        assert second_processing.attempt_number == 2
        assert [a.raw_response for a in await collection_repo.get_all("session-1")] == [
            "raw-1",
            "raw-2",
        ]
        assert (await collection_repo.get_latest("session-1")).raw_response == "raw-2"
        assert [a.raw_result for a in await processing_repo.get_all("session-1")] == [
            "result-1",
            "result-2",
        ]
        assert (await processing_repo.get_latest("session-1")).raw_result == "result-2"


@pytest.mark.asyncio
async def test_analysis_repository_get_or_create_and_save_methods_update_same_row():
    async with await _make_session() as session:
        await GenericRepository(SessionTable, session).create(SessionTable(id="session-1"))
        repo = AnalysisSessionRepository(session)

        created = await repo.get_or_create("session-1")
        fetched = await repo.get_or_create("session-1")
        with_draft = await repo.save_draft(
            "session-1",
            processing_result_json='{"findings": []}',
            analysis_draft_json='{"summary": "draft"}',
        )
        with_note = await repo.save_council_note(
            "session-1",
            council_note_json='{"summary": "council"}',
        )

        assert fetched.id == created.id
        assert with_draft.id == created.id
        assert with_note.id == created.id
        assert (await repo.get_by_session("session-1")).latest_council_note == (
            '{"summary": "council"}'
        )


@pytest.mark.asyncio
async def test_knowledge_repository_search_ranks_keyword_hits_then_priority_and_upserts():
    async with await _make_session() as session:
        repo = KnowledgeRepository(session)
        await repo.bulk_upsert(
            [
                KnowledgeResourceTable(
                    id="telecom-low",
                    category="infrastructure",
                    keywords=json.dumps(["telecom"]),
                    priority=1,
                    markdown_content="old",
                ),
                KnowledgeResourceTable(
                    id="telecom-identity",
                    category="identity",
                    keywords=json.dumps(["telecom", "identity"]),
                    priority=9,
                    markdown_content="identity content",
                ),
                KnowledgeResourceTable(
                    id="unmatched",
                    category="other",
                    keywords=json.dumps(["maritime"]),
                    priority=1,
                    markdown_content="maritime content",
                ),
            ]
        )

        matches = await repo.search("Telecom identity access", limit=2)
        updated_count = await repo.bulk_upsert(
            [
                KnowledgeResourceTable(
                    id="telecom-low",
                    category="updated",
                    keywords=json.dumps(["telecom", "access"]),
                    priority=5,
                    markdown_content="new",
                    citation='{"title": "Updated"}',
                )
            ]
        )
        updated = await repo.get("telecom-low")

        assert [m.id for m in matches] == ["telecom-identity", "telecom-low"]
        assert updated_count == 1
        assert updated.category == "updated"
        assert updated.markdown_content == "new"
        assert updated.citation == '{"title": "Updated"}'


@pytest.mark.asyncio
async def test_perspective_doc_repository_filters_active_docs_and_orders_by_section():
    async with await _make_session() as session:
        repo = PerspectiveDocRepository(session)
        await repo.create(
            PerspectiveDocumentTable(
                id="norway-military",
                perspective="norway",
                section="military",
                title="Military",
            )
        )
        await repo.create(
            PerspectiveDocumentTable(
                id="norway-economic",
                perspective="norway",
                section="economic",
                title="Economic",
            )
        )
        await repo.create(
            PerspectiveDocumentTable(
                id="norway-inactive",
                perspective="norway",
                section="political",
                title="Inactive",
                is_active=False,
            )
        )
        await repo.create(
            PerspectiveDocumentTable(
                id="us-political",
                perspective="us",
                section="political",
                title="Political",
            )
        )

        norway_docs = await repo.list_by_perspective("NORWAY")
        active_docs = await repo.list_all_active()

        assert [doc.id for doc in norway_docs] == ["norway-economic", "norway-military"]
        assert [doc.id for doc in active_docs] == [
            "norway-economic",
            "norway-military",
            "us-political",
        ]


@pytest.mark.asyncio
async def test_research_log_and_upload_repositories_return_session_scoped_rows_in_order():
    async with await _make_session() as session:
        await GenericRepository(SessionTable, session).create(SessionTable(id="session-1"))
        await GenericRepository(SessionTable, session).create(SessionTable(id="session-2"))
        log_repo = ResearchLogRepository(session)
        upload_repo = UploadRepository(session)
        early = datetime(2026, 1, 1, tzinfo=UTC)
        later = datetime(2026, 1, 2, tzinfo=UTC)

        late_log = await log_repo.append("session-1", "ai_generation", "analysis", "{}")
        early_log = await log_repo.append("session-1", "user_action", "direction", "{}")
        late_log.timestamp = later
        early_log.timestamp = early
        session.add(late_log)
        session.add(early_log)
        await upload_repo.create(
            UploadedFileTable(
                id="upload-late",
                session_id="session-1",
                original_filename="late.pdf",
                uploaded_at=later,
            )
        )
        await upload_repo.create(
            UploadedFileTable(
                id="upload-early",
                session_id="session-1",
                original_filename="early.pdf",
                uploaded_at=early,
            )
        )
        await upload_repo.create(
            UploadedFileTable(id="other-session", session_id="session-2")
        )
        await session.flush()

        logs = await log_repo.get_all("session-1")
        uploads = await upload_repo.list_by_session("session-1")
        deleted_count = await upload_repo.delete_by_session("session-1")
        remaining_uploads = await upload_repo.list_all()

        assert [log.entry_type for log in logs] == ["user_action", "ai_generation"]
        assert [upload.id for upload in uploads] == ["upload-early", "upload-late"]
        assert deleted_count == 2
        assert [upload.id for upload in remaining_uploads] == ["other-session"]


@pytest.mark.asyncio
async def test_session_repository_upsert_preserves_created_at_and_delete_cascade_cleans_children():
    async with await _make_session() as session:
        repo = SessionRepository(session)
        original_created_at = datetime(2026, 1, 1, tzinfo=UTC)
        await repo.upsert(
            SessionTable(
                id="session-1",
                created_at=original_created_at,
                direction_state="initial",
            )
        )

        updated = await repo.upsert(
            SessionTable(id="session-1", direction_state="complete", question_count=3)
        )
        await GenericRepository(CollectionAttemptTable, session).create(
            CollectionAttemptTable(session_id="session-1", raw_response="raw")
        )
        await GenericRepository(ProcessingAttemptTable, session).create(
            ProcessingAttemptTable(session_id="session-1", raw_result="processed")
        )
        await GenericRepository(UploadedFileTable, session).create(
            UploadedFileTable(id="upload-1", session_id="session-1")
        )
        await GenericRepository(AnalysisSessionTable, session).create(
            AnalysisSessionTable(session_id="session-1")
        )
        await GenericRepository(ResearchLogEntryTable, session).create(
            ResearchLogEntryTable(session_id="session-1", entry_type="ai_generation")
        )

        deleted_existing = await repo.delete_cascade("session-1")
        deleted_missing = await repo.delete_cascade("session-1")

        assert updated.created_at.replace(tzinfo=UTC) == original_created_at
        assert updated.direction_state == "complete"
        assert updated.question_count == 3
        assert deleted_existing is True
        assert deleted_missing is False
        assert await repo.exists("session-1") is False
        assert await GenericRepository(CollectionAttemptTable, session).list_all() == []
        assert await GenericRepository(ProcessingAttemptTable, session).list_all() == []
        assert await GenericRepository(UploadedFileTable, session).list_all() == []
        assert await GenericRepository(AnalysisSessionTable, session).list_all() == []
        assert await GenericRepository(ResearchLogEntryTable, session).list_all() == []


def test_collection_status_repository_upserts_gets_and_deletes_status(monkeypatch):
    monkeypatch.setenv("SESSIONS_DB_PATH", ":memory:")
    monkeypatch.setattr(collection_status_module, "_conn", None)
    conn = collection_status_module._get_connection()
    _create_collection_status_schema(conn)
    repo = CollectionStatusRepository()

    repo.upsert(
        "session-1",
        {
            "status": "collecting",
            "current_source": "Knowledge Bank",
            "current_activity": "Reading resource",
            "sources": {"Knowledge Bank": {"count": 1}},
        },
    )
    first = repo.get("session-1")
    repo.upsert(
        "session-1",
        {
            "status": "complete",
            "current_source": None,
            "current_activity": None,
            "sources": {"Knowledge Bank": {"count": 2}},
        },
    )
    second = repo.get("session-1")
    repo.delete("session-1")

    assert first["status"] == "collecting"
    assert first["sources"] == {"Knowledge Bank": {"count": 1}}
    assert second["status"] == "complete"
    assert second["current_source"] is None
    assert second["sources"] == {"Knowledge Bank": {"count": 2}}
    assert repo.get("session-1") is None
    conn.close()
    collection_status_module._conn = None
