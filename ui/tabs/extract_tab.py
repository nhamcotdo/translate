import os
import threading
import queue
import customtkinter as ctk
from tkinter import filedialog, messagebox


class ExtractTab(ctk.CTkFrame):
    """Tab for extracting subtitles from video/audio using Whisper STT."""

    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.config_manager = config_manager
        self.stt_service = None
        self.extracted_text = ""
        self.extracted_format = "srt"

        self.ui_queue = queue.Queue()
        self._start_ui_queue_loop()

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(4, weight=1)

        # Row 0: Title
        ctk.CTkLabel(self, text="Extract Subtitles from Video/Audio", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w"
        )

        # Row 1: Options
        self.opt_frame = ctk.CTkFrame(self)
        self.opt_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(self.opt_frame, text="Model:").pack(side="left", padx=5)
        self.model_var = ctk.StringVar(value="base")
        self.model_dropdown = ctk.CTkOptionMenu(
            self.opt_frame,
            variable=self.model_var,
            values=["tiny", "base", "small", "medium", "large"],
        )
        self.model_dropdown.pack(side="left", padx=5)

        ctk.CTkLabel(self.opt_frame, text="Language:").pack(side="left", padx=5)
        self.lang_var = ctk.StringVar(value="auto")
        self.lang_entry = ctk.CTkEntry(self.opt_frame, textvariable=self.lang_var, width=80)
        self.lang_entry.pack(side="left", padx=5)

        ctk.CTkLabel(self.opt_frame, text="Format:").pack(side="left", padx=5)
        self.format_var = ctk.StringVar(value="srt")
        self.format_dropdown = ctk.CTkOptionMenu(
            self.opt_frame,
            variable=self.format_var,
            values=["srt", "vtt"],
        )
        self.format_dropdown.pack(side="left", padx=5)

        # Row 2: File selection
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        self.load_btn = ctk.CTkButton(self.file_frame, text="Select Video/Audio File", command=self.select_file)
        self.load_btn.pack(side="left", padx=5)
        self.file_label = ctk.CTkLabel(self.file_frame, text="No file selected.")
        self.file_label.pack(side="left", padx=5, fill="x", expand=True)

        # Row 3: Actions
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        self.extract_btn = ctk.CTkButton(self.action_frame, text="Extract Subtitles", command=self.start_extraction)
        self.extract_btn.pack(side="left", padx=5)

        self.progress = ctk.CTkProgressBar(self.action_frame, width=300)
        self.progress.pack(side="left", padx=10, fill="x", expand=True)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(self.action_frame, text="")
        self.status_label.pack(side="right", padx=5)

        # Row 4: Output
        ctk.CTkLabel(self, text="Extracted Subtitles:").grid(row=4, column=0, padx=10, sticky="sw")
        self.output_text = ctk.CTkTextbox(self, height=300)
        self.output_text.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        self.grid_rowconfigure(5, weight=1)

        # Row 6: Save & Send to Translate
        self.bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        self.save_btn = ctk.CTkButton(self.bottom_frame, text="Save to File", command=self.save_file)
        self.save_btn.pack(side="right", padx=5)

        self.send_btn = ctk.CTkButton(self.bottom_frame, text="Send to Translate Tab", command=self.send_to_translate)
        self.send_btn.pack(side="right", padx=5)

        self.selected_file = None
        self.translate_tab = None  # Will be set externally

    def set_translate_tab(self, translate_tab):
        """Set reference to translate tab for sending extracted subtitles."""
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
            self.file_label.configure(text=basename)

    def log_status(self, msg: str):
        self.ui_queue.put(lambda m=msg: self.status_label.configure(text=m))

    def update_progress(self, value: float, status: str = ""):
        self.ui_queue.put(lambda v=value: self.progress.set(v))
        if status:
            self.log_status(status)

    def start_extraction(self):
        if not self.selected_file:
            messagebox.showerror("Error", "Please select a video/audio file first.")
            return

        model_size = self.model_var.get()
        language = self.lang_var.get().strip()
        self.extracted_format = self.format_var.get()

        self.output_text.delete("0.0", "end")
        self.extract_btn.configure(state="disabled")
        self.progress.set(0)
        self.log_status("Starting...")

        threading.Thread(
            target=self._extraction_thread,
            args=(self.selected_file, model_size, language),
            daemon=True,
        ).start()

    def _extraction_thread(self, file_path, model_size, language):
        try:
            from core.stt_service import STTService

            # Create or reuse service (reload if model changed)
            if self.stt_service is None or self.stt_service.model_size != model_size:
                self.stt_service = STTService(model_size=model_size)

            segments, detected_lang = self.stt_service.transcribe(
                file_path=file_path,
                language=language,
                progress_callback=self.update_progress,
            )

            # Format output
            fmt = self.extracted_format
            if fmt == "srt":
                output = STTService.segments_to_srt(segments)
            else:
                output = STTService.segments_to_vtt(segments)

            self.extracted_text = output

            self.ui_queue.put(lambda o=output, dl=detected_lang: self._show_result(o, dl))

        except Exception as e:
            self.ui_queue.put(lambda err=str(e): self._show_error(err))
        finally:
            self.ui_queue.put(lambda: self.extract_btn.configure(state="normal"))

    def _show_result(self, output, detected_lang):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", output)
        self.log_status(f"Done! Language: {detected_lang}")

    def _show_error(self, err):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", f"[ERROR] {err}")
        self.log_status("Error!")

    def save_file(self):
        content = self.output_text.get("0.0", "end").strip()
        if not content:
            messagebox.showerror("Error", "No subtitles to save.")
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
            messagebox.showinfo("Saved", f"Subtitles saved to {filename}")

    def send_to_translate(self):
        content = self.output_text.get("0.0", "end").strip()
        if not content:
            messagebox.showerror("Error", "No subtitles to send.")
            return

        if self.translate_tab:
            self.translate_tab.input_text.delete("0.0", "end")
            self.translate_tab.input_text.insert("0.0", content)
            # Switch to translate tab
            tabview = self.master.master  # CTkTabview
            tabview.set("Translate")
            messagebox.showinfo("Sent", "Subtitles sent to Translate tab.")
        else:
            messagebox.showerror("Error", "Translate tab not available.")


