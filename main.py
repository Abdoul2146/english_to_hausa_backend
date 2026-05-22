import os
import torch
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
    # 1. Ensure required local storage directories exist on startup
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    os.makedirs(settings.MODEL_CACHE_DIR, exist_ok=True)
    
    # 2. Automatically build the database schema tables in PostgreSQL on startup
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # 3. Clean up GPU and model resources on shutdown
    from services.model_loader import ModelLoader
    ModelLoader.unload_all()

app = FastAPI(
    title="Hausa Translator API",
    description="FastAPI backend with three independent pipeline stages for Video to Audio, English to Hausa translation, and Hausa TTS synthesis",
    version="2.0.0",
    lifespan=lifespan
)

# Configure clean CORS policies
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to your Vercel or custom frontend origin
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register central routers
app.include_router(api_router)

@app.get("/health", tags=["Global Endpoints"])
def get_health_status(db: Session = Depends(get_db)):
    # 1. Simple db connection check
    try:
        db.execute(Base.metadata.tables["jobs"].select().limit(1))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
        
    gpu_available = torch.cuda.is_available()
    
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_name": torch.cuda.get_device_name(0) if gpu_available else None,
        "database": db_status,
        "storage": {
            "dir": settings.STORAGE_DIR,
            "cache_dir": settings.MODEL_CACHE_DIR
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
        
    # Cancel active jobs or clean up data directories
    clean_job_directory(job_id)
    
    db.delete(job)
    db.commit()
    
    return {"message": f"Job {job_id} cancelled and all local files cleaned up successfully."}
