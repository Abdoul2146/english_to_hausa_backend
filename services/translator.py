import httpx
from models.config import settings

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

    with httpx.Client(timeout=60.0) as client:
        url = f"{GEMINI_URL}?key={settings.GEMINI_API_KEY}"
        response = client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

    return result["candidates"][0]["content"]["parts"][0]["text"].strip()

def translate_segments(segments: list, source_lang: str = "en", target_lang: str = "ha") -> list:
    combined = " ".join(seg["text"] for seg in segments if seg["text"].strip())
    translated = translate_text(combined, source_lang, target_lang)
    return [{"start": 0.0, "end": 0.0, "text": translated}]
