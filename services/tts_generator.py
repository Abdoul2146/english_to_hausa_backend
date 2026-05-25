from pathlib import Path
from services.gtts_tts import synthesize_to_wav
from services.file_manager import get_job_file_path

def generate_tts_wav(job_id: str, text: str, speed: float = 1.0) -> Path:
    output_wav = get_job_file_path(job_id, "output_hausa.wav")
    return synthesize_to_wav(text, output_wav, lang="ha")
