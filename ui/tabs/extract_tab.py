import os
import threading
import queue
import customtkinter as ctk
from tkinter import filedialog, messagebox
from ui.translations import get_tr


class ExtractTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.tr = get_tr(self.config_manager)
        self.stt_service = None
        self.extracted_text = ""
        self.extracted_format = "srt"

        self.ui_queue = queue.Queue()
        self._start_ui_queue_loop()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Settings Card ---
        self.settings_card = ctk.CTkFrame(self)
        self.settings_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        self.settings_card.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(self.settings_card, text=self.tr("Whisper Model:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")
        self.model_var = ctk.StringVar(value="base")
        self.model_dropdown = ctk.CTkOptionMenu(
            self.settings_card,
            variable=self.model_var,
            values=["tiny", "base", "small", "medium", "large"],
            cursor="hand2"
        )
        self.model_dropdown.grid(row=0, column=1, padx=5, pady=15, sticky="w")

        ctk.CTkLabel(self.settings_card, text=self.tr("Audio Lang:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=(15, 5), pady=15, sticky="w")
        self.lang_var = ctk.StringVar(value="auto")
        self.lang_entry = ctk.CTkEntry(self.settings_card, textvariable=self.lang_var, width=80)
        self.lang_entry.grid(row=0, column=3, padx=5, pady=15, sticky="w")

        ctk.CTkLabel(self.settings_card, text=self.tr("Output Format:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=(15, 5), pady=15, sticky="w")
        self.format_var = ctk.StringVar(value="srt")
        self.format_dropdown = ctk.CTkOptionMenu(
            self.settings_card,
            variable=self.format_var,
            values=["srt", "vtt"],
            cursor="hand2",
            width=80
        )
        self.format_dropdown.grid(row=0, column=5, padx=5, pady=15, sticky="w")

        # --- File Card ---
        self.file_card = ctk.CTkFrame(self)
        self.file_card.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.file_card.grid_columnconfigure(1, weight=1)

        self.load_btn = ctk.CTkButton(self.file_card, text=self.tr("🎬 Select Video/Audio"), command=self.select_file, cursor="hand2", height=32, fg_color="#1E293B", border_color="#3B82F6", border_width=1)
        self.load_btn.grid(row=0, column=0, padx=15, pady=15, sticky="w")
        
        self.file_label = ctk.CTkLabel(self.file_card, text=self.tr("No file selected..."), text_color="gray")
        self.file_label.grid(row=0, column=1, padx=10, pady=15, sticky="w")

        # --- Output Area ---
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_rowconfigure(1, weight=1)

        output_header = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        output_header.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(output_header, text=self.tr("Extracted Subtitles"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.clear_output_btn = ctk.CTkButton(output_header, text=self.tr("✕ Clear"), width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.output_text.delete("0.0", "end"))
        self.clear_output_btn.pack(side="right")

        self.output_text = ctk.CTkTextbox(self.text_frame, border_spacing=10, wrap="word")
        self.output_text.grid(row=1, column=0, sticky="nsew")

        # --- Action Bar ---
        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.action_bar.grid_columnconfigure(1, weight=1)

        self.extract_btn = ctk.CTkButton(self.action_bar, text=self.tr("▶ Start Extraction"), font=ctk.CTkFont(weight="bold"), command=self.start_extraction, cursor="hand2", height=40)
        self.extract_btn.grid(row=0, column=0, sticky="w")
        
        self.cancel_btn = ctk.CTkButton(self.action_bar, text=self.tr("⏹ Cancel"), font=ctk.CTkFont(weight="bold"), command=self.cancel_extraction, cursor="hand2", height=40, fg_color="#DC2626", hover_color="#B91C1C", state="disabled")
        self.cancel_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.progress_frame = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        self.progress_frame.grid(row=0, column=2, sticky="ew", padx=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(self.progress_frame, text=self.tr("Ready"), text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        self.progress = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)

        self.save_btn = ctk.CTkButton(self.action_bar, text=self.tr("💾 Save File"), command=self.save_file, cursor="hand2", fg_color="#10B981", hover_color="#059669", height=40)
        self.save_btn.grid(row=0, column=3, sticky="e", padx=(0, 10))

        self.send_btn = ctk.CTkButton(self.action_bar, text=self.tr("↗ Send to Translate"), command=self.send_to_translate, cursor="hand2", fg_color="#8B5CF6", hover_color="#7C3AED", height=40)
        self.send_btn.grid(row=0, column=4, sticky="e")

        self.selected_file = None
        self.translate_tab = None
        self.cancel_event = None

    def set_translate_tab(self, translate_tab):
        self.translate_tab = translate_tab

    def _start_ui_queue_loop(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.after(50, self._start_ui_queue_loop)

    def select_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[
                ("Video/Audio Files", "*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.wav *.flac *.m4a *.ogg *.aac"),
                ("All Files", "*.*"),
            ]
        )
        if filename:
            self.selected_file = filename
            basename = os.path.basename(filename)
            self.file_label.configure(text=basename, text_color=("black", "white"))

    def log_status(self, msg: str):
        self.ui_queue.put(lambda m=msg: self.status_label.configure(text=m))

    def update_progress(self, value: float, status: str = ""):
        self.ui_queue.put(lambda v=value: self.progress.set(v))
        if status:
            self.log_status(status)

    def start_extraction(self):
        if not self.selected_file:
            messagebox.showerror(self.tr("Error"), self.tr("Please select a video/audio file first."))
            return

        model_size = self.model_var.get()
        language = self.lang_var.get().strip()
        self.extracted_format = self.format_var.get()

        self.output_text.delete("0.0", "end")
        self.extract_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.progress.set(0)
        self.log_status(self.tr("Starting..."))

        self.cancel_event = threading.Event()
        threading.Thread(
            target=self._extraction_thread,
            args=(self.selected_file, model_size, language),
            daemon=True,
        ).start()

    def cancel_extraction(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.log_status(self.tr("Cancelling (waiting for Whisper to finish background task)..."))
            self.cancel_btn.configure(state="disabled")

    def _extraction_thread(self, file_path, model_size, language):
        try:
            from core.stt_service import STTService

            if self.stt_service is None or self.stt_service.model_size != model_size:
                self.stt_service = STTService(model_size=model_size)

            segments, detected_lang = self.stt_service.transcribe(
                file_path=file_path,
                language=language,
                progress_callback=self.update_progress,
            )

            if self.cancel_event and self.cancel_event.is_set():
                self.ui_queue.put(lambda: self.log_status(self.tr("Extraction cancelled by user.")))
                return

            fmt = self.extracted_format
            if fmt == "srt":
                output = STTService.segments_to_srt(segments)
            else:
                output = STTService.segments_to_vtt(segments)

            self.extracted_text = output
            self.ui_queue.put(lambda o=output, dl=detected_lang: self._show_result(o, dl))

        except Exception as e:
            if not (self.cancel_event and self.cancel_event.is_set()):
                import logging
                logging.exception("Error during extraction thread:")
                self.ui_queue.put(lambda err=str(e): self._show_error(err))
        finally:
            self.ui_queue.put(lambda: self.extract_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.cancel_btn.configure(state="disabled"))

    def _show_result(self, output, detected_lang):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", output)
        self.log_status(self.tr("Done! Detected Audio Language: {detected_lang}", detected_lang=detected_lang))

    def _show_error(self, err):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", f"[{self.tr('Error')}] {err}")
        self.log_status(self.tr("Error!"))

    def save_file(self):
        content = self.output_text.get("0.0", "end").strip()
        if not content:
            messagebox.showerror(self.tr("Error"), self.tr("No subtitles to save."))
            return

        fmt = self.extracted_format
        if fmt == "srt":
            default_ext = ".srt"
            filetypes = [("SRT files", "*.srt"), ("VTT files", "*.vtt"), ("All Files", "*.*")]
        else:
            default_ext = ".vtt"
            filetypes = [("VTT files", "*.vtt"), ("SRT files", "*.srt"), ("All Files", "*.*")]

        filename = filedialog.asksaveasfilename(defaultextension=default_ext, filetypes=filetypes)
        if filename:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo(self.tr("Saved"), self.tr("Subtitles saved to {filename}", filename=filename))

    def send_to_translate(self):
        content = self.output_text.get("0.0", "end").strip()
        if not content:
            messagebox.showerror(self.tr("Error"), self.tr("No subtitles to send."))
            return

        if self.translate_tab:
            self.translate_tab.input_text.delete("0.0", "end")
            self.translate_tab.input_text.insert("0.0", content)
            tabview = self.master.master
            tabview.set(self.tr("Translate"))
        else:
            messagebox.showerror(self.tr("Error"), self.tr("Translate tab not available."))
