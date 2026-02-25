import logging
from contextlib import asynccontextmanager
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
    """
    Method for logging lifecycle events of the FASTAPI application.
    The method will log:
        - Start of the application
        - End of the application

    Does not have any input of output
    """
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
    """
    Endpoint used for verifiying that the server runs.

    Returns: HTTP 200 OK
    """
    return {"status": "ok"}


@app.post("/api/import/upload")
async def upload_file(file: UploadFile = File(...)):
    """
        Endpoint for uploading a file to the server

        The endpoint will validate the filetype before saving it, to ensure filetype is legal

        The uploaded file will be saved in data/imports/

        Args:
            file UploadFile: The file that is being uploaded.

        Returns:
            A dict containing:
                - Status (str): "success" if upload was succesful
                - filename (str): The filename
                - path (str): The path where the file was saved.
                - e.g ( return {
                        "status": "success",
                        "filename": file.filename,
                        "path": saved_path.as_posix(),
                        }
    )

        Raises:
            - HTTPException 400: If the file is illegal
            - HTTPException 500: If an error occurs while saving
    """
    # Valdiate the uploaded file
    isValid = legal_file_upload(file.filename or "")
    # If the file is not valid retunr error
    if not isValid:
        raise HTTPException(status_code=400, detail="Illegal filetype")
    # If legal, try to save the file to given path
    try:
        saved_path = save_uploaded_file(file.file, file.filename or "", UPLOAD_PATH)
    # If failed raise error
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    # Return the dict
    return {
        "status": "success",
        "filename": file.filename,
        "path": saved_path.as_posix(),
    }
