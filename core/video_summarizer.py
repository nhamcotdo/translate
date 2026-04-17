import json
import logging
import os
import subprocess
import threading
from typing import List, Dict, Callable

from core.vtt_parser import SubtitleProcessor
from core.translator import TranslatorService, BaseProvider

logger = logging.getLogger(__name__)

class VideoSummarizer:
    def __init__(self, translator_service: TranslatorService):
        """
        Initializes with a translator_service that will be used to make LLM calls.
        """
        self.translator_service = translator_service

    def _parse_timestamp_to_seconds(self, ts: str) -> float:
        """Parses HH:MM:SS.mmm or HH:MM:SS,mmm to seconds."""
        ts = ts.replace(",", ".")
        parts = ts.split(":")
        if len(parts) == 3:
            h, m, s = parts
            return float(h) * 3600 + float(m) * 60 + float(s)
        return 0.0
        
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Converts seconds back to HH:MM:SS,mmm"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int(round((seconds % 1) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def analyze_subtitles(self, subtitle_text: str, model_name: str, num_highlights: int, log_callback: Callable = None) -> List[Dict]:
        """
        Uses AI to find the most interesting segments from the subtitles.
        Ensures that segments are sufficiently long and include enough context.
        """
        if log_callback:
            log_callback("Asking AI to select highlights...")
            
        prompt = f"""
You are an expert video editor. I will provide you with the subtitles of a video.
Your task is to select the {num_highlights} most engaging, interesting, or informative segments to create a highlight reel.

CRITICAL RULES FOR SELECTING SEGMENTS:
1. COMPLETE CONTEXT & ACTION RESOLUTION: A segment must NOT be cut off abruptly exactly when someone stops speaking. You MUST predict if an action naturally follows the dialogue (e.g., a reaction, walking away, an impact) and intentionally extend the `end` timestamp further to capture that concluding action. Always include preceding and succeeding sentences to ensure the scene makes complete sense.
2. DURATION: Each segment MUST be at least 15 seconds long, but ideally 30-60 seconds to provide a rich context.
3. FORMAT: Return ONLY a valid JSON array of objects. Do not use markdown blocks unless it is strictly valid JSON.
4. JSON STRUCTURE:
[
  {{
    "start": "HH:MM:SS.mmm", // The start timestamp (expanded backwards slightly for context)
    "end": "HH:MM:SS.mmm", // The end timestamp (predict and extend further to capture post-dialogue actions)
    "reason": "Brief explanation of why this was chosen",
    "transcript": "The expected transcript of this segment"
  }}
]
5. Make sure segments do NOT overlap and are presented in chronological order.

Subtitles:
{subtitle_text}
"""
        try:
            response = self.translator_service.translate_with_retry(prompt, model_name, log_callback)
            
            # Extract JSON from response (handling potential markdown blocks)
            # Find the first '[' and last ']'
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                highlights = json.loads(json_str)
                
                # Apply a safe padding empirically (e.g. 2 seconds before, 2 seconds after)
                padded_highlights = []
                for hl in highlights:
                    s_sec = max(0.0, self._parse_timestamp_to_seconds(hl['start']) - 2.0)
                    e_sec = self._parse_timestamp_to_seconds(hl['end']) + 2.0
                    
                    hl['padded_start_sec'] = s_sec
                    hl['padded_end_sec'] = e_sec
                    hl['start'] = self._seconds_to_timestamp(s_sec)
                    hl['end'] = self._seconds_to_timestamp(e_sec)
                    padded_highlights.append(hl)
                    
                return padded_highlights
            else:
                raise ValueError("Could not parse JSON from AI response")
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] AI analysis failed: {e}")
            raise

    def generate_narration(self, highlights: List[Dict], model_name: str, target_lang: str, log_callback: Callable = None) -> List[Dict]:
        """
        Generates narration text for each selected segment.
        """
        if not highlights:
            return highlights

        if log_callback:
            log_callback(f"Generating narration in {target_lang}...")
            
        # Simplify payload to reduce token count and processing time
        simplified_segments = []
        for i, hl in enumerate(highlights):
            simplified_segments.append({
                "index": i + 1,
                "transcript": hl.get('transcript', '')
            })
            
        highlights_json = json.dumps(simplified_segments, ensure_ascii=False)
        
        prompt = f"""
You are a charismatic video storyteller. Write a short, engaging narration for each of the following video segments.

RULES:
1. Write strictly in {target_lang}.
2. Keep it concise (1-2 short sentences maximum per segment).
3. Make it engaging, describing what happens or why it is interesting based on the transcript.
4. Return ONLY a valid JSON array of strings in the EXACT same order as the segments.
5. Do NOT include markdown formatting like ```json.

Example output format:
[
  "First engaging narration here.",
  "Second engaging narration here."
]

Segments to narrate:
{highlights_json}
"""
        try:
            if log_callback:
                log_callback("Waiting for AI to write narrations...")
                
            response = self.translator_service.translate_with_retry(prompt, model_name, log_callback)
            
            start_idx = response.find('[')
            end_idx = response.rfind(']')
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx+1]
                narrations = json.loads(json_str)
                
                # Merge narration into highlights
                for i, hl in enumerate(highlights):
                    if i < len(narrations) and isinstance(narrations[i], str):
                        hl['narration'] = narrations[i].strip()
                    else:
                        hl['narration'] = ""
                return highlights
            else:
                raise ValueError("Could not parse JSON array from AI response")
        except Exception as e:
            if log_callback:
                log_callback(f"[ERROR] Narration generation failed: {e}")
            raise

    def cut_and_merge_video(self, input_video: str, highlights: List[Dict], output_video: str, log_callback: Callable = None, progress_callback: Callable = None) -> bool:
        """
        Uses FFmpeg to cut each highlighted segment and concatenate them.
        """
        if not highlights:
            if log_callback:
                log_callback("No highlights to process.")
            return False

        if log_callback:
            log_callback(f"Starting video processing with FFmpeg ({len(highlights)} segments)...")
            
        work_dir = os.path.dirname(output_video)
        temp_files = []
        list_file_path = os.path.join(work_dir, "concat_list.txt")
        
        try:
            with open(list_file_path, "w", encoding="utf-8") as list_file:
                for i, hl in enumerate(highlights):
                    segment_file = os.path.join(work_dir, f"segment_{i}.mp4")
                    temp_files.append(segment_file)
                    
                    start_s = hl.get('padded_start_sec', self._parse_timestamp_to_seconds(hl['start']))
                    end_s = hl.get('padded_end_sec', self._parse_timestamp_to_seconds(hl['end']))
                    duration = end_s - start_s
                    
                    if log_callback:
                        log_callback(f"Extracting segment {i+1} ({start_s:.1f}s to {end_s:.1f}s) ...")
                        
                    # Re-encoding audio/video ensures clean cuts and avoids audio sync issues that happen with `-c copy`.
                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", str(start_s),
                        "-i", input_video,
                        "-t", str(duration),
                        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        "-c:a", "aac", "-b:a", "128k",
                        "-avoid_negative_ts", "make_zero",
                        segment_file
                    ]
                    
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    
                    # Get actual encoded duration to prevent SRT drift
                    try:
                        probe_cmd = [
                            "ffprobe", "-v", "error", 
                            "-show_entries", "format=duration", 
                            "-of", "default=noprint_wrappers=1:nokey=1", 
                            segment_file
                        ]
                        actual_dur_str = subprocess.check_output(probe_cmd, text=True).strip()
                        hl['actual_duration'] = float(actual_dur_str)
                    except Exception as e:
                        if log_callback:
                            log_callback(f"[WARNING] Could not probe exact duration: {e}")
                        hl['actual_duration'] = duration
                    
                    # Add to concat list
                    # FFmpeg requires forward slashes or escaped backslashes for file paths
                    safe_path = segment_file.replace("\\", "/")
                    list_file.write(f"file '{safe_path}'\n")
                    
                    if progress_callback:
                        progress_callback(i+1, len(highlights) + 1) # +1 for the concat step

            if log_callback:
                log_callback("Concatenating segments...")

            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                output_video
            ]
            subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            if progress_callback:
                progress_callback(len(highlights) + 1, len(highlights) + 1)
                
            if log_callback:
                log_callback("Video processing complete!")
            return True
            
        except subprocess.CalledProcessError as e:
            if log_callback:
                log_callback(f"[ERROR] FFmpeg failed: {e}")
            return False
        finally:
            # Cleanup temp files
            for f in temp_files:
                if os.path.exists(f):
                    os.remove(f)
            if os.path.exists(list_file_path):
                os.remove(list_file_path)

    def generate_srt(self, highlights: List[Dict], output_srt: str):
        """
        Builds the SRT file for the concatenated highlghts reel.
        Re-calculates the relative timestamps.
        """
        lines = []
        current_time = 0.0
        
        for i, hl in enumerate(highlights):
            start_s = hl.get('padded_start_sec', self._parse_timestamp_to_seconds(hl['start']))
            end_s = hl.get('padded_end_sec', self._parse_timestamp_to_seconds(hl['end']))
            duration = hl.get('actual_duration', end_s - start_s)
            
            new_start = current_time
            new_end = current_time + duration
            
            narration = hl.get('narration', '').strip()
            if narration:
                lines.append(str(i + 1))
                lines.append(f"{self._seconds_to_timestamp(new_start)} --> {self._seconds_to_timestamp(new_end)}")
                lines.append(narration)
                lines.append("")
                
            current_time += duration

        with open(output_srt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
