from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from api.deps import get_api_key, get_db
from schema.api_schemas import VideoToAudioRequest, JobAcceptedResponse
from schema.job_schemas import JobResponse
import crud.job as crud_job
from services.downloader import download_video
from services.audio_extractor import extract_audio_wav
from services.file_manager import get_job_file_path
import cloudinary
import cloudinary.uploader
from models.config import settings
from pathlib import Path
import shutil

router = APIRouter(prefix="/video-to-audio", tags=["Stage 1: Video to Audio"])

def upload_to_cloudinary_if_enabled(local_path: Path) -> str:
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        res = cloudinary.uploader.upload(str(local_path), resource_type="video")
        return res.get("secure_url", "")
    return ""

async def run_video_to_audio_pipeline(job_id: str, url: str, max_duration: int, db_session: Session):
    try:
        # Step 1: Downloading
        crud_job.update_job_status(db_session, job_id, "processing", "downloading", 20.0, "Downloading video stream...")
        video_path = await download_video(job_id, url, max_duration)
        
        # Step 2: Extracting
        crud_job.update_job_status(db_session, job_id, "processing", "extracting", 60.0, "Extracting audio with ffmpeg...")
        audio_path = extract_audio_wav(job_id, video_path)
        
        # Step 3: Cloud upload / local save
        crud_job.update_job_status(db_session, job_id, "processing", "saving", 90.0, "Uploading/saving final audio file...")
        media_url = upload_to_cloudinary_if_enabled(audio_path)
        if not media_url:
            media_url = f"{settings.BASE_URL}/api/video-to-audio/{job_id}/download"
            
        crud_job.complete_job(
            db_session, 
            job_id, 
            output_payload={"format": "wav", "sample_rate": 16000},
            media_url=media_url,
            local_path=str(audio_path)
        )
    except Exception as e:
        crud_job.fail_job(db_session, job_id, str(e))

async def run_file_to_audio_pipeline(job_id: str, temp_video_path: Path, db_session: Session):
    try:
        # Step 1: Extracting directly from the saved file
        crud_job.update_job_status(db_session, job_id, "processing", "extracting", 50.0, "Extracting audio with ffmpeg...")
        audio_path = extract_audio_wav(job_id, temp_video_path)
        
        # Step 2: Cloud upload / local save
        crud_job.update_job_status(db_session, job_id, "processing", "saving", 80.0, "Uploading/saving final audio file...")
        media_url = upload_to_cloudinary_if_enabled(audio_path)
        if not media_url:
            media_url = f"{settings.BASE_URL}/api/video-to-audio/{job_id}/download"
            
        # Clean up intermediate uploaded video file
        if temp_video_path.exists():
            temp_video_path.unlink()
            
        crud_job.complete_job(
            db_session, 
            job_id, 
            output_payload={"format": "wav", "sample_rate": 16000},
            media_url=media_url,
            local_path=str(audio_path)
        )
    except Exception as e:
        # Cleanup uploaded video on failure
        if temp_video_path.exists():
            temp_video_path.unlink()
        crud_job.fail_job(db_session, job_id, str(e))

@router.post("", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_video_job(
    request: VideoToAudioRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    db_job = crud_job.create_job(db, "video-to-audio", request.model_dump())
    background_tasks.add_task(
        run_video_to_audio_pipeline, 
        db_job.id, 
        request.url, 
        request.max_duration_seconds or 7200,
        db
    )
    return JobAcceptedResponse(
        job_id=db_job.id,
        status="queued",
        message="Job accepted. Poll status at GET /api/video-to-audio/{job_id}/status"
    )

@router.post("/extract-file", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_file_extract_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    # Initialize a jobs payload
    db_job = crud_job.create_job(db, "video-to-audio", {"filename": file.filename})
    
    # Securely save the uploaded video to the job's directory
    uploaded_video_path = get_job_file_path(db_job.id, file.filename or "uploaded_video.mp4")
    
    with open(uploaded_video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(
        run_file_to_audio_pipeline,
        db_job.id,
        uploaded_video_path,
        db
    )
    
    return JobAcceptedResponse(
        job_id=db_job.id,
        status="queued",
        message="File received. Extracting audio from direct upload. Poll status at GET /api/video-to-audio/{job_id}/status"
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
def download_audio_file(
    job_id: str,
    db: Session = Depends(get_db)
):
    # Public download route doesn't require API key for general accessibility
    job = crud_job.get_job(db, job_id)
    if not job or not job.local_path:
        raise HTTPException(status_code=404, detail="Audio file not found or job not finished")
    
    path = Path(job.local_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Physical file does not exist")
        
    return FileResponse(
        path=str(path),
        media_type="audio/wav",
        filename=f"english_audio_{job_id}.wav"
    )
