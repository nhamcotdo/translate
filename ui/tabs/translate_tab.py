import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox

from core.engine import TranslationEngine
from core.translator import TranslatorService, OpenAIProvider, GeminiProvider, CustomOpenAIProvider

class TranslateTab(ctk.CTkFrame):
    def __init__(self, master, config_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.config_manager = config_manager
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1) # Input text
        self.grid_rowconfigure(6, weight=1) # Logs
        
        # Row 0: Provider & Model & Key selection
        self.opt_frame = ctk.CTkFrame(self)
        self.opt_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(self.opt_frame, text="Provider:").pack(side="left", padx=5)
        self.provider_var = ctk.StringVar(value="openai")
        self.provider_dropdown = ctk.CTkOptionMenu(self.opt_frame, variable=self.provider_var, command=self.on_provider_change)
        self.provider_dropdown.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.opt_frame, text="Model:").pack(side="left", padx=5)
        self.model_var = ctk.StringVar(value="gpt-4o-mini")
        self.model_dropdown = ctk.CTkOptionMenu(self.opt_frame, variable=self.model_var)
        self.model_dropdown.pack(side="left", padx=5)
        
        ctk.CTkLabel(self.opt_frame, text="Key Mode:").pack(side="left", padx=5)
        self.key_mode_var = ctk.StringVar(value="Auto-Rotate")
        self.key_mode_dropdown = ctk.CTkOptionMenu(self.opt_frame, variable=self.key_mode_var, values=["Auto-Rotate", "Specific Key"])
        self.key_mode_dropdown.pack(side="left", padx=5)

        # Target language
        ctk.CTkLabel(self.opt_frame, text="Lang:").pack(side="left", padx=5)
        self.lang_var = ctk.StringVar(value="Vietnamese")
        self.lang_entry = ctk.CTkEntry(self.opt_frame, variable=self.lang_var, width=100)
        self.lang_entry.pack(side="left", padx=5)
        
        # Row 1: Load file
        self.file_frame = ctk.CTkFrame(self)
        self.file_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.load_btn = ctk.CTkButton(self.file_frame, text="Load VTT File", command=self.load_file)
        self.load_btn.pack(side="left", padx=5)
        self.file_label = ctk.CTkLabel(self.file_frame, text="No file selected.")
        self.file_label.pack(side="left", padx=5)
        
        # Row 2: Text input
        ctk.CTkLabel(self, text="Input Subtitles (VTT or raw text):").grid(row=2, column=0, padx=10, sticky="sw")
        self.input_text = ctk.CTkTextbox(self, height=150)
        self.input_text.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Row 4: Pre-context
        ctk.CTkLabel(self, text="Pre-Context / Background details:").grid(row=4, column=0, padx=10, sticky="sw")
        self.context_text = ctk.CTkTextbox(self, height=60)
        self.context_text.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        # Row 6: Actions
        self.action_frame = ctk.CTkFrame(self)
        self.action_frame.grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        self.translate_btn = ctk.CTkButton(self.action_frame, text="Translate", command=self.start_translation)
        self.translate_btn.pack(side="left", padx=5)
        
        self.progress = ctk.CTkProgressBar(self.action_frame, width=300)
        self.progress.pack(side="left", padx=10, fill="x", expand=True)
        self.progress.set(0)
        
        # Row 7: Output & Logs
        ctk.CTkLabel(self, text="Output / Logs:").grid(row=7, column=0, padx=10, sticky="sw")
        self.output_text = ctk.CTkTextbox(self, height=200)
        self.output_text.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)
        
        self.save_btn = ctk.CTkButton(self, text="Save Translated File", command=self.save_file)
        self.save_btn.grid(row=9, column=1, sticky="e", padx=10, pady=10)
        
        self.refresh_providers()

    def refresh_providers(self):
        providers = ["openai", "gemini"]
        customs = self.config_manager.get_custom_providers()
        providers.extend(list(customs.keys()))
        
        self.provider_dropdown.configure(values=providers)
        
        curr = self.provider_var.get()
        if curr not in providers:
            self.provider_var.set("openai")
            self.on_provider_change("openai")
        else:
            self.on_provider_change(curr)

    def on_provider_change(self, value):
        # Update models based on provider
        if value == "openai":
            models = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        elif value == "gemini":
            models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        else:
            cust = self.config_manager.get_custom_providers().get(value, {})
            models = cust.get("models", ["default-model"])
            if not models:
                models = ["default-model"]
                
        self.model_dropdown.configure(values=models)
        self.model_var.set(models[0])

    def load_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.vtt *.srt"), ("All Files", "*.*")])
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.input_text.delete("0.0", "end")
            self.input_text.insert("0.0", content)
            self.file_label.configure(text=filename)

    def save_file(self):
        filename = filedialog.asksaveasfilename(defaultextension=".vtt", filetypes=[("VTT files", "*.vtt")])
        if filename:
            content = self.output_text.get("0.0", "end")
            # Usually output text will have the logs at the beginning. 
            # We should probably store the final VTT in a variable, but for simplicity we write the whole output block (assuming we replace logs with final result)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content.strip())
            messagebox.showinfo("Saved", "File saved successfully.")

    def log(self, msg: str):
        # Thread safe append
        self.output_text.after(0, self._append_log, msg)

    def _append_log(self, msg: str):
        self.output_text.insert("end", msg + "\n")
        self.output_text.see("end")

    def update_progress(self, current: int, total: int):
        val = current / total if total > 0 else 0
        self.progress.after(0, self.progress.set, val)

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
        
        # Get keys for provider
        keys = self.config_manager.get_keys(provider_id)
        if not keys and provider_id in ["openai", "gemini"]:
            messagebox.showerror("Error", f"No API keys configured for {provider_id}.")
            return
            
        # Instantiate provider
        if provider_id == "openai":
            provider_inst = OpenAIProvider()
        elif provider_id == "gemini":
            provider_inst = GeminiProvider()
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
        self.translate_btn.configure(state="disabled")
        
        # Run in thread
        threading.Thread(target=self._run_translation_thread, args=(engine, vtt_input, target_lang, model_name, pre_ctx), daemon=True).start()

    def _run_translation_thread(self, engine, vtt_input, target_lang, model_name, pre_ctx):
        try:
            final_vtt = engine.run_vtt(
                vtt_text=vtt_input,
                target_lang=target_lang,
                model_name=model_name,
                pre_context=pre_ctx,
                progress_callback=self.update_progress,
                log_callback=self.log
            )
            # Replace logs with final result, or just append it and say "Done"
            self.log("\n--- FINAL TRANSLATED VTT ---\n" + final_vtt)
            self.output_text.after(0, self._set_final_output, final_vtt)
        except Exception as e:
            self.log(f"\n[ERROR] Translation failed: {e}")
        finally:
            self.translate_btn.after(0, lambda: self.translate_btn.configure(state="normal"))

    def _set_final_output(self, final_vtt):
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", final_vtt)
