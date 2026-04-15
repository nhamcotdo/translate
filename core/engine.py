import threading
from typing import List, Dict, Callable

from core.vtt_parser import SubtitleProcessor
from core.translator import TranslatorService

class TranslationEngine:
    """Orchestrates translating an entire subtitle string (VTT or SRT)."""
    
    def __init__(self, translator_service: TranslatorService):
        self.translator_service = translator_service

    def build_prompt(self, chunk: List[Dict], target_lang: str, pre_context: str) -> str:
        lines_to_translate = []
        for idx, s in enumerate(chunk):
            lines_to_translate.append(f"{idx + 1}|{s['text']}")
        
        text_payload = "\n".join(lines_to_translate)
        
        context_block = ""
        if pre_context and pre_context.strip():
            context_block = f"Context Notes / Background details for better translation:\n{pre_context.strip()}\n"

        prompt = f"""
You are an expert movie subtitle translator.

Rules:
- Keep the meaning and tone natural.
- Maintain context between consecutive lines.
- Do NOT merge or split lines.
- Strictly keep the output format: ID|Translated_Text

{context_block}
Translate to {target_lang}:

{text_payload}
"""
        return prompt.strip()

    def translate_chunk(self, chunk: List[Dict], target_lang: str, model_name: str, pre_context: str, log_callback: Callable = None) -> List[Dict]:
        prompt = self.build_prompt(chunk, target_lang, pre_context)
        
        content = self.translator_service.translate_with_retry(prompt, model_name, log_callback=log_callback)
        
        # Parse return
        parsed_lines = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            
            parts = line.split("|", 1)
            if len(parts) == 2 and parts[0].isdigit():
                idx = int(parts[0]) - 1
                parsed_lines[idx] = parts[1].strip()
                
        # Reconstruction
        translated_chunk = []
        for idx, s in enumerate(chunk):
            new_text = parsed_lines.get(idx)
            s_copy = s.copy()
            if new_text:
                s_copy["text"] = new_text
            translated_chunk.append(s_copy)

        return translated_chunk

    def run(self, subtitle_text: str, target_lang: str, model_name: str, pre_context: str, chunk_size: int = 15, progress_callback: Callable = None, log_callback: Callable = None) -> tuple:
        """Translate subtitles. Returns (translated_text, detected_format)."""
        # Auto-detect format
        detected_format = SubtitleProcessor.detect_format(subtitle_text)
        fmt_label = detected_format.upper()

        if log_callback:
            log_callback(f"Detected format: {fmt_label}")
            log_callback(f"Parsing {fmt_label}...")
            
        subs = SubtitleProcessor.parse_auto(subtitle_text)
        subs = SubtitleProcessor.remove_duplicates(subs)
        
        total_chunks = (len(subs) + chunk_size - 1) // chunk_size
        if log_callback:
            log_callback(f"Translating {len(subs)} subtitle lines ({total_chunks} chunks)...")

        translated_subs = []
        
        for i, chunk in enumerate(SubtitleProcessor.chunk_subs(subs, chunk_size=chunk_size)):
            if log_callback:
                log_callback(f"Translating chunk {i+1}/{total_chunks}...")
                
            trans_chunk = self.translate_chunk(chunk, target_lang, model_name, pre_context, log_callback=log_callback)
            translated_subs.extend(trans_chunk)
            
            if progress_callback:
                progress_callback(i + 1, total_chunks)
                
        if log_callback:
            log_callback(f"Formatting back to {fmt_label}...")
            
        translated_subs = SubtitleProcessor.remove_duplicates(translated_subs)
            
        return SubtitleProcessor.to_format(translated_subs, detected_format), detected_format

    # Backward compatibility
    def run_vtt(self, vtt_text: str, target_lang: str, model_name: str, pre_context: str, chunk_size: int = 15, progress_callback: Callable = None, log_callback: Callable = None) -> str:
        result, _ = self.run(vtt_text, target_lang, model_name, pre_context, chunk_size, progress_callback, log_callback)
        return result
