import re
from typing import List, Dict

class VTTProcessor:
    @staticmethod
    def fix_encoding(text: str) -> str:
        try:
            return text.encode('latin1').decode('utf-8')
        except:
            return text

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
                text = VTTProcessor.fix_encoding(text)

                results.append({
                    "start": start,
                    "end": end,
                    "text": text
                })
            i += 1

        return results

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
