from pydantic import BaseModel
from typing import Optional, List

# ==========================================
# STAGE 1: Video to Audio Schemas
# ==========================================
class VideoToAudioRequest(BaseModel):
    url: str
    audio_quality: str = "good"
    max_duration_seconds: Optional[int] = 3600

# ==========================================
# STAGE 2: Translate Schemas
# ==========================================
class AudioTranscribeRequest(BaseModel):
    audio_url: str

class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str

class TextTranslateRequest(BaseModel):
    text: Optional[str] = None
    segments: Optional[List[TranscriptSegment]] = None
    source_language: str = "eng_Latn"
    target_language: str = "hau_Latn"

# ==========================================
# STAGE 3: TTS Schemas
# ==========================================
class TTSRequest(BaseModel):
    text: str
    speed: float = 1.0
    voice: str = "default"

# ==========================================
# Base Response
# ==========================================
class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str
    message: str
