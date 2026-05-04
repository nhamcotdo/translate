import threading
import queue
import functools
import customtkinter as ctk
from tkinter import messagebox
import json

from core.seo_description import SEODescriptionGenerator
from ui.translations import get_tr


class SEOTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, translate_tab=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.config_manager = config_manager
        self.translate_tab = translate_tab
        self.tr = get_tr(self.config_manager)
        self.generator = None
        
        self.ui_queue = queue.Queue()
        self._start_ui_queue_loop()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

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
        # --- Top Section: Settings and Inputs ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_columnconfigure(1, weight=1)

        # 1. Provider & Settings Card
        self.settings_card = ctk.CTkFrame(top_frame)
        self.settings_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.settings_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.settings_card, text=self.tr("⚙️ API Settings"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        # Provider
        ctk.CTkLabel(self.settings_card, text=self.tr("Provider:")).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.provider_var = ctk.StringVar(value=self.config_manager.get("default_provider", "openai"))
        self.provider_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.provider_var, command=self._on_provider_change)
        self.provider_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Model
        ctk.CTkLabel(self.settings_card, text=self.tr("Model:")).grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.model_var = ctk.StringVar(value=self.config_manager.get("default_model", "gpt-4o-mini"))
        self.model_dropdown = ctk.CTkOptionMenu(self.settings_card, variable=self.model_var)
        self.model_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.refresh_providers()

        # 2. SEO Config Card
        self.seo_card = ctk.CTkFrame(top_frame)
        self.seo_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.seo_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.seo_card, text=self.tr("📝 SEO Config"), font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        # Platform
        ctk.CTkLabel(self.seo_card, text=self.tr("Platform:")).grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.platform_var = ctk.StringVar(value="youtube")
        self.platform_dropdown = ctk.CTkOptionMenu(self.seo_card, variable=self.platform_var, values=["youtube", "facebook"])
        self.platform_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Target Lang
        ctk.CTkLabel(self.seo_card, text=self.tr("Output Lang:")).grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.lang_var = ctk.StringVar(value="Vietnamese")
        self.lang_entry = ctk.CTkEntry(self.seo_card, textvariable=self.lang_var)
        self.lang_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Video Title
        ctk.CTkLabel(self.seo_card, text=self.tr("Video Title:")).grid(row=3, column=0, padx=10, pady=5, sticky="e")
        self.title_var = ctk.StringVar()
        self.title_entry = ctk.CTkEntry(self.seo_card, textvariable=self.title_var, placeholder_text=self.tr("Optional"))
        self.title_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # --- Main Workspace (Inputs and Outputs) ---
        self.workspace = ctk.CTkTabview(self)
        self.workspace.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Tab 1: Input
        self.workspace.add(self.tr("Input Context"))
        self.workspace.tab(self.tr("Input Context")).grid_columnconfigure(0, weight=1)
        self.workspace.tab(self.tr("Input Context")).grid_rowconfigure(1, weight=1)
        self.workspace.tab(self.tr("Input Context")).grid_rowconfigure(3, weight=2)
        
        ctk.CTkLabel(self.workspace.tab(self.tr("Input Context")), text=self.tr("Extra Context / Instructions (Optional):"), anchor="w").grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        self.context_text = ctk.CTkTextbox(self.workspace.tab(self.tr("Input Context")), wrap="word", height=60)
        self.context_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        ctk.CTkLabel(self.workspace.tab(self.tr("Input Context")), text=self.tr("Subtitle / Transcript:"), anchor="w").grid(row=2, column=0, sticky="w", padx=5, pady=(10, 0))
        self.subtitle_text = ctk.CTkTextbox(self.workspace.tab(self.tr("Input Context")), wrap="word")
        self.subtitle_text.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        
        import_btn = ctk.CTkButton(self.workspace.tab(self.tr("Input Context")), text=self.tr("📥 Grab from Translate Tab"), command=self.import_from_translate, fg_color="#3B82F6", hover_color="#2563EB")
        import_btn.grid(row=4, column=0, sticky="e", padx=5, pady=5)
        
        # Tab 2: Output
        self.workspace.add(self.tr("Generated SEO"))
        self.workspace.tab(self.tr("Generated SEO")).grid_columnconfigure(0, weight=1)
        self.workspace.tab(self.tr("Generated SEO")).grid_rowconfigure(0, weight=1)
        
        self.output_text = ctk.CTkTextbox(self.workspace.tab(self.tr("Generated SEO")), wrap="word")
        self.output_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- Action Bar ---
        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.action_bar.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(self.action_bar, text=self.tr("🚀 Generate SEO"), font=ctk.CTkFont(weight="bold"), command=self.start_generation, cursor="hand2", height=40)
        self.start_btn.grid(row=0, column=0, sticky="w")
        
        self.progress_frame = ctk.CTkFrame(self.action_bar, fg_color="transparent")
        self.progress_frame.grid(row=0, column=1, sticky="ew", padx=20)
        self.progress_frame.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(self.progress_frame, text=self.tr("Ready"), text_color="gray", font=ctk.CTkFont(size=12))
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        
        self.progress = ctk.CTkProgressBar(self.progress_frame, height=8)
        self.progress.grid(row=1, column=0, sticky="ew")
        self.progress.set(0)

    def import_from_translate(self):
        if self.translate_tab:
            content = self.translate_tab.output_text.get("0.0", "end").strip()
            if not content:
                content = self.translate_tab.input_text.get("0.0", "end").strip()
                
            if content:
                self.subtitle_text.delete("0.0", "end")
                self.subtitle_text.insert("0.0", content)
            else:
                messagebox.showinfo(self.tr("Info"), self.tr("No content found in Translate tab."))

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

        return TranslatorService(provider_inst, keys, auto_rotate=True)

    def start_generation(self):
        subtitle_text = self.subtitle_text.get("0.0", "end").strip()
        extra_context = self.context_text.get("0.0", "end").strip()
        video_title = self.title_var.get().strip()
        
        if not subtitle_text and not extra_context and not video_title:
            messagebox.showerror(self.tr("Error"), self.tr("Please provide at least a subtitle, video title, or extra context."))
            return

        model_name = self.model_var.get()
        if model_name in [self.tr("Loading..."), self.tr("Error"), self.tr("No models found")]:
            messagebox.showerror(self.tr("Error"), self.tr("Please wait for AI models to load or check your API keys."))
            return

        self.start_btn.configure(state="disabled")
        self.update_progress(0.1, self.tr("Initializing generator..."))
        self.output_text.delete("0.0", "end")

        platform = self.platform_var.get()
        target_lang = self.lang_var.get().strip()

        threading.Thread(
            target=self._generation_worker,
            args=(subtitle_text, platform, target_lang, video_title, extra_context, model_name),
            daemon=True
        ).start()

    def _generation_worker(self, subtitle_text, platform, target_lang, video_title, extra_context, model_name):
        try:
            translator_service = self._get_translator_service()
            self.generator = SEODescriptionGenerator(translator_service)
            
            def log_cb(msg):
                self.log_status(msg)
                
            self.update_progress(0.4, self.tr("Generating SEO package..."))
            
            result = self.generator.generate(
                subtitle_text=subtitle_text,
                platform=platform,
                target_lang=target_lang,
                video_title=video_title,
                extra_context=extra_context,
                model_name=model_name,
                log_callback=log_cb
            )
            
            # Format output beautifully
            formatted_output = f"=== {platform.upper()} SEO PACKAGE ===\n\n"
            formatted_output += f"TITLE:\n{result.get('title', '')}\n\n"
            formatted_output += f"DESCRIPTION:\n{result.get('description', '')}\n\n"
            
            tags = result.get('tags', [])
            if tags:
                formatted_output += f"TAGS:\n{', '.join(tags)}\n\n"
                
            hashtags = result.get('hashtags', [])
            if hashtags:
                formatted_output += f"HASHTAGS:\n{' '.join(hashtags)}\n\n"
                
            cta = result.get('call_to_action', '')
            if cta:
                formatted_output += f"CALL TO ACTION:\n{cta}\n\n"
                
            formatted_output += "--- RAW JSON ---\n"
            # Strip out raw response for clean json display
            clean_res = {k:v for k,v in result.items() if k != "raw_response"}
            formatted_output += json.dumps(clean_res, indent=2, ensure_ascii=False)

            self.ui_queue.put(functools.partial(self._finish_generation, formatted_output))
            
        except Exception as e:
            err_msg = str(e)
            self.ui_queue.put(lambda msg=err_msg: self._show_error(msg))
            
    def _finish_generation(self, output_text):
        self.update_progress(1.0, self.tr("Completed successfully!"))
        self.workspace.set(self.tr("Generated SEO"))
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", output_text)
        self.start_btn.configure(state="normal")

    def _show_error(self, err):
        self.log_status(self.tr("Error!"))
        self.start_btn.configure(state="normal")
        messagebox.showerror(self.tr("Error"), str(err))
