import threading
import queue
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.engine import TranslationEngine
from core.translator import TranslatorService, OpenAIProvider, GeminiProvider, CustomOpenAIProvider, NvidiaProvider


class TranslateTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.detected_format = "vtt"

        self.ui_queue = queue.Queue()
        self._start_ui_queue_loop()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Text areas row

        # --- Top Settings Card ---
        self.settings_card = ctk.CTkFrame(self)
        self.settings_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        self.settings_card.grid_columnconfigure(5, weight=1)
        
        ctk.CTkLabel(self.settings_card, text="Provider:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        self.provider_var = ctk.StringVar(value="openai")
        self.provider_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.provider_var, command=self.on_provider_change, cursor="hand2")
        self.provider_dropdown.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_card, text="Model:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=(15, 5), pady=10, sticky="w")
        self.model_var = ctk.StringVar(value="Loading...")
        self.model_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.model_var, cursor="hand2")
        self.model_dropdown.grid(row=0, column=3, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_card, text="Key Mode:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=4, padx=(15, 5), pady=10, sticky="w")
        self.key_mode_var = ctk.StringVar(value="Auto-Rotate")
        self.key_mode_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.key_mode_var, values=["Auto-Rotate", "Specific Key"], cursor="hand2")
        self.key_mode_dropdown.grid(row=0, column=5, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_card, text="Target Lang:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=(15, 5), pady=(0, 15), sticky="w")
        self.lang_var = ctk.StringVar(value="Vietnamese")
        self.lang_entry = ctk.CTkEntry(self.settings_card, textvariable=self.lang_var, width=140)
        self.lang_entry.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="w")

        ctk.CTkLabel(self.settings_card, text="Chunk Size:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=2, padx=(15, 5), pady=(0, 15), sticky="w")
        self.chunk_var = ctk.StringVar(value="1000")
        self.chunk_entry = ctk.CTkEntry(self.settings_card, textvariable=self.chunk_var, width=60)
        self.chunk_entry.grid(row=1, column=3, padx=5, pady=(0, 15), sticky="w")

        self.load_btn = ctk.CTkButton(self.settings_card, text="📂 Load Subtitle File", command=self.load_file, cursor="hand2", fg_color="#1E293B", border_color="#3B82F6", border_width=1)
        self.load_btn.grid(row=1, column=4, columnspan=2, padx=15, pady=(0, 15), sticky="w")
        
        self.file_label = ctk.CTkLabel(self.settings_card, text="No file selected...", text_color="gray")
        self.file_label.grid(row=1, column=6, padx=5, pady=(0, 15), sticky="e")

        # --- Context Card ---
        self.ctx_card = ctk.CTkFrame(self)
        self.ctx_card.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.ctx_card.grid_columnconfigure(0, weight=1)

        ctx_header = ctk.CTkFrame(self.ctx_card, fg_color="transparent")
        ctx_header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(ctx_header, text="Context / Background Details:", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.style_var = ctk.StringVar(value="Custom/Manual")
        self.style_dropdown = ctk.CTkOptionMenu(
            ctx_header, 
            variable=self.style_var, 
            values=["Custom/Manual", "Short Drama", "Historical", "Anime", "Documentary", "Tech/Tutorial", "Comedy", "Vlog", "News"],
            command=self.on_style_selected,
            cursor="hand2"
        )
        self.style_dropdown.pack(side="right")
        ctk.CTkLabel(ctx_header, text="Quick Style:").pack(side="right", padx=10)

        self.context_text = ctk.CTkTextbox(self.ctx_card, height=60, border_spacing=5)
        self.context_text.pack(fill="x", padx=10, pady=(0, 10))

        # --- Text Areas (Split) ---
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        self.text_frame.grid_columnconfigure(0, weight=1)
        self.text_frame.grid_columnconfigure(1, weight=1)
        self.text_frame.grid_rowconfigure(1, weight=1)

        input_header = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        input_header.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(input_header, text="Input Subtitles (VTT/SRT)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.clear_input_btn = ctk.CTkButton(input_header, text="✕ Clear", width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.input_text.delete("0.0", "end"))
        self.clear_input_btn.pack(side="right")

        output_header = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        output_header.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(output_header, text="Translated Output", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.clear_output_btn = ctk.CTkButton(output_header, text="✕ Clear", width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.output_text.delete("0.0", "end"))
        self.clear_output_btn.pack(side="right")

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

        self.translate_btn = ctk.CTkButton(self.action_bar, text="▶ Start Translation", font=ctk.CTkFont(weight="bold"), command=self.start_translation, cursor="hand2", height=40)
        self.translate_btn.grid(row=0, column=0, sticky="w")
        
        self.cancel_btn = ctk.CTkButton(self.action_bar, text="⏹ Cancel", font=ctk.CTkFont(weight="bold"), command=self.cancel_translation, cursor="hand2", height=40, fg_color="#DC2626", hover_color="#B91C1C", state="disabled")
        self.cancel_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.progress_frame = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        self.progress_frame.grid(row=0, column=2, sticky="ew", padx=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        status_row = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        status_row.grid(row=0, column=0, sticky="ew", pady=(0, 2))
        status_row.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(status_row, text="Ready", text_color="gray", font=ctk.CTkFont(size=12))
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

        self.save_btn = ctk.CTkButton(self.action_bar, text="💾 Save File", command=self.save_file, cursor="hand2", fg_color="#10B981", hover_color="#059669", height=40)
        self.save_btn.grid(row=0, column=3, sticky="e")

        self.after(100, self.refresh_providers)

    def on_style_selected(self, value):
        if value == "Custom/Manual":
            self.context_text.pack(fill="x", padx=10, pady=(0, 10))
            return
            
        styles = {
            "Short Drama": "This is the subtitle of a fast-paced modern short-drama. Translate using natural, modern language, and incorporate current popular slang where appropriate. Keep the sentences concise, sharp, and decisive.",
            "Historical": "This is a subtitle for a historical fantasy (Xianxia) drama. Please use a formal, poetic, and classic linguistic style. Accurately use royal and feudal pronouns and honorifics where applicable.",
            "Anime": "Translate this subtitle in a friendly, fun, and warm tone suitable for family animation/anime. Use gentle phrasing and vivid expressive words naturally. Try to keep sentences short.",
            "Documentary": "Translate this content from the perspective of an academic or educational television documentary. The translation must ensure absolute accuracy for specialized terminology. The tone should be objective, formal, and clear.",
            "Tech/Tutorial": "This is a technical video/tutorial about programming or technology. Ensure all technical terms are translated accurately or kept in English if that is the industry standard. The tone should be professional, instructional, and clear.",
            "Comedy": "This is a comedy show or stand-up routine. Translate the jokes naturally to match the target language's sense of humor. Use cultural equivalents to preserve the punchlines, keeping the language informal.",
            "Vlog": "This is a casual daily vlog or YouTube video. The translation should be highly conversational, energetic, and relatable. Use everyday language, common internet slang, and friendly expressions.",
            "News": "This is a news broadcast or journalistic report. The translation must be highly objective, formal, and strictly factual. Maintain a professional anchor-style tone without emotional bias."
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
        self.model_dropdown.configure(values=["Loading models..."])
        self.model_var.set("Loading...")
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
            models = ["No models found"]
            
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
            messagebox.showinfo("Saved", "File saved successfully.")

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
            messagebox.showerror("Error", "Please input text or load a file.")
            return
            
        provider_id = self.provider_var.get()
        model_name = self.model_var.get()
        target_lang = self.lang_var.get()
        auto_rotate = self.key_mode_var.get() == "Auto-Rotate"
        
        try:
            chunk_size = int(self.chunk_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Chunk Size must be a valid integer.")
            return
        
        keys = self.config_manager.get_keys(provider_id)
        if not keys and provider_id in ["openai", "gemini", "nvidia"]:
            messagebox.showerror("Error", f"No API keys configured for {provider_id}.")
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
                messagebox.showerror("Error", "Custom provider not found.")
                return
            provider_inst = CustomOpenAIProvider(base_url=cust.get("base_url"), custom_headers=cust.get("headers", {}))

        service = TranslatorService(provider_inst, keys, auto_rotate=auto_rotate)
        engine = TranslationEngine(service)

        self.output_text.delete("0.0", "end")
        self.log(f"Starting translation to {target_lang} using {provider_id} ({model_name})...")
        self.log_status("Initializing translation engine...")
        self.translate_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        
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
            self.log_status("Cancelling...")
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
                self.log_status("Translation cancelled.")
                # We still show what we got decoded so far
                if final_text:
                    self.ui_queue.put(lambda f=final_text: self._set_final_output(f))
            else:
                self.detected_format = detected_fmt
                fmt_label = detected_fmt.upper()
                self.log(f"\n--- FINAL TRANSLATED {fmt_label} ---\n" + final_text)
                self.log_status("Translation completed successfully!")
                self.ui_queue.put(lambda f=final_text: self._set_final_output(f))
                
        except Exception as e:
            self.log(f"\n[ERROR] Translation failed: {e}")
            self.log_status("Translation failed.")
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

    def _set_final_output(self, final_text):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", final_text)
