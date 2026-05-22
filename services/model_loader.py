import os
import torch
from transformers import pipeline, VitsModel, VitsTokenizer
from models.config import settings

class ModelLoader:
    _cache = {}

    @classmethod
    def get_whisper(cls):
        if "whisper" not in cls._cache:
            device = 0 if torch.cuda.is_available() else -1
            # Ensure model cache directory is set
            os.environ["HF_HOME"] = settings.MODEL_CACHE_DIR
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
            os.environ["HF_HOME"] = settings.MODEL_CACHE_DIR
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
            os.environ["HF_HOME"] = settings.MODEL_CACHE_DIR
            cls._cache["tts"] = {
                "model": VitsModel.from_pretrained("facebook/mms-tts-hau").to(device),
                "tokenizer": VitsTokenizer.from_pretrained("facebook/mms-tts-hau")
            }
        return cls._cache["tts"]

    @classmethod
    def unload_all(cls):
        cls._cache.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
