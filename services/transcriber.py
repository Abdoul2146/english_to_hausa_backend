import httpx
import time
from pathlib import Path
from models.config import settings

HF_WHISPER_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-large-v3"
MAX_RETRIES = 3

def transcribe_audio(audio_path: Path) -> dict:
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    headers = {
        "Authorization": f"Bearer {settings.HF_TOKEN}",
        "Content-Type": "audio/wav",
        "x-wait-for-model": "1",
    }

    for attempt in range(MAX_RETRIES):
        try:
            with httpx.Client(timeout=300.0) as client:
                response = client.post(HF_WHISPER_URL, headers=headers, data=audio_bytes)

            if response.status_code in (502, 503):
                time.sleep(5)
                continue

            response.raise_for_status()
            result = response.json()
            break
        except httpx.HTTPError:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 ** attempt)

    full_text = result.get("text", "").strip()

    return {
        "segments": [{"start": 0.0, "end": 0.0, "text": full_text}],
        "full_text": full_text,
        "language": "en"
    }
