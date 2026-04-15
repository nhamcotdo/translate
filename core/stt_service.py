"""
Speech-to-Text service using OpenAI Whisper
"""
import os
import sys
import threading
import contextlib
import logging
from typing import List, Dict, Callable, Optional, Tuple

logger = logging.getLogger(__name__)


class STTService:
    """Speech-to-Text service using Whisper"""

    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self.model = None
        self.lock = threading.Lock()

    def load_model(self, progress_callback: Optional[Callable] = None):
        """Load the Whisper model (thread-safe, lazy)."""
        if self.model is None:
            with self.lock:
                if self.model is None:
                    if progress_callback:
                        progress_callback(0.05, f"Loading Whisper model '{self.model_size}' (first time may download)...")
                    import whisper
                    logger.info(f"Loading Whisper model: {self.model_size}")
                    self.model = whisper.load_model(self.model_size, device=self.device)
                    logger.info("Model loaded successfully")

    def transcribe(
        self,
        file_path: str,
        language: str = "auto",
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Tuple[List[Dict], str]:
        """
        Transcribe audio/video file to subtitle segments.

        Returns:
            (list of segments, detected_language)
        """
        if progress_callback:
            progress_callback(0.01, "Initializing transcription...")

        self.load_model(progress_callback)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Starting transcription: {file_path}")

        if progress_callback:
            progress_callback(0.1, "Transcribing (this may take a while)...")

        import whisper

        with self.lock:
            with open(os.devnull, "w") as devnull:
                with contextlib.redirect_stderr(devnull):
                    result = self.model.transcribe(
                        file_path,
                        language=None if language == "auto" else language,
                        verbose=None,
                    )

        detected_language = result.get("language", "unknown")
        logger.info(f"Detected language: {detected_language}")

        if progress_callback:
            progress_callback(0.7, "Processing segments...")

        subtitles = []
        segments = result.get("segments", [])

        for i, segment in enumerate(segments):
            subtitles.append(
                {
                    "index": i,
                    "start_time": segment["start"],
                    "end_time": segment["end"],
                    "text": segment["text"].strip(),
                }
            )

            if progress_callback and i % 10 == 0 and segments:
                progress = 0.7 + (i / len(segments)) * 0.25
                progress_callback(progress, f"Processing segment {i + 1}/{len(segments)}...")

        if progress_callback:
            progress_callback(1.0, f"Done! {len(subtitles)} segments extracted.")

        logger.info(f"Transcription completed: {len(subtitles)} segments")
        return subtitles, detected_language

    # ---- Export helpers ----

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_vtt_timestamp(seconds: float) -> str:
        """HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @staticmethod
    def segments_to_srt(subtitles: List[Dict]) -> str:
        """Convert segments to SRT string."""
        lines = []
        for i, sub in enumerate(subtitles, 1):
            start = STTService._format_srt_timestamp(sub["start_time"])
            end = STTService._format_srt_timestamp(sub["end_time"])
            lines.append(str(i))
            lines.append(f"{start} --> {end}")
            lines.append(sub["text"])
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def segments_to_vtt(subtitles: List[Dict]) -> str:
        """Convert segments to VTT string."""
        lines = ["WEBVTT\n"]
        for sub in subtitles:
            start = STTService._format_vtt_timestamp(sub["start_time"])
            end = STTService._format_vtt_timestamp(sub["end_time"])
            lines.append(f"{start} --> {end}")
            lines.append(sub["text"])
            lines.append("")
        return "\n".join(lines)
