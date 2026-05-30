from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from api.deps import get_api_key, get_db
from schema.api_schemas import TTSRequest, JobAcceptedResponse
from schema.job_schemas import JobResponse
import crud.job as crud_job
from services.tts_generator import generate_tts_wav
try:
    import cloudinary
    import cloudinary.uploader
    _cloudinary_available = True
except ImportError:
    _cloudinary_available = False
from models.config import settings
from pathlib import Path

router = APIRouter(prefix="/tts", tags=["Stage 3: Text to Speech"])

def upload_to_cloudinary_if_enabled(local_path: Path) -> str:
    if not _cloudinary_available:
        return ""
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        res = cloudinary.uploader.upload(str(local_path), resource_type="raw")
        return res.get("secure_url", "")
    return ""

async def run_tts_pipeline(job_id: str, text: str, speed: float, db_session: Session):
    try:
        crud_job.update_job_status(db_session, job_id, "processing", "synthesizing", 40.0, "Synthesizing speech with Google TTS...")
        output_wav = generate_tts_wav(job_id, text, speed)
        
        crud_job.update_job_status(db_session, job_id, "processing", "saving", 80.0, "Uploading/saving synthesized audio...")
        media_url = upload_to_cloudinary_if_enabled(output_wav)
        if not media_url:
            media_url = f"{settings.BASE_URL}/api/tts/{job_id}/download"
            
        crud_job.complete_job(
            db_session,
            job_id,
            output_payload={
                "character_count": len(text),
                "speed": speed,
                "voice": "default"
            },
            media_url=media_url,
            local_path=str(output_wav)
        )
    except Exception as e:
        crud_job.fail_job(db_session, job_id, str(e))

@router.post("", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_tts_job(
    request: TTSRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    text = request.text
    if len(text) > settings.MAX_TTS_TEXT_LENGTH:
        text = text[:settings.MAX_TTS_TEXT_LENGTH]
        
    db_job = crud_job.create_job(db, "tts", {"text": text, "speed": request.speed, "voice": request.voice})
    background_tasks.add_task(run_tts_pipeline, db_job.id, text, request.speed, db)
    return JobAcceptedResponse(
        job_id=db_job.id,
        status="queued",
        message="TTS generation started. Poll status at GET /api/tts/{job_id}/status"
    )

@router.get("/{job_id}/status", response_model=JobResponse)
def get_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    job = crud_job.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/{job_id}/download")
def download_tts_file(
    job_id: str,
    db: Session = Depends(get_db)
):
    job = crud_job.get_job(db, job_id)
    if not job or not job.local_path:
        raise HTTPException(status_code=404, detail="Synthesized file not found or job not finished")
        
    path = Path(job.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Physical file does not exist")
        
    return FileResponse(
        path=str(path),
        media_type="audio/wav",
        filename=f"haus_audio_{job_id}.wav"
    )
