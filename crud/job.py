from sqlalchemy.orm import Session
from models.job import Job
from typing import Optional, Dict, Any

def create_job(db: Session, job_type: str, input_payload: Optional[Dict[str, Any]] = None) -> Job:
    db_job = Job(
        job_type=job_type,
        input_payload=input_payload,
        status="queued",
        stage="queued",
        progress_percent=0.0,
        message="Job queued"
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_job(db: Session, job_id: str) -> Optional[Job]:
    return db.query(Job).filter(Job.id == job_id).first()

def update_job_status(
    db: Session,
    job_id: str,
    status: str,
    stage: str,
    progress_percent: float,
    message: str,
    error_message: Optional[str] = None
) -> Optional[Job]:
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = status
        db_job.stage = stage
        db_job.progress_percent = progress_percent
        db_job.message = message
        if error_message is not None:
            db_job.error_message = error_message
        db.commit()
        db.refresh(db_job)
    return db_job

def complete_job(
    db: Session,
    job_id: str,
    output_payload: Dict[str, Any],
    media_url: Optional[str] = None,
    local_path: Optional[str] = None
) -> Optional[Job]:
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = "completed"
        db_job.stage = "completed"
        db_job.progress_percent = 100.0
        db_job.message = "Job completed successfully"
        db_job.output_payload = output_payload
        if media_url:
            db_job.media_url = media_url
        if local_path:
            db_job.local_path = local_path
        db.commit()
        db.refresh(db_job)
    return db_job

def fail_job(db: Session, job_id: str, error_message: str) -> Optional[Job]:
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = "failed"
        db_job.stage = "failed"
        db_job.message = "Job failed"
        db_job.error_message = error_message
        db.commit()
        db.refresh(db_job)
    return db_job
