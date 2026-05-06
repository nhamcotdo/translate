import threading
import queue
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.engine import TranslationEngine
from core.translator import TranslatorService, OpenAIProvider, GeminiProvider, CustomOpenAIProvider, NvidiaProvider
from core.vtt_parser import SubtitleProcessor
from core.auto_fix import run_auto_fix
from ui.translations import get_tr

class TranslateZhViTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.tr = get_tr(self.config_manager)
        self.detected_format = "vtt"

        self.ui_queue = queue.Queue()
        self._start_ui_queue_loop()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Text areas row

        # --- Top Settings Card ---
        self.settings_card = ctk.CTkFrame(self)
        self.settings_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        self.settings_card.grid_columnconfigure(5, weight=1)
        
        ctk.CTkLabel(self.settings_card, text=self.tr("Provider:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        self.provider_var = ctk.StringVar(value="openai")
        self.provider_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.provider_var, command=self.on_provider_change, cursor="hand2")
        self.provider_dropdown.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_card, text=self.tr("Model:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=(15, 5), pady=10, sticky="w")
        self.model_var = ctk.StringVar(value=self.tr("Loading..."))
        self.model_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.model_var, cursor="hand2")
        self.model_dropdown.grid(row=0, column=3, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_card, text=self.tr("Key Mode:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=(15, 5), pady=10, sticky="w")
        self.key_mode_var = ctk.StringVar(value=self.tr("Auto-Rotate"))
        self.key_mode_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.key_mode_var, values=[self.tr("Auto-Rotate"), self.tr("Specific Key")], cursor="hand2")
        self.key_mode_dropdown.grid(row=0, column=5, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_card, text=self.tr("Target Lang:"), font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="w")
        self.lang_var = ctk.StringVar(value="Vietnamese")
        self.lang_entry = ctk.CTkEntry(self.settings_card, textvariable=self.lang_var, width=140, state="disabled")
        self.lang_entry.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="w")

        ctk.CTkLabel(self.settings_card, text=self.tr("Chunk Size:"), font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=(15, 5), pady=(0, 15), sticky="w")
        self.chunk_var = ctk.StringVar(value="1000")
        self.chunk_entry = ctk.CTkEntry(self.settings_card, textvariable=self.chunk_var, width=60)
        self.chunk_entry.grid(row=1, column=3, padx=5, pady=(0, 15), sticky="w")

        self.load_btn = ctk.CTkButton(self.settings_card, text=self.tr("📂 Load Subtitle File"), command=self.load_file, cursor="hand2", fg_color="#1E293B", border_color="#3B82F6", border_width=1)
        self.load_btn.grid(row=1, column=4, columnspan=2, padx=15, pady=(0, 15), sticky="w")
        
        self.file_label = ctk.CTkLabel(self.settings_card, text=self.tr("No file selected..."), text_color="gray")
        self.file_label.grid(row=1, column=6, padx=5, pady=(0, 15), sticky="e")

        # --- Context Card ---
        self.ctx_card = ctk.CTkFrame(self)
        self.ctx_card.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.ctx_card.grid_columnconfigure(0, weight=1)

        ctx_header = ctk.CTkFrame(self.ctx_card, fg_color="transparent")
        ctx_header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(ctx_header, text=self.tr("Context / Background Details:"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.style_var = ctk.StringVar(value="Phim Ngắn (Short Drama)")
        self.style_dropdown = ctk.CTkOptionMenu(
            ctx_header, 
            variable=self.style_var, 
            values=["Phim Ngắn (Short Drama)", "Tiên Hiệp (Xianxia)", "Hiện Đại (Modern)", "Hoạt Hình (Donghua)", "Review Phim (Movie Recap)", "Custom/Manual"],
            command=self.on_style_selected,
            cursor="hand2"
        )
        self.style_dropdown.pack(side="right")
        ctk.CTkLabel(ctx_header, text=self.tr("Quick Style:")).pack(side="right", padx=10)

        self.context_text = ctk.CTkTextbox(self.ctx_card, height=60, border_spacing=5)
        self.context_text.pack(fill="x", padx=10, pady=(0, 10))
        self.on_style_selected(self.style_var.get())

        # --- Text Areas (Split) ---
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_columnconfigure(1, weight=1)
        self.text_frame.grid_rowconfigure(1, weight=1)

        input_header = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        input_header.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(input_header, text=self.tr("Input Subtitles (VTT/SRT)"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.clear_input_btn = ctk.CTkButton(input_header, text=self.tr("✕ Clear"), width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.input_text.delete("0.0", "end"))
        self.clear_input_btn.pack(side="right")

        output_header = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        output_header.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(output_header, text=self.tr("Translated Output"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.clear_output_btn = ctk.CTkButton(output_header, text=self.tr("✕ Clear"), width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.output_text.delete("0.0", "end"))
        self.clear_output_btn.pack(side="right")

        self.split_output_btn = ctk.CTkButton(output_header, text=self.tr("✂️ Split Lines"), width=100, height=24, fg_color="#0EA5E9", hover_color="#0284C7", cursor="hand2", command=self.split_long_lines)
        self.split_output_btn.pack(side="right", padx=(0, 10))

        self.input_text = ctk.CTkTextbox(self.text_frame, border_spacing=10, wrap="word")
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        # Add keyboard shortcut
        self.input_text.bind("<Command-Return>", lambda e: self.start_translation())
        self.input_text.bind("<Control-Return>", lambda e: self.start_translation())

        self.output_text = ctk.CTkTextbox(self.text_frame, border_spacing=10, wrap="word")
        self.output_text.grid(row=1, column=1, sticky="nsew", padx=(5, 0))

        # --- Action Bar ---
        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.action_bar.grid_columnconfigure(1, weight=1)

        self.translate_btn = ctk.CTkButton(self.action_bar, text=self.tr("▶ Start Translation"), font=ctk.CTkFont(weight="bold"), command=self.start_translation, cursor="hand2", height=40)
        self.translate_btn.grid(row=0, column=0, sticky="w")
        
        self.cancel_btn = ctk.CTkButton(self.action_bar, text=self.tr("⏹ Cancel"), font=ctk.CTkFont(weight="bold"), command=self.cancel_translation, cursor="hand2", height=40, fg_color="#DC2626", hover_color="#B91C1C", state="disabled")
        self.cancel_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.progress_frame = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        self.progress_frame.grid(row=0, column=2, sticky="ew", padx=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        status_row = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        status_row.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(status_row, text=self.tr("Ready"), text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="w")
        
        self.time_label = ctk.CTkLabel(status_row, text="", text_color="#94A3B8", font=ctk.CTkFont(size=11))
        self.time_label.grid(row=0, column=1, sticky="e")
        
        self.progress = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)
        
        # Time tracking state
        self._translation_start_time = None
        self._translation_running = False
        self._timer_job = None

        self.autofix_btn = ctk.CTkButton(
            self.action_bar,
            text=self.tr("🔧 Auto-Fix Chinese"),
            command=self.start_auto_fix,
            cursor="hand2",
            fg_color="#7C3AED",
            hover_color="#6D28D9",
            height=40
        )
        self.autofix_btn.grid(row=0, column=3, sticky="e", padx=(10, 0))

        self.fill_missing_btn = ctk.CTkButton(
            self.action_bar,
            text=self.tr("🔍 Detect & Fill Missing"),
            command=self.start_fill_missing,
            cursor="hand2",
            fg_color="#F59E0B",
            hover_color="#D97706",
            height=40
        )
        self.fill_missing_btn.grid(row=0, column=4, sticky="e", padx=(10, 0))

        self.save_btn = ctk.CTkButton(self.action_bar, text=self.tr("💾 Save File"), command=self.save_file, cursor="hand2", fg_color="#10B981", hover_color="#059669", height=40)
        self.save_btn.grid(row=0, column=5, sticky="e", padx=(10, 0))

        self.after(100, self.refresh_providers)

    def on_style_selected(self, value):
        if value == "Custom/Manual":
            self.context_text.pack(fill="x", padx=10, pady=(0, 10))
            return
            
        styles = {
            "Phim Ngắn (Short Drama)": "Đây là phụ đề của một bộ phim ngắn hiện đại (short drama) Trung Quốc. Dịch sang tiếng Việt một cách tự nhiên, ngôn ngữ hiện đại, có thể dùng từ lóng giới trẻ. Câu văn cần súc tích, dứt khoát.",
            "Tiên Hiệp (Xianxia)": "Đây là phụ đề phim cổ trang tiên hiệp/kiếm hiệp Trung Quốc. Dịch sang tiếng Việt với phong cách trang trọng, mang âm hưởng Hán Việt. Sử dụng chính xác các đại từ nhân xưng cổ đại (tại hạ, các hạ, sư tôn, đồ đệ, muội muội...).",
            "Hiện Đại (Modern)": "Đây là phụ đề phim ngôn tình/tâm lý xã hội hiện đại Trung Quốc. Dịch sang tiếng Việt tự nhiên, phù hợp với ngữ cảnh giao tiếp hàng ngày. Chú ý giữ đúng các xưng hô (anh, em, tổng tài, cô nại nại...).",
            "Hoạt Hình (Donghua)": "Đây là phụ đề phim hoạt hình (Donghua) Trung Quốc. Dịch sang tiếng Việt thân thiện, dễ hiểu, phù hợp với đối tượng khán giả trẻ hoặc gia đình.",
            "Review Phim (Movie Recap)": "Đây là phụ đề của một video tóm tắt/review phim. Dịch sang tiếng Việt với giọng điệu kể chuyện hấp dẫn, lôi cuốn và diễn cảm. Ngôn từ cần sinh động để thu hút người xem."
        }
        
        if value in styles:
            self.context_text.delete("0.0", "end")
            self.context_text.insert("0.0", styles[value])
            self.context_text.pack_forget()

    def refresh_providers(self):
        providers = ["openai", "gemini", "nvidia"]
        customs = self.config_manager.get_custom_providers()
        providers.extend(list(customs.keys()))
        
        self.provider_dropdown.configure(values=providers)
        
        curr = self.provider_var.get()
        if curr not in providers:
            self.provider_var.set("openai")
            self.on_provider_change("openai")
        else:
            self.on_provider_change(curr)

    def _start_ui_queue_loop(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.after(50, self._start_ui_queue_loop)

    def on_provider_change(self, value):
        self.model_dropdown.configure(values=[self.tr("Loading models...")])
        self.model_var.set(self.tr("Loading..."))
        threading.Thread(target=self._fetch_models_thread, args=(value,), daemon=True).start()

    def _fetch_models_thread(self, provider_id):
        keys = self.config_manager.get_keys(provider_id)
        api_key = keys[0] if keys else ""
        
        try:
            if provider_id == "openai":
                provider_inst = OpenAIProvider()
                models = provider_inst.get_available_models(api_key)
            elif provider_id == "gemini":
                provider_inst = GeminiProvider()
                models = provider_inst.get_available_models(api_key)
            elif provider_id == "nvidia":
                provider_inst = NvidiaProvider()
                models = provider_inst.get_available_models(api_key)
            else:
                cust = self.config_manager.get_custom_providers().get(provider_id, {})
                provider_inst = CustomOpenAIProvider(base_url=cust.get("base_url", ""), custom_headers=cust.get("headers", {}))
                models = provider_inst.get_available_models(api_key)
                if not models:
                    models = cust.get("models", [])
        except Exception:
            models = []
                
        if not models:
            models = [self.tr("No models found")]
            
        self.ui_queue.put(lambda m=models: self._update_model_dropdown(m))
        
    def _update_model_dropdown(self, models):
        self.model_dropdown.configure(values=models)
        self.model_var.set(models[0] if models else "")

    def load_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.vtt *.srt"), ("All Files", "*.*")])
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.input_text.delete("0.0", "end")
            self.input_text.insert("0.0", content)
            
            import os
            self.file_label.configure(text=os.path.basename(filename))

    def save_file(self):
        if self.detected_format == "srt":
            default_ext = ".srt"
            filetypes = [("SRT files", "*.srt"), ("VTT files", "*.vtt"), ("All Files", "*.*")]
        else:
            default_ext = ".vtt"
            filetypes = [("VTT files", "*.vtt"), ("SRT files", "*.srt"), ("All Files", "*.*")]
        
        filename = filedialog.asksaveasfilename(defaultextension=default_ext, filetypes=filetypes)
        if filename:
            content = self.output_text.get("0.0", "end")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content.strip())
            messagebox.showinfo(self.tr("Saved"), self.tr("File saved successfully."))

    def log(self, msg: str):
        self.ui_queue.put(lambda m=msg: self._append_log(m))
        
    def log_status(self, msg: str):
        self.ui_queue.put(lambda m=msg: self.status_label.configure(text=m))

    def _append_log(self, msg: str):
        self.output_text.insert("end", msg + "\n")
        self.output_text.see("end")

    def _format_duration(self, seconds: float) -> str:
        """Format seconds into mm:ss or hh:mm:ss."""
        seconds = int(seconds)
        if seconds < 0:
            seconds = 0
        hrs, rem = divmod(seconds, 3600)
        mins, secs = divmod(rem, 60)
        if hrs > 0:
            return f"{hrs}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def _update_timer(self):
        """Update elapsed and estimated time labels every second."""
        if not self._translation_running or self._translation_start_time is None:
            return
        elapsed = time.time() - self._translation_start_time
        elapsed_str = self._format_duration(elapsed)
        
        est_str = ""
        if hasattr(self, '_chunks_done') and hasattr(self, '_chunks_total') and self._chunks_done > 0:
            avg_per_chunk = elapsed / self._chunks_done
            remaining = (self._chunks_total - self._chunks_done) * avg_per_chunk
            est_str = f"  ⏳ ~{self._format_duration(remaining)} left"
        
        self.time_label.configure(text=f"⏱ {elapsed_str}{est_str}")
        self._timer_job = self.after(1000, self._update_timer)

    def update_progress(self, current: int, total: int):
        val = current / total if total > 0 else 0
        self._chunks_done = current
        self._chunks_total = total
        self.ui_queue.put(lambda v=val: self.progress.set(v))
        self.log_status(f"Processing chunk {current}/{total}...")

    def start_translation(self):
        vtt_input = self.input_text.get("0.0", "end").strip()
        pre_ctx = self.context_text.get("0.0", "end").strip()
        if not vtt_input:
            messagebox.showerror(self.tr("Error"), self.tr("Please input text or load a file."))
            return
            
        provider_id = self.provider_var.get()
        model_name = self.model_var.get()
        target_lang = self.lang_var.get()
        auto_rotate = self.key_mode_var.get() == self.tr("Auto-Rotate")
        
        try:
            chunk_size = int(self.chunk_var.get().strip())
        except ValueError:
            messagebox.showerror(self.tr("Error"), self.tr("Chunk Size must be a valid integer."))
            return
        
        keys = self.config_manager.get_keys(provider_id)
        if not keys and provider_id in ["openai", "gemini", "nvidia"]:
            messagebox.showerror(self.tr("Error"), self.tr(f"No API keys configured for {provider_id}."))
            return
            
        if provider_id == "openai":
            provider_inst = OpenAIProvider()
        elif provider_id == "gemini":
            provider_inst = GeminiProvider()
        elif provider_id == "nvidia":
            provider_inst = NvidiaProvider()
        else:
            cust = self.config_manager.get_custom_providers().get(provider_id)
            if not cust:
                messagebox.showerror(self.tr("Error"), self.tr("Custom provider not found."))
                return
            provider_inst = CustomOpenAIProvider(base_url=cust.get("base_url"), custom_headers=cust.get("headers", {}))

        service = TranslatorService(provider_inst, keys, auto_rotate=auto_rotate)
        engine = TranslationEngine(service)

        self.output_text.delete("0.0", "end")
        self.log(f"Starting translation to {target_lang} using {provider_id} ({model_name})...")
        self.log_status(self.tr("Initializing translation engine..."))
        self.translate_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.autofix_btn.configure(state="disabled")
        self.fill_missing_btn.configure(state="disabled")
        
        # Start time tracking
        self._translation_start_time = time.time()
        self._translation_running = True
        self._chunks_done = 0
        self._chunks_total = 0
        self.time_label.configure(text="⏱ 00:00")
        self._update_timer()
        
        self.cancel_event = threading.Event()
        threading.Thread(target=self._run_translation_thread, args=(engine, vtt_input, target_lang, model_name, pre_ctx, chunk_size), daemon=True).start()

    def cancel_translation(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.log_status(self.tr("Cancelling..."))
            self.cancel_btn.configure(state="disabled")

    def _run_translation_thread(self, engine, vtt_input, target_lang, model_name, pre_ctx, chunk_size):
        try:
            final_text, detected_fmt = engine.run(
                subtitle_text=vtt_input,
                target_lang=target_lang,
                model_name=model_name,
                pre_context=pre_ctx,
                chunk_size=chunk_size,
                progress_callback=self.update_progress,
                log_callback=self.log,
                cancel_event=self.cancel_event
            )
            
            if self.cancel_event and self.cancel_event.is_set():
                self.log_status(self.tr("Translation cancelled."))
                # We still show what we got decoded so far
                if final_text:
                    self.ui_queue.put(lambda f=final_text: self._set_final_output(f))
            else:
                self.detected_format = detected_fmt
                fmt_label = detected_fmt.upper()
                self.log(f"\n--- FINAL TRANSLATED {fmt_label} ---\n" + final_text)
                self.log_status(self.tr("Translation completed successfully!"))
                self.ui_queue.put(lambda f=final_text: self._set_final_output(f))
                
        except Exception as e:
            import logging
            logging.exception("Error during translation thread:")
            self.log(f"\n[ERROR] Translation failed: {e}")
            self.log_status(self.tr("Translation failed."))
        finally:
            self._translation_running = False
            if self._timer_job:
                self.after_cancel(self._timer_job)
                self._timer_job = None
            # Show final elapsed time
            if self._translation_start_time:
                total_elapsed = time.time() - self._translation_start_time
                self.ui_queue.put(lambda t=total_elapsed: self.time_label.configure(text=f"✅ Total: {self._format_duration(t)}"))
            self.ui_queue.put(lambda: self.translate_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.cancel_btn.configure(state="disabled"))
            self.ui_queue.put(lambda: self.autofix_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.fill_missing_btn.configure(state="normal"))

    def _set_final_output(self, final_text):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", final_text)

    # ── Auto-Fix Chinese ──────────────────────────────────────────────────

    def _build_service(self):
        """Re-create a TranslatorService from current UI settings."""
        provider_id = self.provider_var.get()
        auto_rotate = self.key_mode_var.get() == self.tr("Auto-Rotate")
        keys = self.config_manager.get_keys(provider_id)

        if provider_id == "openai":
            provider_inst = OpenAIProvider()
        elif provider_id == "gemini":
            provider_inst = GeminiProvider()
        elif provider_id == "nvidia":
            provider_inst = NvidiaProvider()
        else:
            cust = self.config_manager.get_custom_providers().get(provider_id)
            if not cust:
                return None, None
            provider_inst = CustomOpenAIProvider(
                base_url=cust.get("base_url"),
                custom_headers=cust.get("headers", {})
            )

        service = TranslatorService(provider_inst, keys, auto_rotate=auto_rotate)
        return service, provider_id

    def start_auto_fix(self):
        """Detect Chinese chars in the output box and re-translate them."""
        output_content = self.output_text.get("0.0", "end").strip()
        if not output_content:
            messagebox.showerror(self.tr("Error"), self.tr("Output is empty. Please translate first."))
            return

        model_name = self.model_var.get()
        target_lang = self.lang_var.get()

        service, provider_id = self._build_service()
        if service is None:
            messagebox.showerror(self.tr("Error"), self.tr("Custom provider not found."))
            return

        keys = self.config_manager.get_keys(provider_id)
        if not keys and provider_id in ["openai", "gemini", "nvidia"]:
            messagebox.showerror(self.tr("Error"), self.tr(f"No API keys configured for {provider_id}."))
            return

        # Parse the current output back to subtitle dicts
        detected_fmt = SubtitleProcessor.detect_format(output_content)
        subs = SubtitleProcessor.parse_auto(output_content)
        if not subs:
            messagebox.showerror(self.tr("Error"), self.tr("Could not parse output as VTT/SRT."))
            return

        self.autofix_btn.configure(state="disabled")
        self.translate_btn.configure(state="disabled")
        self.fill_missing_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.log_status(self.tr("Auto-fixing Chinese characters..."))
        self.progress.set(0)

        self._translation_start_time = time.time()
        self._translation_running = True
        self._chunks_done = 0
        self._chunks_total = 0
        self.time_label.configure(text="⏱ 00:00")
        self._update_timer()

        self.cancel_event = threading.Event()
        threading.Thread(
            target=self._run_auto_fix_thread,
            args=(subs, detected_fmt, target_lang, model_name, service),
            daemon=True
        ).start()

    def _run_auto_fix_thread(self, subs, detected_fmt, target_lang, model_name, service):
        try:
            fixed_subs = run_auto_fix(
                subs=subs,
                target_lang=target_lang,
                model_name=model_name,
                translator_service=service,
                context_window=2,
                log_callback=self.log,
                progress_callback=self.update_progress,
                cancel_event=self.cancel_event,
            )

            final_text = SubtitleProcessor.to_format(fixed_subs, detected_fmt)

            if self.cancel_event and self.cancel_event.is_set():
                self.log_status(self.tr("Auto-fix cancelled."))
            else:
                self.log_status(self.tr("Auto-fix completed!"))

            self.ui_queue.put(lambda f=final_text: self._set_final_output(f))

        except Exception as e:
            import logging
            logging.exception("Error during auto-fix thread:")
            self.log(f"\n[ERROR] Auto-fix failed: {e}")
            self.log_status(self.tr("Auto-fix failed."))
        finally:
            self._translation_running = False
            if self._timer_job:
                self.after_cancel(self._timer_job)
                self._timer_job = None
            if self._translation_start_time:
                total_elapsed = time.time() - self._translation_start_time
                self.ui_queue.put(lambda t=total_elapsed: self.time_label.configure(
                    text=f"✅ Total: {self._format_duration(t)}"
                ))
            self.ui_queue.put(lambda: self.translate_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.cancel_btn.configure(state="disabled"))
            self.ui_queue.put(lambda: self.autofix_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.fill_missing_btn.configure(state="normal"))

    # ── Detect & Fill Missing ─────────────────────────────────────────────

    def start_fill_missing(self):
        vtt_input = self.input_text.get("0.0", "end").strip()
        vtt_output = self.output_text.get("0.0", "end").strip()
        
        if not vtt_input or not vtt_output:
            messagebox.showerror(self.tr("Error"), self.tr("Both input and output text must be present."))
            return

        service, provider_id = self._build_service()
        if service is None:
            messagebox.showerror(self.tr("Error"), self.tr("Custom provider not found."))
            return

        keys = self.config_manager.get_keys(provider_id)
        if not keys and provider_id in ["openai", "gemini", "nvidia"]:
            messagebox.showerror(self.tr("Error"), self.tr(f"No API keys configured for {provider_id}."))
            return

        in_subs = SubtitleProcessor.parse_auto(vtt_input)
        out_subs = SubtitleProcessor.parse_auto(vtt_output)
        
        out_map = {}
        for s in out_subs:
            key = f"{s['start']}_{s['end']}"
            out_map[key] = s['text']
            
        missing_subs = []
        for s in in_subs:
            key = f"{s['start']}_{s['end']}"
            if key not in out_map:
                missing_subs.append(s)
            elif out_map[key] == s['text'] and s['text'].strip() != "":
                # Text is exactly identical to input and not empty -> likely untranslated
                missing_subs.append(s)
                
        if not missing_subs:
            msg = self.tr(f"No missing or untranslated lines detected.\n\nParsed Input: {len(in_subs)} blocks\nParsed Output: {len(out_subs)} blocks\n\nIf the block count differs, it is likely due to the automatic removal of exact duplicates (hallucinations) during the initial translation.")
            messagebox.showinfo(self.tr("Info"), msg)
            return

        self.fill_missing_btn.configure(state="disabled")
        self.autofix_btn.configure(state="disabled")
        self.translate_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.log_status(self.tr(f"Filling {len(missing_subs)} missing lines..."))
        self.progress.set(0)

        self._translation_start_time = time.time()
        self._translation_running = True
        self._chunks_done = 0
        
        try:
            chunk_size = int(self.chunk_var.get().strip())
        except ValueError:
            chunk_size = 15
            
        self._chunks_total = (len(missing_subs) + chunk_size - 1) // chunk_size
        self.time_label.configure(text="⏱ 00:00")
        self._update_timer()

        model_name = self.model_var.get()
        target_lang = self.lang_var.get()
        pre_ctx = self.context_text.get("0.0", "end").strip()

        self.cancel_event = threading.Event()
        threading.Thread(
            target=self._run_fill_missing_thread,
            args=(in_subs, out_map, missing_subs, target_lang, model_name, pre_ctx, chunk_size, service),
            daemon=True
        ).start()

    def _run_fill_missing_thread(self, in_subs, out_map, missing_subs, target_lang, model_name, pre_ctx, chunk_size, service):
        try:
            translated_missing = []
            chunks = list(SubtitleProcessor.chunk_subs(missing_subs, chunk_size=chunk_size))
            
            for i, chunk in enumerate(chunks):
                if self.cancel_event and self.cancel_event.is_set():
                    self.log_status(self.tr("Cancelled."))
                    break
                    
                chunk_to_translate = []
                for s in chunk:
                    if s["text"].strip():
                        chunk_to_translate.append(s)
                        
                if chunk_to_translate:
                    engine = TranslationEngine(service)
                    trans_chunk = engine.translate_chunk(chunk_to_translate, target_lang, model_name, pre_ctx, log_callback=self.log)
                    trans_dict = { f"{s['start']}_{s['end']}": s["text"] for s in trans_chunk }
                    
                    for s in chunk:
                        key = f"{s['start']}_{s['end']}"
                        s_copy = s.copy()
                        if not s["text"].strip():
                            s_copy["text"] = ""
                        else:
                            s_copy["text"] = trans_dict.get(key, s["text"])
                        translated_missing.append(s_copy)
                else:
                    for s in chunk:
                        s_copy = s.copy()
                        s_copy["text"] = ""
                        translated_missing.append(s_copy)
                        
                self.update_progress(i + 1, len(chunks))

            trans_missing_map = { f"{s['start']}_{s['end']}": s["text"] for s in translated_missing }
            
            final_subs = []
            for s in in_subs:
                key = f"{s['start']}_{s['end']}"
                if key in trans_missing_map:
                    s_copy = s.copy()
                    s_copy["text"] = trans_missing_map[key]
                    final_subs.append(s_copy)
                elif key in out_map:
                    s_copy = s.copy()
                    s_copy["text"] = out_map[key]
                    final_subs.append(s_copy)
                else:
                    final_subs.append(s)

            detected_fmt = SubtitleProcessor.detect_format(self.output_text.get("0.0", "end"))
            final_text = SubtitleProcessor.to_format(final_subs, detected_fmt)

            self.ui_queue.put(lambda f=final_text: self._set_final_output(f))
            if not (self.cancel_event and self.cancel_event.is_set()):
                self.log_status(self.tr("Missing lines filled!"))
            
        except Exception as e:
            import logging
            logging.exception("Error in fill missing thread")
            self.log(f"\n[ERROR] Failed to fill missing: {e}")
            self.log_status(self.tr("Failed to fill missing lines."))
        finally:
            self._translation_running = False
            if self._timer_job:
                self.after_cancel(self._timer_job)
                self._timer_job = None
            if self._translation_start_time:
                total_elapsed = time.time() - self._translation_start_time
                self.ui_queue.put(lambda t=total_elapsed: self.time_label.configure(
                    text=f"✅ Total: {self._format_duration(t)}"
                ))
            self.ui_queue.put(lambda: self.translate_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.cancel_btn.configure(state="disabled"))
            self.ui_queue.put(lambda: self.autofix_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.fill_missing_btn.configure(state="normal"))

    # ── Split Long Lines ──────────────────────────────────────────────────

    def split_long_lines(self):
        output_content = self.output_text.get("0.0", "end").strip()
        if not output_content:
            messagebox.showerror(self.tr("Error"), self.tr("Output is empty."))
            return

        dialog = ctk.CTkInputDialog(text=self.tr("Enter max characters per segment/line (e.g., 45):"), title=self.tr("Split Long Lines"))
        max_chars_str = dialog.get_input()
        if not max_chars_str:
            return
            
        try:
            max_chars = int(max_chars_str.strip())
        except ValueError:
            messagebox.showerror(self.tr("Error"), self.tr("Please enter a valid integer."))
            return

        split_to_blocks = messagebox.askyesno(
            self.tr("Split Mode"), 
            self.tr("Do you want to split into separate subtitle BLOCKS?\n\nYes = Create new blocks and divide the timestamp proportionally.\nNo = Just add line breaks (Enter) inside the same block.")
        )

        detected_fmt = SubtitleProcessor.detect_format(output_content)
        subs = SubtitleProcessor.parse_auto(output_content)
        
        def time_to_ms(time_str: str) -> int:
            time_str = time_str.replace(",", ".")
            parts = time_str.split(":")
            if len(parts) == 3:
                h, m, s_ms = parts
            else:
                h = 0
                m, s_ms = parts
            
            if "." in s_ms:
                s, ms = s_ms.split(".")
            else:
                s = s_ms
                ms = 0
                
            return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(str(ms)[:3].ljust(3, "0"))

        def ms_to_time(ms: float, sep=".") -> str:
            ms = max(0, int(ms))
            h = ms // 3600000
            ms = ms % 3600000
            m = ms // 60000
            ms = ms % 60000
            s = ms // 1000
            ms = ms % 1000
            return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"

        new_subs = []
        for s in subs:
            # Replace single newlines with space, but keep double newlines if any (rare in subtitles)
            text = s["text"].replace("\n", " ").strip()
            
            if len(text) <= max_chars:
                new_subs.append(s)
                continue
                
            words = text.split(" ")
            segments = []
            current_seg = []
            current_len = 0
            
            for w in words:
                if current_len + len(w) + 1 > max_chars and current_seg:
                    segments.append(" ".join(current_seg))
                    current_seg = [w]
                    current_len = len(w)
                else:
                    current_seg.append(w)
                    current_len += len(w) + 1 if current_len > 0 else len(w)
                    
            if current_seg:
                segments.append(" ".join(current_seg))
                
            if split_to_blocks and len(segments) > 1:
                total_len = sum(len(seg) for seg in segments)
                
                start_ms = time_to_ms(s["start"])
                end_ms = time_to_ms(s["end"])
                total_dur = end_ms - start_ms
                
                current_start_ms = start_ms
                for i, seg in enumerate(segments):
                    s_copy = s.copy()
                    s_copy["text"] = seg
                    
                    if total_len > 0:
                        seg_dur = total_dur * (len(seg) / total_len)
                    else:
                        seg_dur = total_dur / len(segments)
                        
                    seg_start_ms = current_start_ms
                    seg_end_ms = current_start_ms + seg_dur
                    
                    if i == len(segments) - 1:
                        seg_end_ms = end_ms # Ensure last segment ends exactly at end_ms
                        
                    s_copy["start"] = ms_to_time(seg_start_ms, sep=".")
                    s_copy["end"] = ms_to_time(seg_end_ms, sep=".")
                    
                    new_subs.append(s_copy)
                    current_start_ms = seg_end_ms
            else:
                s_copy = s.copy()
                s_copy["text"] = "\n".join(segments)
                new_subs.append(s_copy)
                
        final_text = SubtitleProcessor.to_format(new_subs, detected_fmt)
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", final_text)
        messagebox.showinfo(self.tr("Success"), self.tr("Split complete!"))
