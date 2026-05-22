from pathlib import Path
from services.model_loader import ModelLoader

def transcribe_audio(audio_path: Path) -> dict:
    whisper_pipeline = ModelLoader.get_whisper()
    
    # Run Whisper pipeline with standard configs
    result = whisper_pipeline(
        str(audio_path),
        chunk_length_s=30,
        batch_size=16,
        return_timestamps=True
    )
    
    segments = []
    # Structure segments with timestamps cleanly
    chunks = result.get("chunks", [])
    if chunks:
        for chunk in chunks:
            timestamp = chunk.get("timestamp", (0.0, 0.0))
            # Handle possible null timestamps
            start = timestamp[0] if timestamp[0] is not None else 0.0
            end = timestamp[1] if timestamp[1] is not None else 0.0
            segments.append({
                "start": start,
                "end": end,
                "text": chunk.get("text", "").strip()
            })
    else:
        # Fallback if chunks are missing
        segments.append({
            "start": 0.0,
            "end": 0.0,
            "text": result.get("text", "").strip()
        })
        
    return {
        "segments": segments,
        "full_text": result.get("text", "").strip(),
        "language": "en"
    }
