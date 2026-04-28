"""
auto_fix.py
-----------
Detect subtitle lines that still contain Chinese characters ([\u4E00-\u9FFF])
after an initial translation pass, then re-translate them with surrounding
context lines for better accuracy.
"""

import re
import threading
from typing import List, Dict, Callable, Optional

from core.translator import TranslatorService

CHINESE_RE = re.compile(r"[\u4E00-\u9FFF]")


def find_chinese_lines(subs: List[Dict]) -> List[int]:
    """Return indices (0-based) of subtitle entries that contain Chinese chars."""
    return [i for i, s in enumerate(subs) if CHINESE_RE.search(s.get("text", ""))]


def build_fix_prompt(target_lang: str, lines_with_ctx: List[Dict], bad_indices_local: List[int]) -> str:
    """
    Build a targeted re-translation prompt.

    lines_with_ctx  – a window of subtitle dicts (context + bad lines)
    bad_indices_local – positions WITHIN lines_with_ctx that need to be fixed
    """
    total = len(lines_with_ctx)
    marked_lines = []
    for i, s in enumerate(lines_with_ctx):
        marker = "[FIX]" if i in bad_indices_local else "[CTX]"
        marked_lines.append(f"{i + 1}|{marker}|{s['text']}")

    payload = "\n".join(marked_lines)
    bad_ids = ", ".join(str(i + 1) for i in bad_indices_local)

    prompt = f"""You are an expert subtitle translator performing a targeted fix pass.

Some subtitle lines were NOT properly translated and still contain Chinese characters.
You must re-translate ONLY the lines marked [FIX] into {target_lang}.
Lines marked [CTX] are surrounding context – do NOT change them, they are provided only for narrative context.

CRITICAL RULES:
1. Target Language: {target_lang}. Translate [FIX] lines FULLY into {target_lang}.
2. Output ONLY the [FIX] lines. IDs to fix: {bad_ids}.
3. Format: ID|Translated_Text  (one line per entry, no extra text)
4. Do NOT output [CTX] lines.
5. Do NOT add explanations or blank lines.

<subtitles>
{payload}
</subtitles>
"""
    return prompt.strip()


def run_auto_fix(
    subs: List[Dict],
    target_lang: str,
    model_name: str,
    translator_service: TranslatorService,
    context_window: int = 2,
    log_callback: Optional[Callable] = None,
    progress_callback: Optional[Callable] = None,
    cancel_event: Optional[threading.Event] = None,
) -> List[Dict]:
    """
    Scan *subs* for Chinese chars, group nearby bad lines into batches,
    then re-translate each batch with context.  Returns updated subs list.

    context_window  – how many lines before/after a bad line to include as CTX
    """
    bad_indices = find_chinese_lines(subs)

    if not bad_indices:
        if log_callback:
            log_callback("[Auto-Fix] No Chinese characters detected. Nothing to fix.")
        return subs

    if log_callback:
        log_callback(f"[Auto-Fix] Found {len(bad_indices)} line(s) with Chinese chars. Starting fix...")

    # ── Group consecutive (or nearby) bad indices into clusters ─────────────
    clusters: List[List[int]] = []
    current: List[int] = [bad_indices[0]]

    for idx in bad_indices[1:]:
        # Merge into current cluster if within 2*context_window gap
        if idx - current[-1] <= context_window * 2 + 1:
            current.append(idx)
        else:
            clusters.append(current)
            current = [idx]
    clusters.append(current)

    total_clusters = len(clusters)
    fixed_subs = [s.copy() for s in subs]

    for cluster_num, cluster in enumerate(clusters, 1):
        if cancel_event and cancel_event.is_set():
            if log_callback:
                log_callback("[Auto-Fix] Cancelled by user.")
            break

        # ── Build window ────────────────────────────────────────────────────
        win_start = max(0, cluster[0] - context_window)
        win_end = min(len(subs) - 1, cluster[-1] + context_window)

        window_subs = subs[win_start : win_end + 1]
        # Positions of bad lines WITHIN the window
        bad_local = [b - win_start for b in cluster]

        if log_callback:
            global_ids = [b + 1 for b in cluster]  # 1-based for display
            log_callback(f"[Auto-Fix] Cluster {cluster_num}/{total_clusters}: fixing line(s) {global_ids} (window {win_start+1}-{win_end+1})")

        prompt = build_fix_prompt(target_lang, window_subs, bad_local)

        try:
            content = translator_service.translate_with_retry(prompt, model_name, log_callback=log_callback)
        except Exception as e:
            if log_callback:
                log_callback(f"[Auto-Fix] ERROR on cluster {cluster_num}: {e}")
            continue

        # ── Parse response and apply fixes ──────────────────────────────────
        fixes: Dict[int, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 1)
            if len(parts) == 2 and parts[0].isdigit():
                local_idx = int(parts[0]) - 1  # 0-based within window
                fixes[local_idx] = parts[1].strip()

        applied = 0
        for local_idx, new_text in fixes.items():
            global_idx = win_start + local_idx
            if 0 <= global_idx < len(fixed_subs):
                if log_callback:
                    old = fixed_subs[global_idx]["text"]
                    log_callback(f"[Auto-Fix] Line {global_idx+1}: «{old}» → «{new_text}»")
                fixed_subs[global_idx]["text"] = new_text
                applied += 1

        if log_callback and applied == 0:
            log_callback(f"[Auto-Fix] Warning: cluster {cluster_num} – no fixes were applied (check LLM response format).")

        if progress_callback:
            progress_callback(cluster_num, total_clusters)

    remaining = find_chinese_lines(fixed_subs)
    if log_callback:
        if remaining:
            log_callback(f"[Auto-Fix] Done. {len(remaining)} line(s) still have Chinese chars (may need manual review).")
        else:
            log_callback("[Auto-Fix] Done. All Chinese characters successfully fixed ✅")

    return fixed_subs
