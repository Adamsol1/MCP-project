import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from src.api.analysis import router as analysis_router
from src.api.dialogue import ensure_sessions_dir, evict_session
from src.api.dialogue import router as dialogue_router
from src.db.engine import get_knowledge_engine, get_sessions_engine, run_migrations, seed_knowledge
from src.db.unit_of_work import KnowledgeUnitOfWork, get_knowledge_uow
from src.db.unit_of_work import UnitOfWork, get_uow
from src.importers.session_uploads import (
    default_uploads_root,
    delete_session_upload,
    delete_session_uploads,
    list_session_uploads,
    save_session_upload,
)
from src.logging_config import setup_logging
from src.services.council.council_mcp_process import maybe_start_council_mcp, stop_council_mcp
from src.services.council.council_service import get_council_mcp_url
from src.services.reasearch_logger import ResearchLogger

load_dotenv()

setup_logging()

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifecycle: initialize DB engines and start council MCP."""
    migrations_applied = await asyncio.to_thread(run_migrations)
    if migrations_applied:
        await asyncio.to_thread(seed_knowledge)
    # Initialize DB engines so connectivity issues surface at startup
    get_sessions_engine()
    get_knowledge_engine()
    # Keep legacy sessions/ dir creation for dev-tool snapshot endpoints
    ensure_sessions_dir()
    council_mcp_process = await maybe_start_council_mcp(get_council_mcp_url())
    logger.info("Backend API started successfully: http://127.0.0.1:8000")
    print("Backend API started successfully: http://127.0.0.1:8000", flush=True)
    logger.info("Application started — database engines initialized")
    try:
        yield
    finally:
        await stop_council_mcp(council_mcp_process)
        logger.info("Application stopped")


app = FastAPI(lifespan=lifespan)


# Cors middleware to allow request from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Includes
app.include_router(analysis_router)
app.include_router(dialogue_router)

# Path for saving uploaded files.
UPLOADS_ROOT = Path(default_uploads_root())


@app.get("/api/knowledge/perspective-documents")
async def list_perspective_documents(
    kuow: KnowledgeUnitOfWork = Depends(get_knowledge_uow),
):
    """Return all active perspective documents grouped by perspective and section."""
    docs = await kuow.perspective_docs.list_all_active()
    grouped: dict[str, dict[str, list[dict]]] = {}
    for doc in docs:
        grouped.setdefault(doc.perspective, {}).setdefault(doc.section, []).append(
            {
                "id": doc.id,
                "title": doc.title,
                "source": doc.source,
                "date_published": doc.date_published.isoformat(),
            }
        )
    return {"perspective_documents": grouped}


# Health check endpoint used for checking system status
@app.get("/health")
async def check_health():
    """
    Endpoint used for verifiying that the server runs.

    Returns: HTTP 200 OK
    """
    return {"status": "ok"}


@app.post("/api/import/upload")
async def upload_file(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Endpoint for uploading a file to the server

    The endpoint validates filetype and stores files under:
    data/imports/{session_id}/

    Args:
        session_id str: Session identifier used to scope uploaded sources.
        file UploadFile: The file that is being uploaded.

    Returns:
        A dict containing:
            - Status (str): "success" if upload was succesful
            - file_upload_id (str): Stable ID used for list/delete/search
            - session_id (str): Session scope for this file
            - path (str): Stored file path
            - searchable (bool): Whether content can be searched as evidence

    Raises:
        - HTTPException 400: If request validation fails
        - HTTPException 500: If an error occurs while saving
    """
    try:
        result = save_session_upload(
            file_obj=file.file,
            filename=file.filename or "",
            session_id=session_id,
            uploads_root=UPLOADS_ROOT,
            mime_type=file.content_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"[upload_file] Failed to save upload for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to save uploaded file"
        ) from e
    logger.info(f"[upload_file] Saved '{file.filename}' for session {session_id}")
    return {"status": "success", **result}


@app.get("/api/import/files")
async def list_uploaded_files(session_id: str = Query(...)):
    """List all uploaded sources for a session."""
    try:
        files = list_session_uploads(session_id=session_id, uploads_root=UPLOADS_ROOT)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"[list_uploaded_files] Failed to list uploads for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to list uploaded files"
        ) from e

    return {
        "status": "success",
        "session_id": session_id,
        "files": files,
    }


@app.delete("/api/import/files/{file_upload_id}")
async def delete_uploaded_file(file_upload_id: str, session_id: str = Query(...)):
    """Delete one uploaded source and related parsed artifacts."""
    try:
        deleted = delete_session_upload(
            session_id=session_id,
            file_upload_id=file_upload_id,
            uploads_root=UPLOADS_ROOT,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(
            f"[delete_uploaded_file] Failed to delete {file_upload_id} for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to delete uploaded file"
        ) from e

    if not deleted:
        raise HTTPException(status_code=404, detail="Upload not found")
    logger.info(
        f"[delete_uploaded_file] Deleted {file_upload_id} for session {session_id}"
    )
    return Response(status_code=204)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, uow: UnitOfWork = Depends(get_uow)):
    """Delete all backend and MCP artifacts for a session.

    Removes:
    - Session DB rows (cascade delete across all tables)
    - All uploaded files and parsed artifacts (data/imports/{session_id}/)
    - Research and reasoning logs (data/outputs/research_log_* and reasoning_log_*)
    - Legacy: analysis state file and session JSON if they exist

    The DB delete is attempted first and committed independently of the file
    cleanups.  If file cleanup later fails we still return 204 — the
    authoritative DB row is already gone and stale files can be pruned later.
    """
    # --- DB delete (authoritative) ---
    try:
        existed = await evict_session(session_id, uow)
    except Exception as e:
        logger.error(
            f"[delete_session] DB delete failed for session {session_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail="Failed to delete session from DB"
        ) from e

    # --- Filesystem cleanups (best-effort) ---
    try:
        delete_session_uploads(session_id=session_id, uploads_root=UPLOADS_ROOT)

        outputs_dir = ResearchLogger(session_id=session_id).log_path.parent
        for log_name in (
            f"research_log_{session_id}.jsonl",
            f"reasoning_log_{session_id}.json",
        ):
            log_file = outputs_dir / log_name
            if log_file.exists():
                log_file.unlink()

        analysis_state_file = (
            Path(__file__).resolve().parents[2]
            / "sessions"
            / f"{session_id}.analysis.json"
        )
        if analysis_state_file.exists():
            analysis_state_file.unlink()

        legacy_session_file = (
            Path(__file__).resolve().parents[2] / "sessions" / f"{session_id}.json"
        )
        if legacy_session_file.exists():
            legacy_session_file.unlink()
    except Exception as e:
        # File cleanup failures do not mask the successful DB delete above.
        logger.warning(
            f"[delete_session] File cleanup failed for session {session_id}: {e}",
            exc_info=True,
        )

    logger.info(
        f"[delete_session] Deleted session {session_id} (db_existed={existed})"
    )
    return Response(status_code=204)
