import subprocess
from pathlib import Path
from gtts import gTTS

def synthesize_to_wav(text: str, output_path: Path, lang: str = "ha") -> Path:
    tts = gTTS(text=text, lang=lang, slow=False)
    mp3_path = output_path.with_suffix(".mp3")
    tts.save(str(mp3_path))

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mp3_path),
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
         str(output_path)],
        check=True, capture_output=True
    )

    mp3_path.unlink(missing_ok=True)
    return output_path
