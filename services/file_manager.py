import shutil
from pathlib import Path
from models.config import settings

def ensure_job_directory(job_id: str) -> Path:
    path = Path(settings.STORAGE_DIR) / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path

def clean_job_directory(job_id: str):
    path = Path(settings.STORAGE_DIR) / job_id
    if path.exists():
        shutil.rmtree(path)

def get_job_file_path(job_id: str, filename: str) -> Path:
    return ensure_job_directory(job_id) / filename
