import httpx
import time
from models.config import settings

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = ["gemini-3.5-flash", "gemini-2.5-flash"]

TRANSLATION_PROMPT = (
    "You are a professional translator. Translate the following English text "
    "to Hausa (the Chadic language spoken in Nigeria and Niger). "
    "Return ONLY the Hausa translation, with no explanations, notes, or English text.\n\n"
    "English: {text}\nHausa:"
)

MAX_RETRIES = 3

def translate_text(text: str, source_lang: str = "en", target_lang: str = "ha") -> str:
    prompt = TRANSLATION_PROMPT.format(text=text)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "maxOutputTokens": 8192,
            "topP": 1.0
        }
    }

    last_error = None

    for model in GEMINI_MODELS:
        url = f"{GEMINI_BASE}/{model}:generateContent?key={settings.GEMINI_API_KEY}"

        for attempt in range(MAX_RETRIES):
            try:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(url, json=payload)

                if response.status_code in (502, 503):
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    last_error = httpx.HTTPStatusError(
                        f"Server error {response.status_code} for {model}",
                        request=response.request,
                        response=response
                    )
                    break

                response.raise_for_status()
                result = response.json()
                return result["candidates"][0]["content"]["parts"][0]["text"].strip()

            except httpx.HTTPStatusError as e:
                last_error = e
                break
            except (httpx.ConnectError, httpx.RemoteProtocolError):
                if attempt == MAX_RETRIES - 1:
                    last_error = httpx.ConnectError(f"Connection failed for {model}")
                    break
                time.sleep(2 ** attempt)

    raise last_error or RuntimeError("All Gemini models failed")

def translate_segments(segments: list, source_lang: str = "en", target_lang: str = "ha") -> list:
    combined = " ".join(seg["text"] for seg in segments if seg["text"].strip())
    translated = translate_text(combined, source_lang, target_lang)
    return [{"start": 0.0, "end": 0.0, "text": translated}]
