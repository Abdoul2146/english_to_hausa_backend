import httpx
import time
import socket
from models.config import settings

_original_getaddrinfo = socket.getaddrinfo
def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

TRANSLATION_PROMPT = (
    "You are a professional translator. Translate the following English text "
    "to Hausa (the Chadic language spoken in Nigeria and Niger). "
    "Return ONLY the Hausa translation, with no explanations, notes, or English text.\n\n"
    "English: {text}\nHausa:"
)

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

    for attempt in range(3):
        try:
            with httpx.Client(timeout=60.0) as client:
                url = f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}"
                response = client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            break
        except (httpx.ConnectError, httpx.RemoteProtocolError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

    return result["candidates"][0]["content"]["parts"][0]["text"].strip()

def translate_segments(segments: list, source_lang: str = "en", target_lang: str = "ha") -> list:
    combined = " ".join(seg["text"] for seg in segments if seg["text"].strip())
    translated = translate_text(combined, source_lang, target_lang)
    return [{"start": 0.0, "end": 0.0, "text": translated}]
