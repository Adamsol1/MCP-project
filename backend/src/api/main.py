from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile

from fastapi.middleware.cors import CORSMiddleware

from src.importers.upload import legal_file_upload, save_uploaded_file

app = FastAPI()

#Cors middleware to allow request from frontend

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], #Port used by vite
    allow_credentials=True,
    allow_methods=["*"], #Allow all methods
    allow_headers=["*"], #Allow all headers
)

#Path for saving uploaded files. This is fixed.
UPLOAD_PATH = Path("../data/imports/")

#Health check endpoint used for checking system status
@app.get("/health")
async def check_health():
    return {"status": "ok"}

@app.post("/api/import/upload")
async def upload_file(file: UploadFile = File(...)):
    isValid = legal_file_upload(file.filename or "")
    #Check if filetype is illegal
    if not isValid:
        #If illegal, return error message
        raise HTTPException(status_code=400, detail="Illegal filetype")
    #If legal, return success message
    try:
        saved_path = save_uploaded_file(file.file, file.filename or "", UPLOAD_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "success", "filename": file.filename, "path": saved_path.as_posix()}
