import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, JSON, Text
from models.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(50), nullable=False)  # video-to-audio, translate, tts
    status = Column(String(50), nullable=False, default="queued")  # queued, processing, completed, failed, cancelled
    stage = Column(String(100), nullable=False, default="queued")
    progress_percent = Column(Float, nullable=False, default=0.0)
    message = Column(String(255), nullable=False, default="Job queued")
    error_message = Column(Text, nullable=True)

    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)

    media_url = Column(String(1024), nullable=True)
    local_path = Column(String(1024), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
