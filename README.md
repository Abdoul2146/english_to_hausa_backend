# Hausa Translator Backend API (v2.0)

A production-grade, highly scalable, and fully decoupled FastAPI backend featuring three modular processing pipelines. This backend is optimized to run on GPU-enabled hosting environments (such as a Lightning AI GPU Studio) while persisting transaction and progress metadata to a managed Supabase PostgreSQL instance.

---

## 🚀 Key Features

*   **Clean Separation of Concerns:** Rigid domain layering (`models`, `schema`, `crud`, `services`, and `api/endpoints`) ensures maximum maintainability and code clarity.
*   **Fully Decoupled Architecture:** Users can chain outputs or run individual pipeline stages completely standalone.
*   **No In-Memory Dependencies:** Built on PostgreSQL using SQLAlchemy and Alembic, allowing infinite application scaling and seamless recovery on restarts.
*   **Decoupled Audio Extraction:** Stage 1 is fully decoupled. You can download and extract audio from public URLs (YouTube, Vimeo, etc.) OR upload raw video files directly to the server.
*   **Interactive Transcription & Translation Flow:** Stage 2 is split into distinct, modular operations. Transcribe English audio to English text, review or copy it, and then submit it for segment-by-segment Hausa translation preserving all timestamps.
*   **Robust Security:** Endpoint operations are protected via custom `X-API-KEY` authorization headers to prevent GPU compute resource exhaustion.
*   **Lazy Singleton Model Cache:** Deep learning models (Whisper, NLLB-200, MMS-TTS) load lazily on demand and stay cached efficiently in GPU memory.

---

## 📂 Codebase Directory Layout

```
english_to_hausa/
├── api/
│   ├── endpoints/
│   │   ├── video_to_audio.py    # URL extraction & Direct file upload pipelines
│   │   ├── translate.py         # Whisper transcription & NLLB translation pipelines
│   │   └── tts.py               # MMS-TTS synthesis pipeline
│   └── deps.py                  # API Key security validation & DB dependency injection
├── crud/
│   └── job.py                   # Complete CRUD operations mapping job status, progress, and results
├── models/
│   ├── config.py                # Pydantic Settings parsing environment parameters
│   ├── database.py              # PostgreSQL database engine and session configurations
│   └── job.py                   # SQLAlchemy declarative model representing the 'jobs' table
├── schema/
│   ├── api_schemas.py           # Pydantic schemas validating API requests/responses
│   └── job_schemas.py           # Pydantic schemas serializing SQLAlchemy database records
├── services/
│   ├── audio_extractor.py       # Decoupled WAV audio extraction service using FFmpeg
│   ├── downloader.py            # External video downloading service using yt-dlp
│   ├── file_manager.py          # Secure path management and job workspace cleanup
│   ├── model_loader.py          # Thread-safe Lazy Singleton loading cached deep learning models
│   ├── transcriber.py           # Whisper ASR speech-to-text inference pipeline
│   ├── translator.py            # NLLB-200 English-to-Hausa machine translation pipeline
│   └── tts_generator.py         # MMS-TTS text-to-speech audio segment synthesis and concatenation
├── migrations/                  # Alembic database migrations tracking schemas
├── main.py                      # Core FastAPI application initialization, lifespans, and health metrics
├── route.py                     # Centralized aggregation and mounting of endpoint routers
├── pyproject.toml               # Python project configuration and package definitions
└── .env                         # Environment settings containing database connection strings & secrets
```

---

## ⚡ Deployment to Lightning AI (GPU Studio)

Since your local Windows network may throttle or timeout outgoing connections on port 5432, follow this direct deployment workflow to run your backend on **Lightning AI GPU Studios (T4 GPU)**.

### Step 1: Clone your Repository on Lightning AI
Open the Studio terminal and fetch your codebase:
```bash
git clone <YOUR_GITHUB_REPO_URL>
cd english_to_hausa
```

### Step 2: One-Time System Setup & FFMPEG Installation
```bash
# Update local packages and install ffmpeg system binaries
sudo apt-get update && sudo apt-get install -y ffmpeg

# Sync the python environment using uv
uv sync
```

### Step 3: Configure your Environments (`.env`)
Create a `.env` file on Lightning AI:
```bash
touch .env
```
Paste your production Supabase database connections and secure parameters:
```ini
HOST=0.0.0.0
PORT=8000
DEBUG=false
API_KEY=your-super-secure-custom-api-key

# Supabase Connection URI (Add sslmode=require at the end)
DATABASE_URL=postgresql://postgres:[YOUR-CLEAN-PASSWORD]@db.luupxtsvhbvvufloqruf.supabase.co:5432/postgres?sslmode=require

STORAGE_DIR=./downloads
MODEL_CACHE_DIR=./models_cache
```

### Step 4: Execute Alembic Database Migrations
Run your migration scripts from the Studio terminal to instantly construct the `jobs` database table on Supabase:
```bash
uv run alembic upgrade head
```
*(You can verify the table exists instantly by opening the **Table Editor** on your Supabase web dashboard!)*

### Step 5: Cache Deep Learning Models
Pre-download the Hugging Face weights directly onto Lightning AI's fast persistent disk storage. This takes under a minute:
```bash
uv run python -c "
import os
from transformers import pipeline, VitsModel, VitsTokenizer
os.environ['HF_HOME'] = './models_cache'
print('Downloading Whisper-small (~244MB)...')
pipeline('automatic-speech-recognition', model='openai/whisper-small')
print('Downloading NLLB-200-Distilled-600M (~600MB)...')
pipeline('translation', model='facebook/nllb-200-distilled-600M')
print('Downloading MMS-TTS Hausa (~500MB)...')
VitsModel.from_pretrained('facebook/mms-tts-hau')
VitsTokenizer.from_pretrained('facebook/mms-tts-hau')
print('All models cached successfully on Lightning AI!')
"
```

### Step 6: Start the Production Server
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```
Lightning AI will automatically generate a public URL for your port 8000. Copy it and plug it directly into your Next.js frontend!

---

## 🛠️ Local API Testing & Development

If you'd like to run a local dev environment:
1. Update `.env` to point to a local PostgreSQL cluster (or local Docker container).
2. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```
3. Run the development server:
   ```bash
   uv run uvicorn main:app --reload
   ```
4. Access interactive API documentation at: `http://localhost:8000/docs`.

---

## 🛡️ Secure Authorization Check
All background mutations and status endpoints (`POST` & `GET`) require the following header:
```http
X-API-KEY: <your-configured-api-key>
```
*(Public file download routes for processed audios do not require keys so your frontend can stream files cleanly).*
