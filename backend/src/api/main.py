from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.api.dialogue import router as dialogue_router
from src.importers.upload import legal_file_upload, save_uploaded_file
from src.logging_config import setup_logging

setup_logging()

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Application started")
    yield
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
app.include_router(dialogue_router)

# Path for saving uploaded files. This is fixed.
UPLOAD_PATH = Path("../data/imports/")


# Health check endpoint used for checking system status
@app.get("/health")
async def check_health():
    return {"status": "ok"}


@app.post("/api/import/upload")
async def upload_file(file: UploadFile = File(...)):
    isValid = legal_file_upload(file.filename or "")
    if not isValid:
        raise HTTPException(status_code=400, detail="Illegal filetype")
    try:
        saved_path = save_uploaded_file(file.file, file.filename or "", UPLOAD_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {
        "status": "success",
        "filename": file.filename,
        "path": saved_path.as_posix(),
    }
