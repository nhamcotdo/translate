import os
import threading
import queue
import functools
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.stt_service import STTService
from core.video_summarizer import VideoSummarizer
from ui.translations import get_tr

class SummaryTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, translate_tab=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.translate_tab = translate_tab
        self.tr = get_tr(self.config_manager)
        self.stt_service = None
        self.summarizer = None
        
        self.ui_queue = queue.Queue()
        self._start_ui_queue_loop()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.selected_file = None
        self.cancel_event = None
        
        # Pipeline state
        self.extracted_subtitles = ""
        self.ai_highlights = []
        self.final_narrations = []

        self._build_ui()

    def _start_ui_queue_loop(self):
        try:
            while True:
                task = self.ui_queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.after(50, self._start_ui_queue_loop)

    def _build_ui(self):
        # --- Top Section: Settings and File ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)

        # 1. Settings Card
        self.settings_card = ctk.CTkFrame(top_frame)
        self.settings_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.settings_card.grid_columnconfigure(3, weight=1)
        
        ctk.CTkLabel(self.settings_card, text=self.tr("⚙️ Summary Settings"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5))

        # Whisper Model
        ctk.CTkLabel(self.settings_card, text=self.tr("Whisper:")).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.whisper_var = ctk.StringVar(value="base")
        ctk.CTkOptionMenu(self.settings_card, variable=self.whisper_var, values=["tiny", "base", "small", "medium", "large"], width=90).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Highlights Count
        ctk.CTkLabel(self.settings_card, text=self.tr("Highlights:")).grid(row=1, column=2, padx=10, pady=5, sticky="e")
        self.highlights_var = ctk.StringVar(value="5")
        ctk.CTkEntry(self.settings_card, textvariable=self.highlights_var, width=50).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # Narration Lang
        ctk.CTkLabel(self.settings_card, text=self.tr("Narration Lang:")).grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.lang_var = ctk.StringVar(value="Vietnamese")
        ctk.CTkEntry(self.settings_card, textvariable=self.lang_var, width=120).grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="w")

        # 2. File Card
        self.file_card = ctk.CTkFrame(top_frame)
        self.file_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.file_card.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.file_card, text=self.tr("🎬 Input Video"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))
        
        self.load_btn = ctk.CTkButton(self.file_card, text=self.tr("Select Video"), command=self.select_file, height=32)
        self.load_btn.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        
        self.file_label = ctk.CTkLabel(self.file_card, text=self.tr("No file selected..."), text_color="gray", wraplength=400)
        self.file_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        # --- Middle Section: Provider and Status ---
        mid_frame = ctk.CTkFrame(self, fg_color="transparent")
        mid_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        mid_frame.grid_columnconfigure(0, weight=1)

        # Provider Card based on translation tab
        self.provider_card = ctk.CTkFrame(mid_frame)
        self.provider_card.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.provider_card.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(self.provider_card, text=self.tr("🤖 AI Provider:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(15, 5), pady=15, sticky="w")
        
        self.provider_var = ctk.StringVar(value=self.config_manager.get("default_provider", "openai"))
        self.provider_dropdown = ctk.CTkOptionMenu(self.provider_card, variable=self.provider_var, command=self._on_provider_change, width=120)
        self.provider_dropdown.grid(row=0, column=1, padx=5, pady=15, sticky="w")

        ctk.CTkLabel(self.provider_card, text=self.tr("Model:"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=2, padx=(15, 5), pady=15, sticky="w")
        self.model_var = ctk.StringVar(value=self.config_manager.get("default_model", "gpt-4o-mini"))
        self.model_dropdown = ctk.CTkOptionMenu(self.provider_card, variable=self.model_var, width=150)
        self.model_dropdown.grid(row=0, column=3, padx=5, pady=15, sticky="w")
        
        self.refresh_providers()

        # --- Main Workspace (Highlights review and SRT) ---
        self.workspace = ctk.CTkTabview(self)
        self.workspace.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Tab 1: Highlights Review
        self.workspace.add(self.tr("Highlights Selected by AI"))
        self.workspace.tab(self.tr("Highlights Selected by AI")).grid_columnconfigure(0, weight=1)
        self.workspace.tab(self.tr("Highlights Selected by AI")).grid_rowconfigure(0, weight=1)
        
        self.scrollable_highlights = ctk.CTkScrollableFrame(self.workspace.tab(self.tr("Highlights Selected by AI")))
        self.scrollable_highlights.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.highlight_widgets = [] # Tuples of (checkbox_var, widget_frame, highlight_data)
        
        # Tab 2: Output
        self.workspace.add(self.tr("SRT Output"))
        self.workspace.tab(self.tr("SRT Output")).grid_columnconfigure(0, weight=1)
        self.workspace.tab(self.tr("SRT Output")).grid_rowconfigure(0, weight=1)
        
        self.output_text = ctk.CTkTextbox(self.workspace.tab(self.tr("SRT Output")), wrap="word")
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- Action Bar ---
        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        self.action_bar.grid_columnconfigure(2, weight=1)

        self.start_btn = ctk.CTkButton(self.action_bar, text=self.tr("▶ Start Auto Summary"), font=ctk.CTkFont(weight="bold"), command=self.start_pipeline, cursor="hand2", height=40)
        self.start_btn.grid(row=0, column=0, sticky="w")
        
        self.continue_btn = ctk.CTkButton(self.action_bar, text=self.tr("▶ Continue Process"), font=ctk.CTkFont(weight="bold"), command=self.continue_pipeline, cursor="hand2", height=40, fg_color="#F59E0B", hover_color="#D97706", state="disabled")
        self.continue_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self.progress_frame = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        self.progress_frame.grid(row=0, column=2, sticky="ew", padx=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(self.progress_frame, text=self.tr("Ready"), text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        self.progress = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)

        # Output dir selection
        self.save_btn = ctk.CTkButton(self.action_bar, text=self.tr("💾 Setup Output & Run"), command=self.select_output_and_continue, cursor="hand2", fg_color="#10B981", hover_color="#059669", height=40, state="disabled")
        self.save_btn.grid(row=0, column=3, sticky="e", padx=(0, 10))

    def refresh_providers(self):
        providers = ["openai", "gemini", "nvidia"]
        custom = self.config_manager.get_custom_providers()
        providers.extend(list(custom.keys()))
        
        self.provider_dropdown.configure(values=providers)
        if self.provider_var.get() not in providers:
            self.provider_var.set("openai")
            
        self._on_provider_change(self.provider_var.get())

    def _on_provider_change(self, selected_provider: str):
        self.ui_queue.put(lambda: self.model_dropdown.configure(state="disabled", values=[self.tr("Loading...")]))
        self.model_var.set(self.tr("Loading..."))
        
        def fetch():
            try:
                from core.translator import OpenAIProvider, GeminiProvider, CustomOpenAIProvider, NvidiaProvider
                keys = self.config_manager.get_keys(selected_provider)
                api_key = keys[0] if keys else ""
                
                if selected_provider == "openai":
                    provider_inst = OpenAIProvider()
                    models = provider_inst.get_available_models(api_key)
                elif selected_provider == "gemini":
                    provider_inst = GeminiProvider()
                    models = provider_inst.get_available_models(api_key)
                elif selected_provider == "nvidia":
                    provider_inst = NvidiaProvider()
                    models = provider_inst.get_available_models(api_key)
                else:
                    cust = self.config_manager.get_custom_providers().get(selected_provider, {})
                    provider_inst = CustomOpenAIProvider(base_url=cust.get("base_url", ""), custom_headers=cust.get("headers", {}))
                    models = provider_inst.get_available_models(api_key)
                    if not models:
                        models = cust.get("models", [])
                
                def update():
                    self.model_dropdown.configure(state="normal", values=models if models else [self.tr("No models found")])
                    default_model = self.config_manager.get("default_model", "")
                    if models:
                        if default_model in models:
                            self.model_var.set(default_model)
                        elif selected_provider == "gemini" and "gemini-1.5-flash" in models:
                            self.model_var.set("gemini-1.5-flash")
                        elif "gpt-4o-mini" in models:
                            self.model_var.set("gpt-4o-mini")
                        else:
                            self.model_var.set(models[0])
                    else:
                        self.model_var.set(self.tr("No models found"))
                self.ui_queue.put(update)
            except Exception as e:
                self.ui_queue.put(lambda: self.model_dropdown.configure(state="normal", values=[self.tr("Error")]))
                self.ui_queue.put(lambda: self.model_var.set(self.tr("Error")))
                
        threading.Thread(target=fetch, daemon=True).start()

    def select_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[
                ("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm"),
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

    def _get_translator_service(self):
        from core.translator import TranslatorService, OpenAIProvider, GeminiProvider, CustomOpenAIProvider, NvidiaProvider
        
        provider_id = self.provider_var.get()
        keys = self.config_manager.get_keys(provider_id)
        if not keys and provider_id in ["openai", "gemini", "nvidia"]:
            raise ValueError(f"No API keys configured for {provider_id}.")
            
        if provider_id == "openai":
            provider_inst = OpenAIProvider()
        elif provider_id == "gemini":
            provider_inst = GeminiProvider()
        elif provider_id == "nvidia":
            provider_inst = NvidiaProvider()
        else:
            cust = self.config_manager.get_custom_providers().get(provider_id)
            if not cust:
                raise ValueError("Custom provider not found.")
            provider_inst = CustomOpenAIProvider(base_url=cust.get("base_url"), custom_headers=cust.get("headers", {}))

        # Auto-rotate keys
        return TranslatorService(provider_inst, keys, auto_rotate=True)

    # ----------- PIPELINE STAGE 1: Extract & Analyze -----------

    def start_pipeline(self):
        if not self.selected_file:
            messagebox.showerror(self.tr("Error"), self.tr("Please select a video/audio file first."))
            return
            
        try:
            num_highlights = int(self.highlights_var.get())
        except ValueError:
            messagebox.showerror(self.tr("Error"), self.tr("Invalid number of highlights."))
            return

        model_name = self.model_var.get()
        if model_name in [self.tr("Loading..."), self.tr("Error"), self.tr("No models found")]:
            messagebox.showerror(self.tr("Error"), self.tr("Please wait for AI models to load or check your API keys."))
            return

        self.start_btn.configure(state="disabled")
        self.continue_btn.configure(state="disabled")
        self.save_btn.configure(state="disabled")
        
        # Clear previous highlights
        for _, w_frame, _ in self.highlight_widgets:
            w_frame.destroy()
        self.highlight_widgets.clear()
        self.output_text.delete("0.0", "end")
        
        whisper_size = self.whisper_var.get()

        threading.Thread(
            target=self._phase_1_worker,
            args=(self.selected_file, whisper_size, model_name, num_highlights),
            daemon=True
        ).start()

    def _phase_1_worker(self, file_path, whisper_size, model_name, num_highlights):
        try:
            # 1. Whisper Extraction
            if self.stt_service is None or self.stt_service.model_size != whisper_size:
                self.stt_service = STTService(model_size=whisper_size)
                
            segments, _ = self.stt_service.transcribe(
                file_path=file_path,
                progress_callback=lambda p, m: self.update_progress(p * 0.4, f"[Extract] {m}") # 0-40%
            )
            
            self.extracted_subtitles = STTService.segments_to_srt(segments)
            
            # 2. AI Selection
            translator_service = self._get_translator_service()
            self.summarizer = VideoSummarizer(translator_service)
            
            self.update_progress(0.4, self.tr("Analyzing subtitles with AI to find highlights..."))
            def log_cb(msg):
                self.log_status(f"[AI Analysis] {msg}")
                
            self.ai_highlights = self.summarizer.analyze_subtitles(
                self.extracted_subtitles,
                model_name,
                num_highlights,
                log_callback=log_cb
            )
            
            self.update_progress(0.6, self.tr("AI selected highlights. Please review and continue."))
            
            # Show in UI and pause
            self.ui_queue.put(self._populate_highlights_ui)
            
        except Exception as e:
            err_msg = str(e)
            self.ui_queue.put(lambda msg=err_msg: self._show_error(msg))

    def _populate_highlights_ui(self):
        self.workspace.set(self.tr("Highlights Selected by AI"))
        
        for i, hl in enumerate(self.ai_highlights):
            frame = ctk.CTkFrame(self.scrollable_highlights)
            frame.pack(fill="x", padx=5, pady=5)
            
            chk_var = ctk.BooleanVar(value=True)
            chk = ctk.CTkCheckBox(frame, text=self.tr("Highlight #{i} : {start} -> {end}", i=i+1, start=hl.get('start'), end=hl.get('end')), variable=chk_var, font=ctk.CTkFont(weight="bold"))
            chk.pack(anchor="w", padx=10, pady=(10, 5))
            
            lbl = ctk.CTkLabel(frame, text=self.tr("Reason: {reason}", reason=hl.get('reason', '')), text_color="gray", justify="left")
            lbl.pack(anchor="w", padx=35, pady=0)
            
            transcript_lbl = ctk.CTkTextbox(frame, height=60, fg_color="transparent")
            transcript_lbl.insert("0.0", hl.get('transcript', ''))
            transcript_lbl.configure(state="disabled")
            transcript_lbl.pack(fill="x", padx=35, pady=(5, 10))
            
            self.highlight_widgets.append((chk_var, frame, hl))
            
        self.continue_btn.configure(state="normal")
        self.start_btn.configure(state="normal")

    # ----------- PIPELINE STAGE 2: Cut & Narrate -----------

    def continue_pipeline(self):
        selected = []
        for chk_var, _, hl in self.highlight_widgets:
            if chk_var.get():
                selected.append(hl)
                
        if not selected:
            messagebox.showerror(self.tr("Error"), self.tr("No highlights selected. Please select at least one."))
            return
            
        self.ai_highlights = selected
        
        self.continue_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.save_btn.configure(state="normal") # User must set output path now
        self.select_output_and_continue()

    def select_output_and_continue(self):
        output_video_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4")],
            title="Save Output Video As"
        )
        if not output_video_path:
            # User cancelled, re-enable continue button
            self.continue_btn.configure(state="normal")
            return
            
        self.save_btn.configure(state="disabled")
        output_srt_path = output_video_path.rsplit('.', 1)[0] + ".srt"
        
        model_name = self.model_var.get()
        target_lang = self.lang_var.get().strip()
        
        threading.Thread(
            target=self._phase_2_worker,
            args=(self.selected_file, output_video_path, output_srt_path, model_name, target_lang),
            daemon=True
        ).start()

    def _phase_2_worker(self, input_video, output_video, output_srt, model_name, target_lang):
        try:
            def log_cb(msg):
                self.log_status(msg)
                
            def prog_cb(current, total):
                # FFmpeg is 60->85%
                fraction = current / max(1, total)
                self.update_progress(0.6 + fraction * 0.25)

            # 1. FFmpeg Cutting
            success = self.summarizer.cut_and_merge_video(
                input_video, 
                self.ai_highlights, 
                output_video,
                log_callback=log_cb,
                progress_callback=prog_cb
            )
            
            if not success:
                raise Exception("FFmpeg processing failed")
                
            # 2. Narration Generation
            self.update_progress(0.85, self.tr("Generating narrations via AI..."))
            self.final_narrations = self.summarizer.generate_narration(
                self.ai_highlights,
                model_name,
                target_lang,
                log_callback=log_cb
            )
            
            # 3. Create SRT
            self.update_progress(0.95, self.tr("Generating final SRT file..."))
            self.summarizer.generate_srt(self.final_narrations, output_srt)
            
            # Read SRT for preview
            with open(output_srt, "r", encoding="utf-8") as f:
                srt_content = f.read()
                
            self.ui_queue.put(functools.partial(self._finish_pipeline, srt_content, output_video, output_srt))
            
        except Exception as e:
            err_msg = str(e)
            self.ui_queue.put(lambda msg=err_msg: self._show_error(msg))

    def _finish_pipeline(self, srt_content, output_video, output_srt):
        self.update_progress(1.0, self.tr("Completed successfully!"))
        self.workspace.set(self.tr("SRT Output"))
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", srt_content)
        self.start_btn.configure(state="normal")
        messagebox.showinfo(self.tr("Success"), self.tr("Video Summary Processed!\n\nVideo: {output_video}\nSRT: {output_srt}", output_video=output_video, output_srt=output_srt))

    def _show_error(self, err):
        self.log_status(self.tr("Error!"))
        self.start_btn.configure(state="normal")
        self.continue_btn.configure(state="normal")
        messagebox.showerror(self.tr("Error"), str(err))

