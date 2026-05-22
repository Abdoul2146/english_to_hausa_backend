from services.model_loader import ModelLoader

def translate_text(text: str, source_lang: str = "eng_Latn", target_lang: str = "hau_Latn") -> str:
    resources = ModelLoader.get_translator()
    model = resources["model"]
    tokenizer = resources["tokenizer"]

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    translated_tokens = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_lang),
        max_length=256
    )
    return tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)[0]

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
