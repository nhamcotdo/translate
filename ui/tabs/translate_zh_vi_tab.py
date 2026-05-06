import threading
import queue
import time
import customtkinter as ctk
from tkinter import messagebox

from core.translator import TranslatorService, OpenAIProvider, GeminiProvider, CustomOpenAIProvider, NvidiaProvider
from ui.translations import get_tr

class TranslateZhViTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.tr = get_tr(self.config_manager)

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

        # --- Context Card ---
        self.ctx_card = ctk.CTkFrame(self)
        self.ctx_card.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.ctx_card.grid_columnconfigure(0, weight=1)

        ctx_header = ctk.CTkFrame(self.ctx_card, fg_color="transparent")
        ctx_header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(ctx_header, text=self.tr("Context / Guidelines:"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        
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
        ctk.CTkLabel(input_header, text=self.tr("Tên Phim Tiếng Trung (Mỗi dòng 1 tên)"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.clear_input_btn = ctk.CTkButton(input_header, text=self.tr("✕ Clear"), width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.input_text.delete("0.0", "end"))
        self.clear_input_btn.pack(side="right")

        output_header = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        output_header.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ctk.CTkLabel(output_header, text=self.tr("Tên Phim Tiếng Việt"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.clear_output_btn = ctk.CTkButton(output_header, text=self.tr("✕ Clear"), width=60, height=24, fg_color="#334155", hover_color="#475569", cursor="hand2", command=lambda: self.output_text.delete("0.0", "end"))
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
        
        # Time tracking state
        self._translation_start_time = None
        self._translation_running = False
        self._timer_job = None
        self.cancel_event = None

        self.after(100, self.refresh_providers)

    def on_style_selected(self, value):
        if value == "Custom/Manual":
            self.context_text.pack(fill="x", padx=10, pady=(0, 10))
            return
            
        styles = {
            "Phim Ngắn (Short Drama)": "Dịch tên phim ngắn hiện đại. Dịch sang tiếng Việt tự nhiên, súc tích, giật gân, hấp dẫn.",
            "Tiên Hiệp (Xianxia)": "Dịch tên phim cổ trang tiên hiệp/kiếm hiệp. Ưu tiên dịch theo âm Hán Việt, nghe trang trọng, đậm chất kiếm hiệp.",
            "Hiện Đại (Modern)": "Dịch tên phim ngôn tình/tâm lý xã hội hiện đại. Dịch sang tiếng Việt tự nhiên, nghe ngôn tình, lãng mạn.",
            "Hoạt Hình (Donghua)": "Dịch tên phim hoạt hình (Donghua). Dịch sang tiếng Việt dễ hiểu, phù hợp với đối tượng khán giả trẻ.",
            "Review Phim (Movie Recap)": "Dịch tên phim cho video review. Tên phim cần dễ nhớ, có yếu tố thu hút sự chú ý của người xem (Clickbait hợp lý)."
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

    def log_status(self, msg: str):
        self.ui_queue.put(lambda m=msg: self.status_label.configure(text=m))

    def _format_duration(self, seconds: float) -> str:
        seconds = int(seconds)
        if seconds < 0:
            seconds = 0
        hrs, rem = divmod(seconds, 3600)
        mins, secs = divmod(rem, 60)
        if hrs > 0:
            return f"{hrs}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def _update_timer(self):
        if not self._translation_running or self._translation_start_time is None:
            return
        elapsed = time.time() - self._translation_start_time
        self.time_label.configure(text=f"⏱ {self._format_duration(elapsed)}")
        self._timer_job = self.after(1000, self._update_timer)

    def start_translation(self):
        input_text = self.input_text.get("0.0", "end").strip()
        pre_ctx = self.context_text.get("0.0", "end").strip()
        if not input_text:
            messagebox.showerror(self.tr("Error"), self.tr("Please input movie title(s)."))
            return
            
        provider_id = self.provider_var.get()
        model_name = self.model_var.get()
        auto_rotate = self.key_mode_var.get() == self.tr("Auto-Rotate")
        
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

        self.output_text.delete("0.0", "end")
        self.log_status(self.tr("Starting translation..."))
        self.translate_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        
        self._translation_start_time = time.time()
        self._translation_running = True
        self.time_label.configure(text="⏱ 00:00")
        self._update_timer()
        
        self.cancel_event = threading.Event()
        threading.Thread(target=self._run_translation_thread, args=(service, input_text, model_name, pre_ctx), daemon=True).start()

    def cancel_translation(self):
        if self.cancel_event:
            self.cancel_event.set()
            self.log_status(self.tr("Cancelling..."))
            self.cancel_btn.configure(state="disabled")

    def _run_translation_thread(self, service, input_text, model_name, pre_ctx):
        try:
            lines = [line for line in input_text.splitlines() if line.strip()]
            
            prompt = f"""You are an expert movie title translator.
Translate the following Chinese movie title(s) into Vietnamese.
Target language: Vietnamese.
Keep the translation natural, catchy, and culturally appropriate. Use Hán Việt where appropriate for historical/xianxia titles.

Context / Instructions:
{pre_ctx}

Input Titles:
{chr(10).join(lines)}

IMPORTANT: Output ONLY the translated titles, one per line, exactly matching the number of input lines. Do not add numbers, explanations, or quotes.
"""
            
            # Using log_status to update UI instead of writing to output
            def local_log(msg):
                self.log_status(msg)
                
            result = service.translate_with_retry(prompt, model_name, log_callback=local_log)
            
            if self.cancel_event and self.cancel_event.is_set():
                self.log_status(self.tr("Translation cancelled."))
            else:
                self.log_status(self.tr("Translation completed successfully!"))
                self.ui_queue.put(lambda f=result: self._set_final_output(f))
                
        except Exception as e:
            import logging
            logging.exception("Error during translation thread:")
            self.log_status(self.tr("Translation failed."))
            self.ui_queue.put(lambda err=e: self.output_text.insert("end", f"\n[ERROR] Translation failed: {err}"))
        finally:
            self._translation_running = False
            if self._timer_job:
                self.after_cancel(self._timer_job)
                self._timer_job = None
            if self._translation_start_time:
                total_elapsed = time.time() - self._translation_start_time
                self.ui_queue.put(lambda t=total_elapsed: self.time_label.configure(text=f"✅ Total: {self._format_duration(t)}"))
            self.ui_queue.put(lambda: self.translate_btn.configure(state="normal"))
            self.ui_queue.put(lambda: self.cancel_btn.configure(state="disabled"))

    def _set_final_output(self, final_text):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", final_text)
