import json
import logging
from typing import Callable, Optional

from core.translator import TranslatorService

logger = logging.getLogger(__name__)


SEO_PLATFORM_CONFIGS = {
    "youtube": {
        "title_limit": 100,
        "description_limit": 5000,
        "tags_limit": 500,     # total chars across all tags
        "max_tags": 15,
    },
    "facebook": {
        "title_limit": 255,
        "description_limit": 63206,
        "tags_limit": None,
        "max_tags": 30,
    },
}


class SEODescriptionGenerator:
    """
    Uses an LLM to generate SEO-optimized video descriptions for
    YouTube and Facebook from subtitle / context text.
    """

    def __init__(self, translator_service: TranslatorService):
        self.translator_service = translator_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        subtitle_text: str,
        platform: str,            # "youtube" | "facebook"
        target_lang: str,
        video_title: str = "",
        extra_context: str = "",
        model_name: str = "gpt-4o-mini",
        log_callback: Optional[Callable] = None,
    ) -> dict:
        """
        Generate a complete SEO package for the given platform.

        Returns a dict with keys:
            - title          (str)
            - description    (str)
            - tags           (list[str])
            - hashtags       (list[str])
            - call_to_action (str)
            - raw_response   (str)   – the raw LLM output for debugging
        """
        platform = platform.lower()
        if platform not in SEO_PLATFORM_CONFIGS:
            raise ValueError(f"Unsupported platform: {platform}. Choose 'youtube' or 'facebook'.")

        cfg = SEO_PLATFORM_CONFIGS[platform]

        if log_callback:
            log_callback(f"Generating SEO description for {platform.upper()} in {target_lang}...")

        prompt = self._build_prompt(
            subtitle_text=subtitle_text,
            platform=platform,
            target_lang=target_lang,
            video_title=video_title,
            extra_context=extra_context,
            cfg=cfg,
        )

        raw = self.translator_service.translate_with_retry(prompt, model_name, log_callback)

        if log_callback:
            log_callback("Parsing SEO response...")

        result = self._parse_response(raw)
        result["raw_response"] = raw
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        subtitle_text: str,
        platform: str,
        target_lang: str,
        video_title: str,
        extra_context: str,
        cfg: dict,
    ) -> str:
        title_note = f"Keep the title under {cfg['title_limit']} characters." if cfg["title_limit"] else ""
        desc_note  = f"Keep description under {cfg['description_limit']} characters." if cfg["description_limit"] else ""
        tag_note   = (
            f"Provide up to {cfg['max_tags']} tags. Each tag must be a single keyword or short phrase without #."
            if cfg["max_tags"] else ""
        )

        platform_specific = ""
        if platform == "youtube":
            platform_specific = """
YouTube-specific guidelines:
- Title: Include the main keyword near the front. Use power words (How, Why, Best, etc.) if appropriate.
- Description: Write a 150–200 word opening paragraph (this is shown before "Show more"). Include keywords naturally.
  Add chapters/timestamps if relevant (format: 0:00 Intro), links, and a call-to-action.
- Tags: Use a mix of broad and niche tags relevant to the content.
- Include relevant hashtags (3–5) at the very END of the description, each starting with #.
"""
        elif platform == "facebook":
            platform_specific = """
Facebook-specific guidelines:
- Title: This is the post headline. Make it emotionally compelling and concise.
- Description: Write an engaging post body. Start with a hook sentence. Use short paragraphs (1–3 lines).
  Include emojis naturally. End with a clear call-to-action (e.g., "Comment below 👇", "Share with a friend ❤️").
- Tags/Keywords: These will be added as hashtags in the post. Use popular, relevant hashtags (# prefix will be added automatically).
- Include 5–10 trending hashtags relevant to the content.
"""

        video_title_section = f"\nVideo Title (if known): {video_title}" if video_title.strip() else ""
        context_section = f"\nExtra Context: {extra_context}" if extra_context.strip() else ""
        subtitle_section = f"\nSubtitle / Transcript:\n{subtitle_text[:8000]}" if subtitle_text.strip() else "\n(No subtitle provided — infer from title and context)"

        prompt = f"""You are an expert social media manager and SEO strategist specialized in video content.

Your task: Generate a complete SEO-optimized package for a {platform.upper()} video.

Language: ALL output text (title, description, tags, hashtags, call_to_action) MUST be written in **{target_lang}**.
{title_note}
{desc_note}
{tag_note}

{platform_specific}

---
INPUT DATA:
{video_title_section}
{context_section}
{subtitle_section}
---

Return your answer as a single, valid JSON object with EXACTLY these keys:
{{
  "title": "...",
  "description": "...",
  "tags": ["tag1", "tag2", ...],
  "hashtags": ["#hashtag1", "#hashtag2", ...],
  "call_to_action": "..."
}}

Rules:
1. Output ONLY the JSON object — no markdown fences, no extra text.
2. All string values must be valid JSON (escape quotes, newlines use \\n).
3. Tags should NOT include the # symbol.
4. Hashtags MUST include the # symbol.
5. Ensure the description is rich in keywords but reads naturally.
"""
        return prompt

    def _parse_response(self, raw: str) -> dict:
        """Extract and parse the JSON object from the LLM response."""
        # Find the first '{' and last '}' to extract JSON robustly
        start = raw.find("{")
        end   = raw.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("Could not find JSON object in AI response.")

        json_str = raw[start:end + 1]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse AI JSON response: {e}\n\nRaw:\n{json_str[:500]}")

        # Normalise keys — provide defaults for missing ones
        return {
            "title":          data.get("title", ""),
            "description":    data.get("description", ""),
            "tags":           data.get("tags", []),
            "hashtags":       data.get("hashtags", []),
            "call_to_action": data.get("call_to_action", ""),
        }
