# Hausa Translator API — Frontend Consumption Guide

Base URL: `https://8000-01ks55qwbe6q40k48n17st7gcf.cloudspaces.litng.ai`

---

## Authentication

All `POST` and `DELETE` endpoints require the API key header:

```http
X-API-KEY: your-api-key-here
```

`GET` download and status endpoints are public (no key required).

---

## Pipeline Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   STAGE 1       │     │   STAGE 2            │     │   STAGE 3       │
│ Video → Audio   │ ──► │ English → Hausa Text │ ──► │ Hausa Text →    │
│                 │     │                      │     │ Audio           │
│ [Upload video]  │     │ [Transcribe audio]   │     │ [Synthesize     │
│  or [YouTube    │     │  then [Translate     │     │  speech]        │
│   URL]          │     │   text]              │     │                 │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
```

---

## Stage 1: Video to Audio

### Option A: Upload a video file directly

**Endpoint:** `POST /api/video-to-audio/extract-file`

**Request:** Multipart form data

| Field | Type | Description |
|-------|------|-------------|
| `file` | File | Video file (MP4, MOV, AVI, etc.) |

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "File received. Extracting audio from direct upload."
}
```

**cURL Example:**
```bash
curl -X POST https://base-url/api/video-to-audio/extract-file \
  -H "X-API-KEY: your-api-key" \
  -F "file=@/path/to/video.mp4"
```

**JavaScript (Fetch):**
```javascript
const formData = new FormData();
formData.append('file', videoFile);

const res = await fetch(`${BASE_URL}/api/video-to-audio/extract-file`, {
  method: 'POST',
  headers: { 'X-API-KEY': API_KEY },
  body: formData
});
const { job_id } = await res.json();
```

---

### Option B: Extract from a YouTube / video URL

**Endpoint:** `POST /api/video-to-audio`

**Request Body:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "audio_quality": "good",
  "max_duration_seconds": 3600
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Job accepted."
}
```

**JavaScript (Fetch):**
```javascript
const res = await fetch(`${BASE_URL}/api/video-to-audio`, {
  method: 'POST',
  headers: {
    'X-API-KEY': API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://youtube.com/watch?v=...',
    max_duration_seconds: 3600
  })
});
const { job_id } = await res.json();
```

---

### Check Job Status (All Stages)

**Endpoint:** `GET /api/video-to-audio/{job_id}/status`

**Response:**
```json
{
  "id": "550e8400-...",
  "job_type": "video-to-audio",
  "status": "completed",
  "stage": "completed",
  "progress_percent": 100,
  "message": "Job completed successfully",
  "created_at": "2026-05-22T10:00:00Z",
  "updated_at": "2026-05-22T10:02:00Z",
  "media_url": "https://base-url/api/video-to-audio/{job_id}/download"
}
```

**Status values:** `queued` → `processing` → `completed` or `failed`

**Polling strategy:** Poll every 2-3 seconds until `status` is `completed` or `failed`.

---

### Download Extracted Audio

**Endpoint:** `GET /api/video-to-audio/{job_id}/download`

**Response:** `audio/wav` stream

Use the `media_url` from the status response to get the audio. This URL can be passed directly to Stage 2.

---

## Stage 2: Translate

### Step 2A: Transcribe Audio → English Text

**Endpoint:** `POST /api/translate/transcribe`

**Request Body:**
```json
{
  "audio_url": "https://base-url/api/video-to-audio/{job_id}/download"
}
```

Use the `media_url` from Stage 1's completed job.

**Response (202 Accepted):**
```json
{
  "job_id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "queued",
  "message": "Transcription started."
}
```

---

### Check Transcribe Status & Get Result

**Endpoint:** `GET /api/translate/{job_id}/status`

When `status` is `completed`, the `output_payload` contains the English transcript:

```json
{
  "id": "660e8400-...",
  "status": "completed",
  "output_payload": {
    "original_text": "In this documentary we explore the rich cultural heritage...",
    "segments": [
      { "start": 0.0, "end": 5.2, "text": "In this documentary..." },
      { "start": 5.2, "end": 12.8, "text": "we explore the rich cultural heritage..." }
    ],
    "metadata": {
      "word_count_original": 1500,
      "model": "openai/whisper-small"
    }
  }
}
```

**Alternative result endpoint:** `GET /api/translate/{job_id}/result` (returns 400 if not yet completed)

---

### Step 2B: Translate English Text → Hausa Text

**Endpoint:** `POST /api/translate`

Transcribe only gives you **English text**. Translate that text to Hausa as a **separate step**.

**Option 1 — Plain text:**
```json
{
  "text": "In this documentary we explore the rich cultural heritage...",
  "source_language": "eng_Latn",
  "target_language": "hau_Latn"
}
```

**Option 2 — Segments with timestamps (preserves timing):**
```json
{
  "segments": [
    { "start": 0.0, "end": 5.2, "text": "In this documentary..." },
    { "start": 5.2, "end": 12.8, "text": "we explore the rich cultural heritage..." }
  ],
  "source_language": "eng_Latn",
  "target_language": "hau_Latn"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "queued",
  "message": "Translation started."
}
```

**JavaScript Example:**
```javascript
// After getting English text from transcription
const res = await fetch(`${BASE_URL}/api/translate`, {
  method: 'POST',
  headers: {
    'X-API-KEY': API_KEY,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: englishTranscriptText,
    source_language: 'eng_Latn',
    target_language: 'hau_Latn'
  })
});
const { job_id } = await res.json();
```

---

### Check Translate Status & Get Result

**Endpoint:** `GET /api/translate/{job_id}/status`

When `status` is `completed`:

```json
{
  "id": "770e8400-...",
  "status": "completed",
  "output_payload": {
    "hausa_text": "A wannan takardar za mu bincika al'adun gargajiya...",
    "segments": [
      { "start": 0.0, "end": 5.2, "text": "A wannan takardar..." },
      { "start": 5.2, "end": 12.8, "text": "za mu bincika al'adun gargajiya..." }
    ],
    "metadata": {
      "word_count_hausa": 1200,
      "model": "facebook/nllb-200-distilled-600M"
    }
  }
}
```

---

## Stage 3: Text to Speech (TTS)

### Generate Hausa Speech

**Endpoint:** `POST /api/tts`

**Request Body:**
```json
{
  "text": "A wannan takardar za mu bincika al'adun gargajiya...",
  "speed": 1.0,
  "voice": "default"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "880e8400-e29b-41d4-a716-446655440003",
  "status": "queued",
  "message": "TTS generation started."
}
```

---

### Check TTS Status

**Endpoint:** `GET /api/tts/{job_id}/status`

When `status` is `completed`:

```json
{
  "id": "880e8400-...",
  "status": "completed",
  "media_url": "https://base-url/api/tts/{job_id}/download"
}
```

---

### Download Hausa Audio

**Endpoint:** `GET /api/tts/{job_id}/download`

**Response:** `audio/wav` stream

Use the `media_url` from the status response to play the audio in the browser or allow download.

---

## Other Endpoints

### Health Check

**Endpoint:** `GET /health`

```json
{
  "status": "healthy",
  "gpu_available": true,
  "database": "connected"
}
```

### Delete / Cancel a Job

**Endpoint:** `DELETE /api/jobs/{job_id}`

**Headers:** Requires `X-API-KEY`

```json
{
  "message": "Job {job_id} cancelled and all local files cleaned up successfully."
}
```

---

## Full Chaining Example (Frontend Flow)

```
1. User uploads video
   POST /api/video-to-audio/extract-file
   ↓
2. Poll until completed
   GET /api/video-to-audio/{job_id}/status
   ↓ Gets media_url
3. Transcribe audio to English
   POST /api/translate/transcribe { audio_url: media_url }
   ↓
4. Poll until completed
   GET /api/translate/{job_id}/status
   ↓ Gets original_text
5. Translate English to Hausa (separate manual step)
   POST /api/translate { text: original_text }
   ↓
6. Poll until completed
   GET /api/translate/{job_id}/status
   ↓ Gets hausa_text
7. Synthesize Hausa speech
   POST /api/tts { text: hausa_text }
   ↓
8. Poll until completed
   GET /api/tts/{job_id}/status
   ↓ Gets media_url
9. Play or download Hausa audio
   GET /api/tts/{job_id}/download
```

---

## Error Handling

All endpoints return standard HTTP status codes:

| Code | Meaning |
|------|---------|
| 202 | Job accepted and queued |
| 200 | Request successful (status check or download) |
| 400 | Invalid input or job not yet completed |
| 401 | Missing or invalid API key |
| 404 | Job or file not found |
| 500 | Internal server error |

Failed jobs contain an `error_message` field in the status response:

```json
{
  "status": "failed",
  "error_message": "FFmpeg extraction failed: ..."
}
```

---

## Notes for the Frontend

- **Polling:** Poll status endpoints every 2-3 seconds. Do not poll faster.
- **Audio format:** All audio output is WAV (16kHz, mono). The browser `<audio>` element plays WAV natively.
- **Text limits:** Maximum 10,000 characters for translation, 5,000 for TTS.
- **No auth on downloads:** Audio download URLs are public so the browser can stream them directly.
- **Segments:** The `segments` array contains `start` and `end` times in seconds. Useful for captioning or aligning audio with text.
- **User controls translation:** Transcription produces English. Translation to Hausa is a **separate user-initiated step**. The user can review/copy the English text before deciding to translate.
