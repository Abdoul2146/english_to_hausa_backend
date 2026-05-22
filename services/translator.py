from services.model_loader import ModelLoader

def translate_text(text: str, source_lang: str = "eng_Latn", target_lang: str = "hau_Latn") -> str:
    translator = ModelLoader.get_translator()
    
    # Run distilled translation pipeline
    result = translator(
        text,
        src_lang=source_lang,
        tgt_lang=target_lang,
        max_length=256
    )
    
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("translation_text", "").strip()
    return ""

def translate_segments(segments: list, source_lang: str = "eng_Latn", target_lang: str = "hau_Latn") -> list:
    translated_segments = []
    for seg in segments:
        text = seg.get("text", "")
        if text.strip():
            translated_text = translate_text(text, source_lang, target_lang)
        else:
            translated_text = ""
        translated_segments.append({
            "start": seg.get("start", 0.0),
            "end": seg.get("end", 0.0),
            "text": translated_text
        })
    return translated_segments
