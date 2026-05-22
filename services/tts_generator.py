import torch
import soundfile as sf
import re
from pathlib import Path
from services.model_loader import ModelLoader
from services.file_manager import ensure_job_directory, get_job_file_path

def split_text_into_chunks(text: str, max_chars: int = 400) -> list[str]:
    # Split by sentence boundaries cleanly
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += " " + sentence if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If a single sentence is longer than max_chars, split it crudely or just keep it
            if len(sentence) > max_chars:
                # Force chunking
                sub_sentences = [sentence[i:i+max_chars] for i in range(0, len(sentence), max_chars)]
                chunks.extend(sub_sentences)
                current_chunk = ""
            else:
                current_chunk = sentence
                
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def generate_tts_wav(job_id: str, text: str, speed: float = 1.0) -> Path:
    tts_resources = ModelLoader.get_tts()
    model = tts_resources["model"]
    tokenizer = tts_resources["tokenizer"]
    device = model.device
    
    chunks = split_text_into_chunks(text)
    temp_dir = ensure_job_directory(job_id) / "tts_segments"
    temp_dir.mkdir(exist_ok=True)
    
    segment_files = []
    
    for i, chunk in enumerate(chunks):
        inputs = tokenizer(chunk, return_tensors="pt").to(device)
        with torch.no_grad():
            output = model(**inputs)
        
        # Audio is returned as float tensor
        waveform = output.waveform[0].cpu().numpy()
        
        # Write wav file chunk
        chunk_file = temp_dir / f"{i:04d}.wav"
        # Sampling rate is usually 16000 or 22050 for VITS. facebook/mms-tts is 16000Hz
        sf.write(str(chunk_file), waveform, 16000)
        segment_files.append(chunk_file)
        
    # Concatenate the wav segments using soundfile directly
    output_wav = get_job_file_path(job_id, "output_hausa.wav")
    
    all_data = []
    sr = None
    for file in segment_files:
        data, samplerate = sf.read(str(file))
        if sr is None:
            sr = samplerate
        all_data.append(data)
        
    import numpy as np
    if all_data:
        concatenated_data = np.concatenate(all_data)
        sf.write(str(output_wav), concatenated_data, sr if sr else 16000)
    else:
        # Empty text fallback
        sf.write(str(output_wav), np.zeros(16000), 16000)
        
    return output_wav
