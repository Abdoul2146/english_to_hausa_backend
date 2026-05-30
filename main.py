import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from models.config import settings
from models.database import Base, engine
from route import api_router
from api.deps import get_api_key, get_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Hausa Translator API",
    description="FastAPI backend with three independent pipeline stages for Video to Audio, English to Hausa translation, and Hausa TTS synthesis",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)

@app.get("/health", tags=["Global Endpoints"])
def get_health_status(db: Session = Depends(get_db)):
    try:
        db.execute(Base.metadata.tables["jobs"].select().limit(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "gpu_available": False,
        "database": db_status,
        "storage": {
            "dir": settings.STORAGE_DIR,
        }
    }

@app.delete("/api/jobs/{job_id}", tags=["Global Endpoints"])
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    import crud.job as crud_job
    from services.file_manager import clean_job_directory

    job = crud_job.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    clean_job_directory(job_id)
    db.delete(job)
    db.commit()

    return {"message": f"Job {job_id} cancelled and all local files cleaned up successfully."}
