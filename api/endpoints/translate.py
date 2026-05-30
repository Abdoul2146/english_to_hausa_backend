from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from api.deps import get_api_key, get_db
from schema.api_schemas import AudioTranscribeRequest, TextTranslateRequest, JobAcceptedResponse
from schema.job_schemas import JobResponse
import crud.job as crud_job
from services.transcriber import transcribe_audio
from services.translator import translate_text, translate_segments
from models.config import settings
from pathlib import Path
import httpx
import tempfile
import uuid
from typing import Optional, List

router = APIRouter(prefix="/translate", tags=["Stage 2: Translate"])

async def run_transcribe_pipeline(job_id: str, audio_url: str, db_session: Session):
    try:
        crud_job.update_job_status(db_session, job_id, "processing", "fetching_audio", 10.0, "Fetching input audio stream...")
        
        # Download audio to a temp location
        temp_dir = Path(tempfile.gettempdir())
        local_audio_path = temp_dir / f"input_{uuid.uuid4()}.wav"
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            local_audio_path.write_bytes(resp.content)
            
        crud_job.update_job_status(db_session, job_id, "processing", "whisper_inference", 50.0, "Running Whisper transcription...")
        transcription_result = transcribe_audio(local_audio_path)
        
        # Clean up temp file
        if local_audio_path.exists():
            local_audio_path.unlink()
            
        crud_job.complete_job(
            db_session,
            job_id,
            output_payload={
                "original_text": transcription_result["full_text"],
                "segments": transcription_result["segments"],
                "metadata": {
                    "word_count_original": len(transcription_result["full_text"].split()),
                    "model": "openai/whisper-small"
                }
            }
        )
    except Exception as e:
        crud_job.fail_job(db_session, job_id, str(e))

async def run_translate_pipeline(
    job_id: str, 
    text: Optional[str], 
    segments: Optional[List[dict]], 
    source_lang: str, 
    target_lang: str, 
    db_session: Session
):
    try:
        crud_job.update_job_status(db_session, job_id, "processing", "gemini_translation", 50.0, "Running Gemini translation...")
        
        if segments:
            # Segment-by-segment translation preserving timestamps
            translated_segments = translate_segments(segments, source_lang, target_lang)
            hausa_text = " ".join([seg["text"] for seg in translated_segments if seg["text"].strip()])
            
            crud_job.complete_job(
                db_session,
                job_id,
                output_payload={
                    "hausa_text": hausa_text,
                    "segments": translated_segments,
                    "metadata": {
                        "word_count_hausa": len(hausa_text.split()),
                        "model": "google/gemini-2.5-flash"
                    }
                }
            )
        elif text:
            # Plain text translation
            hausa_text = translate_text(text, source_lang, target_lang)
            
            crud_job.complete_job(
                db_session,
                job_id,
                output_payload={
                    "hausa_text": hausa_text,
                    "segments": [{"start": 0.0, "end": 0.0, "text": hausa_text}],
                    "metadata": {
                        "word_count_hausa": len(hausa_text.split()),
                        "model": "google/gemini-2.5-flash"
                    }
                }
            )
        else:
            raise ValueError("Either 'text' or 'segments' must be supplied for translation")
            
    except Exception as e:
        crud_job.fail_job(db_session, job_id, str(e))

@router.post("/transcribe", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_transcribe_job(
    request: AudioTranscribeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    db_job = crud_job.create_job(db, "translate", request.model_dump())
    background_tasks.add_task(run_transcribe_pipeline, db_job.id, request.audio_url, db)
    return JobAcceptedResponse(
        job_id=db_job.id,
        status="queued",
        message="Transcription started. Poll status at GET /api/translate/{job_id}/status"
    )

@router.post("", response_model=JobAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def create_translate_job(
    request: TextTranslateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    # Validate payload
    if not request.text and not request.segments:
        raise HTTPException(
            status_code=400,
            detail="Either 'text' or 'segments' field must be provided."
        )
        
    text = request.text
    if text and len(text) > settings.MAX_TEXT_LENGTH:
        text = text[:settings.MAX_TEXT_LENGTH]
        
    segments_payload = None
    if request.segments:
        # Convert Pydantic Segment models into standard dictionaries for processing
        segments_payload = [seg.model_dump() for seg in request.segments]
        
    db_job = crud_job.create_job(
        db, 
        "translate", 
        {
            "text": text, 
            "segments": segments_payload, 
            "source_language": request.source_language, 
            "target_language": request.target_language
        }
    )
    
    background_tasks.add_task(
        run_translate_pipeline, 
        db_job.id, 
        text,
        segments_payload,
        request.source_language, 
        request.target_language, 
        db
    )
    
    return JobAcceptedResponse(
        job_id=db_job.id,
        status="queued",
        message="Translation started. Poll status at GET /api/translate/{job_id}/status"
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

@router.get("/{job_id}/result", response_model=JobResponse)
def get_job_result(
    job_id: str,
    db: Session = Depends(get_db),
    _api_key: str = Depends(get_api_key)
):
    job = crud_job.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
    return job
