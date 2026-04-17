import time
import requests
from typing import List, Dict, Tuple, Any
from abc import ABC, abstractmethod

from openai import OpenAI, RateLimitError as OpenAIRateLimitError
import httpx
import certifi
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

class BaseProvider(ABC):
    @abstractmethod
    def translate(self, prompt: str, model_name: str, api_key: str) -> str:
        """Translates the prompt and returns the output string."""
        pass
        
    @abstractmethod
    def is_rate_limit_error(self, e: Exception) -> bool:
        """Returns True if the exception is a rate limit error."""
        pass
        
    @abstractmethod
    def get_available_models(self, api_key: str) -> List[str]:
        """Fetches a list of available model names."""
        pass

class OpenAIProvider(BaseProvider):
    def translate(self, prompt: str, model_name: str, api_key: str) -> str:
        client_key = api_key if api_key.strip() else "dummy-key"
        client = OpenAI(
            api_key=client_key,
            http_client=httpx.Client(verify=certifi.where())
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def is_rate_limit_error(self, e: Exception) -> bool:
        return isinstance(e, OpenAIRateLimitError)

    def get_available_models(self, api_key: str) -> List[str]:
        client_key = api_key if api_key.strip() else "dummy-key"
        client = OpenAI(api_key=client_key, http_client=httpx.Client(verify=certifi.where()))
        try:
            models = client.models.list()
            # Sort models by creation time or alphabetically
            m_list = [m.id for m in models.data]
            m_list.sort()
            # Optionally filter out some whisper/dall-e but for now return all
            return [m for m in m_list if "gpt" in m or "o1" in m]
        except Exception:
            return ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

class GeminiProvider(BaseProvider):
    def translate(self, prompt: str, model_name: str, api_key: str) -> str:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()

    def is_rate_limit_error(self, e: Exception) -> bool:
        return isinstance(e, ResourceExhausted) or "429" in str(e)

    def get_available_models(self, api_key: str) -> List[str]:
        genai.configure(api_key=api_key)
        try:
            models = genai.list_models()
            m_list = [m.name for m in models if "generateContent" in m.supported_generation_methods]
            # remove 'models/' prefix
            m_list = [m.replace("models/", "") for m in m_list]
            return m_list
        except Exception:
            return ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]

class CustomOpenAIProvider(BaseProvider):
    def __init__(self, base_url: str, custom_headers: Dict[str, str] = None):
        self.base_url = base_url
        self.custom_headers = custom_headers or {}

    def translate(self, prompt: str, model_name: str, api_key: str) -> str:
        # If API key is empty strings, we might pass a dummy key because OpenAI lib requires one
        client_key = api_key if api_key.strip() else "dummy-key"
        
        # Build transport with custom headers
        transport = httpx.HTTPTransport()
        client = OpenAI(
            api_key=client_key,
            base_url=self.base_url,
            http_client=httpx.Client(transport=transport, headers=self.custom_headers, verify=certifi.where())
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()

    def is_rate_limit_error(self, e: Exception) -> bool:
        return isinstance(e, OpenAIRateLimitError)

    def get_available_models(self, api_key: str) -> List[str]:
        client_key = api_key if api_key.strip() else "dummy-key"
        transport = httpx.HTTPTransport()
        client = OpenAI(
            api_key=client_key,
            base_url=self.base_url,
            http_client=httpx.Client(transport=transport, headers=self.custom_headers, verify=certifi.where())
        )
        try:
            models = client.models.list()
            return [m.id for m in models.data]
        except Exception:
            return []

class NvidiaProvider(BaseProvider):
    def translate(self, prompt: str, model_name: str, api_key: str) -> str:
        client_key = api_key if api_key.strip() else "dummy-key"
        client = OpenAI(
            api_key=client_key,
            base_url="https://integrate.api.nvidia.com/v1",
            http_client=httpx.Client(verify=certifi.where())
        )
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.95
        )
        return response.choices[0].message.content.strip()

    def is_rate_limit_error(self, e: Exception) -> bool:
        return isinstance(e, OpenAIRateLimitError)

    def get_available_models(self, api_key: str) -> List[str]:
        client_key = api_key if api_key.strip() else "dummy-key"
        client = OpenAI(
            api_key=client_key,
            base_url="https://integrate.api.nvidia.com/v1",
            http_client=httpx.Client(verify=certifi.where())
        )
        try:
            models = client.models.list()
            m_list = [m.id for m in models.data]
            m_list.sort()
            return m_list
        except Exception:
            return ["meta/llama-3.1-405b-instruct", "google/gemma-4-31b-it", "google/gemma-2-27b-it"]

class TranslatorService:
    def __init__(self, provider: BaseProvider, keys: List[str], auto_rotate: bool = True):
        self.provider = provider
        self.keys = keys
        self.auto_rotate = auto_rotate
        self.current_key_idx = 0

    def get_current_key(self) -> str:
        if not self.keys:
            return ""
        return self.keys[self.current_key_idx % len(self.keys)]

    def next_key(self):
        self.current_key_idx += 1

    def translate_with_retry(self, prompt: str, model_name: str, log_callback=None) -> str:
        if not self.keys:
            # Maybe the provider doesn't need a key (like some custom ones)
            # Try once with empty key
            try:
                return self.provider.translate(prompt, model_name, "")
            except Exception as e:
                raise Exception(f"Translation failed: {e}")

        attempts = 0
        max_attempts = len(self.keys) if self.auto_rotate else 1
        
        while attempts < max_attempts:
            key = self.get_current_key()
            try:
                return self.provider.translate(prompt, model_name, key)
            except Exception as e:
                is_rl = self.provider.is_rate_limit_error(e)
                if is_rl and self.auto_rotate:
                    if log_callback:
                        log_callback(f"Rate limit hit for key index {self.current_key_idx % len(self.keys)}. Rotating...")
                    self.next_key()
                    attempts += 1
                    time.sleep(1) # Slight pause to avoid spam
                else:
                    raise e
                    
        raise Exception(f"All {max_attempts} keys exhausted or rate limited.")
