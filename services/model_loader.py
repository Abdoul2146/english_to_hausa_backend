import os
import torch
from transformers import pipeline, AutoModelForSeq2SeqLM, AutoTokenizer
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
            device = "cuda" if torch.cuda.is_available() else "cpu"
            os.environ["HF_HOME"] = settings.MODEL_CACHE_DIR
            cls._cache["translator"] = {
                "model": AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M").to(device),
                "tokenizer": AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
            }
        return cls._cache["translator"]

    @classmethod
    def unload_all(cls):
        cls._cache.clear()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
