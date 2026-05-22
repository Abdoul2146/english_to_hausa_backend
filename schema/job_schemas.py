from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any

class JobBase(BaseModel):
    job_type: str
    status: str
    stage: str
    progress_percent: float
    message: str
    error_message: Optional[str] = None
    input_payload: Optional[Dict[str, Any]] = None
    output_payload: Optional[Dict[str, Any]] = None
    media_url: Optional[str] = None

class JobResponse(JobBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
