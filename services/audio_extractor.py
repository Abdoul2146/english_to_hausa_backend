import subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe
from services.file_manager import get_job_file_path

def extract_audio_wav(job_id: str, video_path: Path) -> Path:
    output_wav = get_job_file_path(job_id, "audio.wav")
    ffmpeg_path = get_ffmpeg_exe()
    
    command = [
        ffmpeg_path, "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_wav)
    ]
    
    try:
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        if not output_wav.exists() or output_wav.stat().st_size == 0:
            raise Exception("Generated audio file is empty or missing")
        return output_wav
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
        raise Exception(f"FFmpeg extraction failed: {error_msg}")
