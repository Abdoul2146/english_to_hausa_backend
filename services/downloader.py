import yt_dlp
import time
from pathlib import Path
from services.file_manager import get_job_file_path

async def download_video(job_id: str, url: str, max_duration: int = 7200) -> Path:
    # Use standard format configuration for yt-dlp to extract best audio
    output_path_template = str(get_job_file_path(job_id, "input_video.%(ext)s"))
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path_template,
        'noplaylist': True,
        'max_filesize': 500 * 1024 * 1024, # 500MB
    }

    # Validate duration before downloading by using yt-dlp to extract metadata
    with yt_dlp.YoutubeDL({'noplaylist': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        duration = info.get('duration', 0)
        if duration > max_duration:
            raise ValueError(f"Video duration ({duration}s) exceeds the maximum allowed ({max_duration}s)")
        
    # Download with retry logic
    retries = 3
    for attempt in range(retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return Path(filename)
        except Exception as e:
            if attempt == retries - 1:
                raise e
            time.sleep(2 * (attempt + 1))
    
    raise Exception("Download failed after maximum retries")
