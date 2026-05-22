# Hausa Translator — Backend Pipeline Document v2.0

## 1. Overview

FastAPI backend with **three independent pipeline stages**, each exposed as its own API. Users can chain them or use any stage standalone. Runs on Lightning AI free tier (T4 GPU, 16GB RAM, 50GB persistent storage) with local development support.

**Tech Stack:** FastAPI, Uvicorn, Transformers, Whisper, yt-dlp, ffmpeg, MMS TTS
**Python Version:** 3.11
**Package Manager:** `uv`

---

## 2. Pipeline Architecture

Three separate pipelines, each independently callable:

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   VIDEO → AUDIO     │    │     TRANSLATE       │    │        TTS          │
│                     │    │                     │    │                     │
│  [ URL Input ]      │    │  [ Audio or Text ]  │    │  [ Hausa Text ]     │
│       │             │    │       │             │    │       │             │
│       ▼             │    │       ▼             │    │       ▼             │
│  yt-dlp download    │    │  [If audio]         │    │  MMS TTS (hau)      │
│       │             │    │  Whisper transcribe │    │       │             │
│       ▼             │    │       │             │    │       ▼             │
│  ffmpeg extract     │    │       ▼             │    │  Concat segments    │
│       │             │    │  NLLB eng→hausa     │    │       │             │
│       ▼             │    │       │             │    │       ▼             │
│  English audio file │    │       ▼             │    │  Hausa audio file   │
│  (.wav 16kHz)       │    │  Hausa text         │    │                     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

**Chaining:** Frontend passes output from one stage as input to the next via URLs or text.

---

## 3. Stage 1: Video → Audio

### Purpose
Download video from URL and extract clean English audio track.

### Tools
- **Download:** `yt-dlp` (Python package)
- **Extract:** `ffmpeg` (system binary)

### Input
```json
{
  "url": "https://youtube.com/watch?v=...",
  "audio_quality": "good",
  "max_duration_seconds": 3600
}
```

### Process
1. Validate URL format and accessibility
2. `yt-dlp` downloads best audio stream (or video+audio if needed)
3. `ffmpeg` converts to WAV 16kHz mono
4. Validate output file exists and is playable

### Output
```json
{
  "job_id": "uuid",
  "status": "completed",
  "audio_url": "/api/video-to-audio/{job_id}/download",
  "metadata": {
    "original_title": "Documentary Title",
    "duration_seconds": 1800,
    "file_size_bytes": 57600000,
    "format": "wav",
    "sample_rate": 16000,
    "channels": 1
  }
}
```

### Errors
| Error | HTTP | Message |
|-------|------|---------|
| Invalid URL | 400 | "URL must be a valid YouTube, Vimeo, or direct video link" |
| Video unavailable | 400 | "Video is private, removed, or region-blocked" |
| Too long | 400 | "Video exceeds maximum duration of {max} minutes" |
| Download failed | 500 | "Failed to download video after 3 retries" |
| Extract failed | 500 | "Failed to extract audio stream" |

---

## 4. Stage 2: Translate

### Purpose
English audio or text → Hausa text.

### Sub-stages

#### 4.1 Transcribe (Audio → English Text)
**Model:** `openai/whisper-small` (244MB)
**Framework:** Hugging Face `transformers` pipeline

**Input:** Audio file (WAV, MP3, M4A, OGG) or URL to audio file
**Config:**
- Language: `en`
- Chunk length: 30s
- Batch size: 16 (GPU) / 1 (CPU)
- Device: `cuda` if available

**Output format:**
```json
{
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "In this documentary..."},
    {"start": 5.2, "end": 12.8, "text": "we explore the rich..."}
  ],
  "full_text": "In this documentary we explore the rich...",
  "language": "en"
}
```

**Performance:**
- T4 GPU: ~0.5x real-time
- CPU: ~2-4x real-time

#### 4.2 Translate (English Text → Hausa Text)
**Model:** `facebook/nllb-200-distilled-600M` (600MB)
**Framework:** Hugging Face `transformers`

**Input:** English text or transcript segments
**Config:**
- Source: `eng_Latn`
- Target: `hau_Latn`
- Max tokens: 256 per segment
- Batch size: 8 (GPU) / 2 (CPU)

**Segment strategy:**
- If input has timestamps (from Whisper): translate segment-by-segment, preserve timing
- If plain text: split into chunks (~200 words), translate each, reassemble

**Output format:**
```json
{
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "A wannan takardar..."},
    {"start": 5.2, "end": 12.8, "text": "za mu bincika..."}
  ],
  "full_text": "A wannan takardar za mu bincika...",
  "source_language": "eng_Latn",
  "target_language": "hau_Latn"
}
```

**Performance:**
- T4 GPU: ~2-5s per segment
- CPU: ~10-30s per segment

### Combined Endpoint Behavior
When user submits audio with `transcribe_first: true`:
1. Transcribe audio → English text
2. Translate English text → Hausa text
3. Return both original and Hausa

When user submits text directly:
1. Skip transcription
2. Translate directly to Hausa

### Input
```json
// Audio input
{
  "audio_url": "https://backend.com/audio/123.wav",
  "transcribe_first": true
}

// OR text input
{
  "text": "In this documentary we explore...",
  "source_language": "eng_Latn",
  "target_language": "hau_Latn"
}
```

### Output
```json
{
  "job_id": "uuid",
  "status": "completed",
  "original_text": "In this documentary...",
  "hausa_text": "A wannan takardar...",
  "segments": [...],
  "metadata": {
    "word_count_original": 1500,
    "word_count_hausa": 1200,
    "processing_time_seconds": 180,
    "model": "nllb-200-distilled-600M"
  }
}
```

---

## 5. Stage 3: TTS (Text-to-Speech)

### Purpose
Hausa text → spoken Hausa audio.

### Model
**Primary:** `facebook/mms-tts-hau` (MMS TTS, Hausa voice)
**Framework:** Hugging Face `transformers` VitsModel

### Input
```json
{
  "text": "A wannan takardar za mu bincika al'adun gargajiya...",
  "speed": 1.0,
  "voice": "default"
}
```

### Process
1. Split long text into chunks (~400 chars) at sentence boundaries
2. Generate audio for each chunk using MMS TTS
3. Concatenate chunks with ffmpeg
4. Validate output duration matches expected

### Output
```json
{
  "job_id": "uuid",
  "status": "completed",
  "audio_url": "/api/tts/{job_id}/download",
  "metadata": {
    "duration_seconds": 45.2,
    "character_count": 450,
    "speed": 1.0,
    "voice": "default",
    "file_size_bytes": 3616000
  }
}
```

### Fallback (if MMS quality is poor)
**Google Cloud Text-to-Speech** free tier:
- 1M characters/month free
- Language codes: `ha-NG` (Nigeria), `ha-NE` (Niger)
- Requires `GOOGLE_APPLICATION_CREDENTIALS` env var
- Better quality but requires API key setup

---

## 6. API Endpoints

### 6.1 Video → Audio

#### `POST /api/video-to-audio`
Submit video URL for audio extraction.

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "audio_quality": "good",
  "max_duration_seconds": 3600
}
```

**Response (202):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job accepted. Poll /api/video-to-audio/{job_id}/status for progress."
}
```

---

#### `GET /api/video-to-audio/{job_id}/status`
Check extraction progress.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "extracting",
  "stage": "ffmpeg_extract",
  "progress_percent": 65,
  "message": "Extracting audio track (65%)...",
  "created_at": "2026-05-21T10:00:00Z",
  "updated_at": "2026-05-21T10:02:15Z"
}
```

**Status values:** `queued` | `downloading` | `extracting` | `completed` | `failed`

---

#### `GET /api/video-to-audio/{job_id}/download`
Download extracted audio file.

**Response:** `audio/wav` stream
**Headers:**
- `Content-Disposition: attachment; filename="english_audio_{job_id}.wav"`
- `X-Original-Title: "Documentary Title"`

---

### 6.2 Translate

#### `POST /api/transcribe`
Transcribe English audio to text.

**Request:** Multipart form with `audio` file OR JSON with `audio_url`

**Response (202):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Transcription started."
}
```

---

#### `POST /api/translate`
Translate English text to Hausa.

**Request:**
```json
{
  "text": "In this documentary...",
  "source_language": "eng_Latn",
  "target_language": "hau_Latn"
}
```

**Response (202):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Translation started."
}
```

---

#### `GET /api/translate/{job_id}/status`
Check transcription or translation progress.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "translating",
  "stage": "nllb_inference",
  "progress_percent": 40,
  "message": "Translating segment 8 of 20...",
  "partial_result": {
    "segments_completed": 8,
    "hausa_text_so_far": "A wannan takardar..."
  }
}
```

---

#### `GET /api/translate/{job_id}/result`
Get final result (available when status is `completed`).

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "original_text": "In this documentary...",
  "hausa_text": "A wannan takardar...",
  "segments": [...],
  "metadata": {...}
}
```

---

### 6.3 TTS

#### `POST /api/tts`
Generate Hausa speech from text.

**Request:**
```json
{
  "text": "A wannan takardar...",
  "speed": 1.0,
  "voice": "default"
}
```

**Response (202):**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "TTS generation started."
}
```

---

#### `GET /api/tts/{job_id}/status`
Check TTS progress.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "synthesizing",
  "progress_percent": 60,
  "message": "Generating audio chunk 3 of 5...",
  "created_at": "2026-05-21T10:00:00Z",
  "updated_at": "2026-05-21T10:01:30Z"
}
```

---

#### `GET /api/tts/{job_id}/download`
Download generated Hausa audio.

**Response:** `audio/wav` stream
**Headers:**
- `Content-Disposition: attachment; filename="haus_audio_{job_id}.wav"`

---

### 6.4 Global Endpoints

#### `GET /health`
Backend health and model status.

**Response:**
```json
{
  "status": "healthy",
  "gpu_available": true,
  "gpu_name": "NVIDIA T4",
  "models_loaded": {
    "whisper": "openai/whisper-small",
    "translator": "facebook/nllb-200-distilled-600M",
    "tts": "facebook/mms-tts-hau"
  },
  "storage": {
    "total_gb": 50,
    "used_gb": 12.4,
    "free_gb": 37.6
  }
}
```

---

#### `DELETE /api/jobs/{job_id}`
Cancel active job or clean up completed job.

**Response:**
```json
{"message": "Job cancelled and files cleaned up"}
```

---

## 7. Job State Management

### In-Memory Store

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid

class JobType(Enum):
    VIDEO_TO_AUDIO = "video-to-audio"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    TTS = "tts"

class JobStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Job:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    job_type: JobType = JobType.VIDEO_TO_AUDIO
    status: JobStatus = JobStatus.QUEUED
    stage: str = "queued"
    progress_percent: float = 0.0
    message: str = "Job queued"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Inputs
    input_url: Optional[str] = None
    input_text: Optional[str] = None
    input_audio_path: Optional[str] = None

    # Outputs
    output_audio_path: Optional[str] = None
    output_text_path: Optional[str] = None
    output_json: Optional[Dict[str, Any]] = None

    # Metadata
    original_title: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None

    # Partial results (for streaming progress)
    partial_result: Optional[Dict[str, Any]] = None
```

**Storage:** Python `dict[str, Job]` — sufficient for 5 users.
**Cleanup:** Background task removes jobs + files older than 24 hours.

---

## 8. File System Layout

```
project_root/
├── src/
│   └── hausa_translator_api/
│       ├── __init__.py
│       ├── main.py                  # FastAPI app, routes, lifespan
│       ├── config.py                # Settings, env vars
│       │
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── video_to_audio.py    # /api/video-to-audio/*
│       │   ├── translate.py         # /api/transcribe, /api/translate/*
│       │   └── tts.py               # /api/tts/*
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── downloader.py        # yt-dlp wrapper
│       │   ├── audio_extractor.py   # ffmpeg wrapper
│       │   ├── transcriber.py       # Whisper inference
│       │   ├── translator.py        # NLLB inference
│       │   ├── tts_generator.py     # MMS TTS inference
│       │   └── file_manager.py      # Cleanup, validation
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   └── model_manager.py     # Lazy loading, GPU management
│       │
│       └── schemas/
│           ├── __init__.py
│           └── api_schemas.py       # Pydantic request/response models
│
├── downloads/                       # Job working directories (gitignored)
│   └── {job_id}/
│       ├── input_video.*            # Downloaded video
│       ├── audio.wav                # Extracted audio
│       ├── transcript.json          # Whisper output
│       ├── translation.json         # NLLB output
│       ├── tts_segments/            # Individual TTS chunks
│       │   ├── 000.wav
│       │   └── 001.wav
│       ├── output_hausa.wav         # Final TTS output
│       └── checkpoint.json          # Resume state
│
├── models_cache/                    # Hugging Face weights (gitignored)
│   ├── openai--whisper-small/
│   ├── facebook--nllb-200-distilled-600M/
│   └── facebook--mms-tts-hau/
│
├── pyproject.toml
├── uv.lock
└── .env.example
```

---

## 9. Model Loading Strategy

### Lazy Singleton Pattern

Models load once on first request, stay in memory:

```python
import torch
from transformers import pipeline, VitsModel, VitsTokenizer

class ModelManager:
    _cache = {}

    @classmethod
    def get_whisper(cls):
        if "whisper" not in cls._cache:
            device = 0 if torch.cuda.is_available() else -1
            cls._cache["whisper"] = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-small",
                device=device,
                torch_dtype=torch.float16 if device == 0 else torch.float32
            )
        return cls._cache["whisper"]

    @classmethod
    def get_translator(cls):
        if "translator" not in cls._cache:
            device = 0 if torch.cuda.is_available() else -1
            cls._cache["translator"] = pipeline(
                "translation",
                model="facebook/nllb-200-distilled-600M",
                device=device,
                torch_dtype=torch.float16 if device == 0 else torch.float32
            )
        return cls._cache["translator"]

    @classmethod
    def get_tts(cls):
        if "tts" not in cls._cache:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            cls._cache["tts"] = {
                "model": VitsModel.from_pretrained("facebook/mms-tts-hau").to(device),
                "tokenizer": VitsTokenizer.from_pretrained("facebook/mms-tts-hau")
            }
        return cls._cache["tts"]

    @classmethod
    def unload_all(cls):
        cls._cache.clear()
        torch.cuda.empty_cache()
```

**Memory Budget (T4 16GB):**
- Whisper small: ~1GB
- NLLB 600M: ~2GB
- MMS TTS: ~500MB
- **Total: ~3.5GB** — safe margin for batch processing

---

## 10. Error Handling & Resilience

| Failure Point | Strategy |
|---------------|----------|
| **Download fails** | Retry 3x with exponential backoff (2s, 5s, 10s) |
| **GPU OOM** | Fall back to CPU for that stage, log warning, notify user |
| **Model download fails** | Resume from partial download, retry from HF |
| **Lightning AI restart** | Save checkpoint after each stage, auto-resume on boot |
| **Long input (>limits)** | Reject at API with clear limit message |
| **TTS chunk fails** | Skip chunk, continue with rest, note in output |
| **Translation segment fails** | Retry once, then skip with placeholder |

### Checkpointing for Restarts

```python
import json
from pathlib import Path

def save_checkpoint(job_id: str, stage: str, data: dict):
    path = Path(f"downloads/{job_id}/checkpoint.json")
    checkpoint = {
        "stage": stage,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    path.write_text(json.dumps(checkpoint, indent=2))

def load_checkpoint(job_id: str) -> Optional[dict]:
    path = Path(f"downloads/{job_id}/checkpoint.json")
    if path.exists():
        return json.loads(path.read_text())
    return None

def resume_job(job_id: str):
    checkpoint = load_checkpoint(job_id)
    if checkpoint:
        stage = checkpoint["stage"]
        if stage == "downloaded":
            return resume_from_extract(job_id, checkpoint["data"])
        elif stage == "extracted":
            return resume_from_transcribe(job_id, checkpoint["data"])
        # ... etc
```

On app startup, scan `downloads/` for incomplete jobs and resume.

---

## 11. Background Processing

### FastAPI BackgroundTasks

Sufficient for 5 users. Each stage runs as a background task.

```python
from fastapi import BackgroundTasks

@router.post("/api/video-to-audio")
async def create_video_job(
    request: VideoToAudioRequest,
    background_tasks: BackgroundTasks
):
    job = Job(job_type=JobType.VIDEO_TO_AUDIO, input_url=request.url)
    jobs[job.job_id] = job

    background_tasks.add_task(run_video_pipeline, job.job_id)
    return {"job_id": job.job_id, "status": "queued"}

async def run_video_pipeline(job_id: str):
    job = jobs[job_id]
    try:
        # Stage 1: Download
        update_job(job_id, status=JobStatus.PROCESSING, stage="downloading")
        video_path = await download_video(job_id, job.input_url)
        save_checkpoint(job_id, "downloaded", {"video_path": str(video_path)})

        # Stage 2: Extract
        update_job(job_id, stage="extracting")
        audio_path = extract_audio(video_path)
        save_checkpoint(job_id, "extracted", {"audio_path": str(audio_path)})

        # Complete
        update_job(job_id, status=JobStatus.COMPLETED, stage="completed",
                   output_audio_path=str(audio_path))

    except Exception as e:
        update_job(job_id, status=JobStatus.FAILED, error_message=str(e))
        raise
```

---

## 12. Environment Configuration

```bash
# .env (not committed)
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Models
WHISPER_MODEL=openai/whisper-small
NLLB_MODEL=facebook/nllb-200-distilled-600M
TTS_MODEL=facebook/mms-tts-hau
MODEL_CACHE_DIR=./models_cache

# Processing
MAX_VIDEO_DURATION_SECONDS=7200
MAX_AUDIO_SIZE_MB=500
MAX_TEXT_LENGTH=10000
MAX_TTS_TEXT_LENGTH=5000
DEFAULT_AUDIO_QUALITY=good

# Storage
DOWNLOAD_DIR=./downloads
MAX_STORAGE_GB=40
CLEANUP_AFTER_HOURS=24

# Fallback TTS (optional)
GOOGLE_APPLICATION_CREDENTIALS=
USE_GOOGLE_TTS_FALLBACK=false

# Lightning AI specific
CHECKPOINT_ON_SHUTDOWN=true
```

---

## 13. Local Development vs Lightning AI

| Aspect | Local | Lightning AI |
|--------|-------|--------------|
| **Device** | CPU (slow) or local GPU | T4 GPU (fast) |
| **Install ffmpeg** | `brew install ffmpeg` / `apt-get` | `apt-get install ffmpeg` |
| **Install yt-dlp** | `uv add yt-dlp` | `uv add yt-dlp` |
| **Models** | Download on first run | Download once, persist in `models_cache/` |
| **Storage** | Your disk | 50GB persistent |
| **Public URL** | `localhost:8000` | Auto-generated Lightning URL |
| **Restart** | Manual | Every 4 hours (checkpointing handles) |
| **GPU hours** | Unlimited (if you have GPU) | ~22-80h/month |

### Lightning AI Setup Commands

```bash
# Run once in Studio terminal
sudo apt-get update && sudo apt-get install -y ffmpeg
uv add yt-dlp fastapi uvicorn python-multipart transformers torch

# Download models (cached in persistent storage)
python -c "from transformers import pipeline; pipeline('automatic-speech-recognition', model='openai/whisper-small')"
python -c "from transformers import pipeline; pipeline('translation', model='facebook/nllb-200-distilled-600M')"
python -c "from transformers import VitsModel; VitsModel.from_pretrained('facebook/mms-tts-hau')"

# Run app
uv run uvicorn hausa_translator_api.main:app --host 0.0.0.0 --port 8000
```

---

## 14. Performance Targets

### Video → Audio
| Video Length | Download | Extract | Total |
|--------------|----------|---------|-------|
| 10 min | ~30s | ~5s | ~35s |
| 30 min | ~2 min | ~15s | ~2.5 min |
| 1 hour | ~5 min | ~30s | ~5.5 min |
| 2 hours | ~10 min | ~1 min | ~11 min |

### Translate (Audio Input)
| Audio Length | Transcribe (T4) | Translate (T4) | Total |
|--------------|-----------------|----------------|-------|
| 10 min | ~5 min | ~2 min | ~7 min |
| 30 min | ~15 min | ~5 min | ~20 min |
| 1 hour | ~30 min | ~10 min | ~40 min |

### TTS
| Text Length | Generate (T4) | Concat | Total |
|-------------|---------------|--------|-------|
| 500 chars | ~30s | ~2s | ~32s |
| 2000 chars | ~2 min | ~5s | ~2.5 min |
| 5000 chars | ~5 min | ~10s | ~5.5 min |

---

## 15. Security (5-User Scope)

- **No authentication** — private deployment, URL-only access
- **CORS:** Allow Next.js frontend origin only
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["https://your-frontend.vercel.app", "http://localhost:3000"],
      allow_methods=["GET", "POST", "DELETE"],
      allow_headers=["*"],
  )
  ```
- **URL validation:** Block `file://`, `ftp://`, internal IPs (`10.`, `192.168.`, `127.`)
- **File cleanup:** Delete temp files 24h after completion
- **Rate limiting:** Max 2 concurrent jobs per IP (optional, using slowapi)
- **Input limits:** Enforce max duration, file size, text length at API level

---

*Document version: 2.0*
*Target: MVP for Lightning AI free tier + local dev*
*Architecture: 3 independent stages with chaining support*
