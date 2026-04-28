"""
format_tab.py
-------------
A standalone subtitle format editor tab.
Supports SRT/VTT: re-numbering, spacing fix, format conversion,
HTML tag stripping, and line-merge/split utilities.
"""

import re
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.vtt_parser import SubtitleProcessor
from ui.translations import get_tr


# ── helpers ──────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    """Remove common subtitle HTML tags (<i>, <b>, <u>, <font ...>, etc.)."""
    return re.sub(r"<[^>]+>", "", text)


def _fix_srt_spacing(text: str) -> str:
    """
    Rebuild SRT structure from messy input:
    Index → Timestamp → Text → blank line.
    Handles extra blank lines, missing blanks, and stray whitespace.
    """
    srt_ts_re = re.compile(
        r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$"
    )
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if re.fullmatch(r"\d+", line):
            # Ensure blank separator before each block (except very first)
            if result and result[-1].strip() != "":
                result.append("")
            result.append(line)   # index
            i += 1
            if i < len(lines):
                ts = lines[i].strip()
                if srt_ts_re.match(ts):
                    result.append(ts)  # timestamp
                    i += 1
                    while i < len(lines):
                        tl = lines[i].strip()
                        if not tl or re.fullmatch(r"\d+", tl) or srt_ts_re.match(tl):
                            break
                        result.append(tl)
                        i += 1
                else:
                    result.append(ts)
                    i += 1
        else:
            result.append(line)
            i += 1
    return "\n".join(result)


def _fix_vtt_spacing(text: str) -> str:
    """Rebuild VTT structure (WEBVTT header + cue blocks separated by blanks)."""
    vtt_ts_re = re.compile(
        r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}"
    )
    lines = text.split("\n")
    # Strip existing blank lines for re-processing
    non_blank = [l for l in lines if l.strip()]
    result = []
    if non_blank and non_blank[0].strip().startswith("WEBVTT"):
        result.append(non_blank[0].strip())
        start = 1
    else:
        result.append("WEBVTT")
        start = 0
    i = start
    while i < len(non_blank):
        line = non_blank[i].strip()
        if vtt_ts_re.match(line):
            result.append("")   # blank before cue
            result.append(line)  # timestamp
            i += 1
            while i < len(non_blank):
                tl = non_blank[i].strip()
                if vtt_ts_re.match(tl):
                    break
                result.append(tl)
                i += 1
        else:
            i += 1  # skip stray non-timestamp lines (cue IDs, etc.)
    return "\n".join(result)


def _renumber_srt(text: str) -> str:
    """Re-index SRT blocks sequentially starting from 1."""
    srt_ts_re = re.compile(
        r"^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$"
    )
    lines = text.split("\n")
    result = []
    counter = 1
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.fullmatch(r"\d+", line):
            # Check the next non-empty line is a timestamp
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and srt_ts_re.match(lines[j].strip()):
                if result and result[-1].strip() != "":
                    result.append("")
                result.append(str(counter))
                counter += 1
                i += 1
                continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def _merge_short_lines(subs, max_chars=42):
    """
    Merge subtitle text that is split across multiple lines inside a cue
    but try to keep under max_chars per line. Returns subs unchanged structure,
    only modifying 'text' field.
    """
    merged = []
    for s in subs:
        words = s["text"].replace("\n", " ").split()
        lines = []
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            if len(test) <= max_chars:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        merged.append({**s, "text": "\n".join(lines)})
    return merged


def _split_long_lines(subs, max_chars=42):
    """
    Split cue text lines that exceed max_chars at word boundaries.
    """
    result = []
    for s in subs:
        raw_lines = s["text"].split("\n")
        new_lines = []
        for rl in raw_lines:
            if len(rl) <= max_chars:
                new_lines.append(rl)
            else:
                words = rl.split()
                current = ""
                for w in words:
                    test = (current + " " + w).strip()
                    if len(test) <= max_chars:
                        current = test
                    else:
                        if current:
                            new_lines.append(current)
                        current = w
                if current:
                    new_lines.append(current)
        result.append({**s, "text": "\n".join(new_lines)})
    return result


def _count_blocks(text: str) -> int:
    """Count subtitle blocks (by index lines for SRT, or timestamp lines for VTT)."""
    fmt = SubtitleProcessor.detect_format(text)
    if fmt == "srt":
        return len(re.findall(r"^\d+$", text, re.MULTILINE))
    else:
        return len(re.findall(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s*-->", text, re.MULTILINE))


# ── Tab class ─────────────────────────────────────────────────────────────────

class FormatTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.tr = get_tr(config_manager)
        self._loaded_filename = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        btn_cfg = dict(height=32, cursor="hand2", corner_radius=6)

        ctk.CTkButton(toolbar, text="📂 " + self.tr("Load"), width=90,
                      command=self._load_file, **btn_cfg,
                      fg_color="#1E293B", border_color="#3B82F6", border_width=1
                      ).pack(side="left", padx=(6, 4), pady=6)

        ctk.CTkButton(toolbar, text="💾 " + self.tr("Save"), width=90,
                      command=self._save_file, **btn_cfg,
                      fg_color="#10B981", hover_color="#059669"
                      ).pack(side="left", padx=4, pady=6)

        ttk_sep1 = ctk.CTkFrame(toolbar, width=1, fg_color="#334155")
        ttk_sep1.pack(side="left", fill="y", padx=8, pady=6)

        # Format operations
        ctk.CTkButton(toolbar, text="🔢 Renumber", width=110,
                      command=self._renumber, **btn_cfg,
                      fg_color="#334155", hover_color="#475569"
                      ).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(toolbar, text="⬜ Fix Spacing", width=115,
                      command=self._fix_spacing, **btn_cfg,
                      fg_color="#334155", hover_color="#475569"
                      ).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(toolbar, text="🏷 Strip HTML", width=110,
                      command=self._strip_html_tags, **btn_cfg,
                      fg_color="#334155", hover_color="#475569"
                      ).pack(side="left", padx=4, pady=6)

        ttk_sep2 = ctk.CTkFrame(toolbar, width=1, fg_color="#334155")
        ttk_sep2.pack(side="left", fill="y", padx=8, pady=6)

        # Conversion
        ctk.CTkButton(toolbar, text="🔁 SRT → VTT", width=115,
                      command=lambda: self._convert("vtt"), **btn_cfg,
                      fg_color="#7C3AED", hover_color="#6D28D9"
                      ).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(toolbar, text="🔁 VTT → SRT", width=115,
                      command=lambda: self._convert("srt"), **btn_cfg,
                      fg_color="#7C3AED", hover_color="#6D28D9"
                      ).pack(side="left", padx=4, pady=6)

        ttk_sep3 = ctk.CTkFrame(toolbar, width=1, fg_color="#334155")
        ttk_sep3.pack(side="left", fill="y", padx=8, pady=6)

        # Line tools
        ctk.CTkButton(toolbar, text="↔ Merge Lines", width=115,
                      command=self._merge_lines, **btn_cfg,
                      fg_color="#0E7490", hover_color="#0891B2"
                      ).pack(side="left", padx=4, pady=6)

        ctk.CTkButton(toolbar, text="↕ Split Lines", width=110,
                      command=self._split_lines, **btn_cfg,
                      fg_color="#0E7490", hover_color="#0891B2"
                      ).pack(side="left", padx=4, pady=6)

        # Max chars entry for split/merge
        ctk.CTkLabel(toolbar, text="Max chars:", text_color="#94A3B8",
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(8, 2))
        self.max_chars_var = ctk.StringVar(value="42")
        ctk.CTkEntry(toolbar, textvariable=self.max_chars_var, width=44,
                     height=28).pack(side="left", padx=(0, 6))

        ttk_sep4 = ctk.CTkFrame(toolbar, width=1, fg_color="#334155")
        ttk_sep4.pack(side="left", fill="y", padx=8, pady=6)

        ctk.CTkButton(toolbar, text="↩ Undo", width=80,
                      command=self._undo, **btn_cfg,
                      fg_color="#334155", hover_color="#475569"
                      ).pack(side="left", padx=4, pady=6)

        # Status label on the right
        self.status_lbl = ctk.CTkLabel(toolbar, text="", text_color="#94A3B8",
                                       font=ctk.CTkFont(size=12))
        self.status_lbl.pack(side="right", padx=12)

        # ── Split pane ───────────────────────────────────────────────────────
        pane = ctk.CTkFrame(self, fg_color="transparent")
        pane.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 4))
        pane.grid_columnconfigure(0, weight=1)
        pane.grid_columnconfigure(1, weight=1)
        pane.grid_rowconfigure(1, weight=1)

        # Input side
        in_hdr = ctk.CTkFrame(pane, fg_color="transparent")
        in_hdr.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
        ctk.CTkLabel(in_hdr, text=self.tr("Input (SRT / VTT)"),
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(in_hdr, text="✕ Clear", width=60, height=24,
                      fg_color="#334155", hover_color="#475569", cursor="hand2",
                      command=self._clear_input).pack(side="right")
        ctk.CTkButton(in_hdr, text="📋 Paste", width=70, height=24,
                      fg_color="#1E293B", hover_color="#334155", cursor="hand2",
                      command=self._paste_input).pack(side="right", padx=(0, 4))

        self.input_text = ctk.CTkTextbox(pane, border_spacing=10, wrap="none")
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
        self.input_text.bind("<<Modified>>", self._on_input_change)

        # Input stats bar
        self.in_stats = ctk.CTkLabel(pane, text="Lines: 0  Chars: 0  Blocks: 0",
                                     text_color="#64748B", font=ctk.CTkFont(size=11),
                                     anchor="w")
        self.in_stats.grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=(2, 0))

        # Output side
        out_hdr = ctk.CTkFrame(pane, fg_color="transparent")
        out_hdr.grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=(0, 4))
        ctk.CTkLabel(out_hdr, text=self.tr("Output (Formatted)"),
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(out_hdr, text="✕ Clear", width=60, height=24,
                      fg_color="#334155", hover_color="#475569", cursor="hand2",
                      command=self._clear_output).pack(side="right")
        ctk.CTkButton(out_hdr, text="📋 Copy", width=70, height=24,
                      fg_color="#1E293B", hover_color="#334155", cursor="hand2",
                      command=self._copy_output).pack(side="right", padx=(0, 4))
        ctk.CTkButton(out_hdr, text="→ Input", width=70, height=24,
                      fg_color="#0E7490", hover_color="#0891B2", cursor="hand2",
                      command=self._output_to_input).pack(side="right", padx=(0, 4))

        self.output_text = ctk.CTkTextbox(pane, border_spacing=10, wrap="none")
        self.output_text.grid(row=1, column=1, sticky="nsew", padx=(4, 0))

        # Output stats bar
        self.out_stats = ctk.CTkLabel(pane, text="Lines: 0  Chars: 0  Blocks: 0",
                                      text_color="#64748B", font=ctk.CTkFont(size=11),
                                      anchor="w")
        self.out_stats.grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=(2, 0))

        # Bottom stats strip
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.detect_lbl = ctk.CTkLabel(bot, text="Format: –",
                                       text_color="#64748B",
                                       font=ctk.CTkFont(size=12))
        self.detect_lbl.pack(side="left")

        # Undo stack
        self._undo_stack = []

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _get_input(self) -> str:
        return self.input_text.get("0.0", "end").rstrip("\n")

    def _set_output(self, text: str):
        self.output_text.configure(state="normal")
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", text)
        self._update_out_stats(text)

    def _push_undo(self):
        self._undo_stack.append(self._get_input())
        if len(self._undo_stack) > 30:
            self._undo_stack.pop(0)

    def _update_in_stats(self, text: str):
        lines = text.count("\n") + (1 if text else 0)
        chars = len(text)
        blocks = _count_blocks(text) if text.strip() else 0
        self.in_stats.configure(text=f"Lines: {lines}  Chars: {chars}  Blocks: {blocks}")

    def _update_out_stats(self, text: str):
        lines = text.count("\n") + (1 if text else 0)
        chars = len(text)
        blocks = _count_blocks(text) if text.strip() else 0
        self.out_stats.configure(text=f"Lines: {lines}  Chars: {chars}  Blocks: {blocks}")

    def _on_input_change(self, event=None):
        text = self._get_input()
        self._update_in_stats(text)
        if text.strip():
            fmt = SubtitleProcessor.detect_format(text)
            self.detect_lbl.configure(text=f"Format: {fmt.upper()}")
        else:
            self.detect_lbl.configure(text="Format: –")
        self.input_text.edit_modified(False)

    def _status(self, msg: str):
        self.status_lbl.configure(text=msg)

    def _max_chars(self) -> int:
        try:
            return max(10, int(self.max_chars_var.get()))
        except ValueError:
            return 42

    # ── Toolbar actions ──────────────────────────────────────────────────────

    def _load_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("Subtitle Files", "*.vtt *.srt"), ("All Files", "*.*")]
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(filename, "r", encoding="latin-1") as f:
                content = f.read()
        self._loaded_filename = filename
        self.input_text.delete("0.0", "end")
        self.input_text.insert("0.0", content)
        self._update_in_stats(content)
        fmt = SubtitleProcessor.detect_format(content)
        self.detect_lbl.configure(text=f"Format: {fmt.upper()}")
        self._status(f"Loaded: {os.path.basename(filename)}")

    def _save_file(self):
        content = self.output_text.get("0.0", "end").strip()
        if not content:
            messagebox.showwarning("Empty", "Output is empty – nothing to save.")
            return
        fmt = SubtitleProcessor.detect_format(content)
        default_ext = f".{fmt}"
        filetypes = [("SRT files", "*.srt"), ("VTT files", "*.vtt"), ("All Files", "*.*")]
        initial = ""
        if self._loaded_filename:
            base = os.path.splitext(os.path.basename(self._loaded_filename))[0]
            initial = base + "_formatted" + default_ext
        filename = filedialog.asksaveasfilename(
            defaultextension=default_ext,
            filetypes=filetypes,
            initialfile=initial,
        )
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            self._status(f"Saved: {os.path.basename(filename)}")

    def _clear_input(self):
        self.input_text.delete("0.0", "end")
        self.in_stats.configure(text="Lines: 0  Chars: 0  Blocks: 0")
        self.detect_lbl.configure(text="Format: –")

    def _clear_output(self):
        self.output_text.delete("0.0", "end")
        self.out_stats.configure(text="Lines: 0  Chars: 0  Blocks: 0")

    def _paste_input(self):
        try:
            text = self.clipboard_get()
            self.input_text.delete("0.0", "end")
            self.input_text.insert("0.0", text)
            self._update_in_stats(text)
        except Exception:
            pass

    def _copy_output(self):
        content = self.output_text.get("0.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(content)
        self._status("Copied to clipboard ✓")

    def _output_to_input(self):
        """Move output → input for chaining operations."""
        content = self.output_text.get("0.0", "end").strip()
        if not content:
            return
        self._push_undo()
        self.input_text.delete("0.0", "end")
        self.input_text.insert("0.0", content)
        self._update_in_stats(content)
        self._clear_output()
        self._status("Output moved to input ✓")

    def _undo(self):
        if not self._undo_stack:
            self._status("Nothing to undo.")
            return
        prev = self._undo_stack.pop()
        self.input_text.delete("0.0", "end")
        self.input_text.insert("0.0", prev)
        self._update_in_stats(prev)
        self._status("Undo applied ✓")

    # ── Format operations ────────────────────────────────────────────────────

    def _renumber(self):
        text = self._get_input().strip()
        if not text:
            return
        fmt = SubtitleProcessor.detect_format(text)
        if fmt != "srt":
            messagebox.showwarning("SRT only", "Renumber only works on SRT files.")
            return
        result = _renumber_srt(text)
        self._set_output(result)
        self._status("Blocks renumbered ✓")

    def _fix_spacing(self):
        text = self._get_input().strip()
        if not text:
            return
        fmt = SubtitleProcessor.detect_format(text)
        if fmt == "srt":
            result = _fix_srt_spacing(text)
        else:
            result = _fix_vtt_spacing(text)
        self._set_output(result)
        self._status(f"Spacing fixed ({fmt.upper()}) ✓")

    def _strip_html_tags(self):
        text = self._get_input().strip()
        if not text:
            return
        result = _strip_html(text)
        self._set_output(result)
        self._status("HTML tags stripped ✓")

    def _convert(self, target_fmt: str):
        """Convert the input to the target format (srt or vtt)."""
        text = self._get_input().strip()
        if not text:
            return
        src_fmt = SubtitleProcessor.detect_format(text)
        if src_fmt == target_fmt:
            messagebox.showinfo("Same format",
                                f"Input is already {target_fmt.upper()}.")
            return
        subs = SubtitleProcessor.parse_auto(text)
        if not subs:
            messagebox.showerror("Parse error",
                                 "Could not parse subtitle blocks.")
            return
        result = SubtitleProcessor.to_format(subs, target_fmt)
        self._set_output(result)
        self._status(f"Converted {src_fmt.upper()} → {target_fmt.upper()} ✓")

    def _merge_lines(self):
        text = self._get_input().strip()
        if not text:
            return
        max_c = self._max_chars()
        fmt = SubtitleProcessor.detect_format(text)
        subs = SubtitleProcessor.parse_auto(text)
        if not subs:
            messagebox.showerror("Parse error", "Could not parse subtitle blocks.")
            return
        subs = _merge_short_lines(subs, max_chars=max_c)
        result = SubtitleProcessor.to_format(subs, fmt)
        self._set_output(result)
        self._status(f"Lines merged (max {max_c} chars) ✓")

    def _split_lines(self):
        text = self._get_input().strip()
        if not text:
            return
        max_c = self._max_chars()
        fmt = SubtitleProcessor.detect_format(text)
        subs = SubtitleProcessor.parse_auto(text)
        if not subs:
            messagebox.showerror("Parse error", "Could not parse subtitle blocks.")
            return
        subs = _split_long_lines(subs, max_chars=max_c)
        result = SubtitleProcessor.to_format(subs, fmt)
        self._set_output(result)
        self._status(f"Lines split (max {max_c} chars) ✓")
