import re
from typing import List, Dict

class SubtitleProcessor:
    @staticmethod
    def fix_encoding(text: str) -> str:
        try:
            return text.encode('latin1').decode('utf-8')
        except:
            return text

    @staticmethod
    def detect_format(text: str) -> str:
        """Detect subtitle format: 'vtt' or 'srt'."""
        stripped = text.strip()
        if stripped.startswith("WEBVTT"):
            return "vtt"
        # Check for SRT pattern: number line followed by timestamp with comma
        srt_pattern = re.compile(r"^\d+\s*\n\d{2}:\d{2}:\d{2},\d{3}\s*-->", re.MULTILINE)
        if srt_pattern.search(stripped):
            return "srt"
        # Fallback: check for VTT-style timestamp (dot separator)
        vtt_pattern = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3}\s*-->")
        if vtt_pattern.search(stripped):
            return "vtt"
        # Default to srt if has comma timestamps
        srt_ts = re.compile(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->")
        if srt_ts.search(stripped):
            return "srt"
        return "vtt"

    @staticmethod
    def parse_vtt(vtt_text: str) -> List[Dict]:
        lines = vtt_text.splitlines()
        results = []

        time_pattern = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})")

        i = 0
        while i < len(lines):
            match = time_pattern.match(lines[i])
            if match:
                start, end = match.groups()
                i += 1

                text_lines = []
                while i < len(lines) and lines[i].strip() != "":
                    text_lines.append(lines[i])
                    i += 1

                text = " ".join(text_lines).strip()
                text = SubtitleProcessor.fix_encoding(text)

                results.append({
                    "start": start,
                    "end": end,
                    "text": text
                })
            i += 1

        return results

    @staticmethod
    def parse_srt(srt_text: str) -> List[Dict]:
        """Parse SRT format subtitles."""
        lines = srt_text.splitlines()
        results = []

        time_pattern = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})")

        i = 0
        while i < len(lines):
            # Skip sequence number lines (pure digits)
            if lines[i].strip().isdigit():
                i += 1
                continue

            match = time_pattern.match(lines[i].strip())
            if match:
                start_raw, end_raw = match.groups()
                # Convert SRT timestamps (comma) to internal format (dot)
                start = start_raw.replace(",", ".")
                end = end_raw.replace(",", ".")
                i += 1

                text_lines = []
                while i < len(lines) and lines[i].strip() != "":
                    text_lines.append(lines[i])
                    i += 1

                text = " ".join(text_lines).strip()
                text = SubtitleProcessor.fix_encoding(text)

                results.append({
                    "start": start,
                    "end": end,
                    "text": text
                })
            i += 1

        return results

    @staticmethod
    def parse_auto(text: str) -> List[Dict]:
        """Auto-detect format and parse."""
        fmt = SubtitleProcessor.detect_format(text)
        if fmt == "srt":
            return SubtitleProcessor.parse_srt(text)
        return SubtitleProcessor.parse_vtt(text)

    @staticmethod
    def remove_duplicates(subs: List[Dict]) -> List[Dict]:
        seen = set()
        cleaned = []

        for s in subs:
            key = (s["start"], s["end"], s["text"])
            if key not in seen:
                seen.add(key)
                cleaned.append(s)

        return cleaned

    @staticmethod
    def chunk_subs(subs: List[Dict], chunk_size=15):
        for i in range(0, len(subs), chunk_size):
            yield subs[i:i + chunk_size]

    @staticmethod
    def to_vtt(subs: List[Dict]) -> str:
        output = ["WEBVTT\n"]

        for s in subs:
            output.append(f"{s['start']} --> {s['end']}")
            output.append(s["text"])
            output.append("")

        return "\n".join(output)

    @staticmethod
    def to_srt(subs: List[Dict]) -> str:
        """Format subtitles as SRT."""
        output = []

        for idx, s in enumerate(subs, 1):
            output.append(str(idx))
            # Convert internal timestamps (dot) to SRT format (comma)
            start = s["start"].replace(".", ",")
            end = s["end"].replace(".", ",")
            output.append(f"{start} --> {end}")
            output.append(s["text"])
            output.append("")

        return "\n".join(output)

    @staticmethod
    def to_format(subs: List[Dict], fmt: str) -> str:
        """Format subtitles to the specified format ('vtt' or 'srt')."""
        if fmt == "srt":
            return SubtitleProcessor.to_srt(subs)
        return SubtitleProcessor.to_vtt(subs)


# Backward compatibility alias
VTTProcessor = SubtitleProcessor
