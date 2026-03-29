# Handles LLM interactions
import os
import time
import requests
from groq import Groq
from dotenv import load_dotenv
from core.personas import Personas

# Load .env from backend/ or project root
_backend_dir = os.path.dirname(os.path.dirname(__file__))
_project_root = os.path.dirname(_backend_dir)
load_dotenv(os.path.join(_backend_dir, ".env"))   # backend/.env
load_dotenv(os.path.join(_project_root, ".env"))   # project root/.env

class LLMHandler:
    def __init__(self):
        # Load all available API keys
        self.api_keys = []
        primary = os.getenv("GROQ_API_KEY")
        if primary:
            self.api_keys.append(primary)
        
        # Load sub keys: GROQ_API_KEY_2, GROQ_API_KEY_3, ...
        for i in range(2, 10):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.api_keys.append(key)
        
        if not self.api_keys:
            print("[LLM] WARNING: No GROQ_API_KEY found in environment!")
            self.api_keys = [""]  # Will fail gracefully
        
        self.current_key_idx = 0
        self.client = Groq(api_key=self.api_keys[0])
        print(f"[LLM] Loaded {len(self.api_keys)} API key(s)")

    def _rotate_key(self):
        """Switch to the next available API key."""
        if len(self.api_keys) <= 1:
            return False
        self.current_key_idx = (self.current_key_idx + 1) % len(self.api_keys)
        self.client = Groq(api_key=self.api_keys[self.current_key_idx])
        print(f"[LLM] Rotated to API key #{self.current_key_idx + 1}")
        return True

    def get_response(self, prompt, model="llama-3.3-70b-versatile", system_prompt=None, chat_history=None, mode="Fast Mode"):
        """
        Generates response from LLM with automatic key rotation and retry.
        """
        messages = []
        
        # 1. Determine System Prompt
        if system_prompt:
            final_system_prompt = system_prompt
        else:
            final_system_prompt = Personas.get_prompt(mode)
            
        messages.append({"role": "system", "content": final_system_prompt})
            
        # 2. Append History
        if chat_history:
            for msg in chat_history:
                if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                    messages.append({"role": msg["role"], "content": msg["content"]})
            
        # 3. Append User Query
        messages.append({"role": "user", "content": prompt})
        
        # Try each key, with retries
        total_keys = len(self.api_keys)
        keys_tried = 0
        
        while keys_tried < total_keys:
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=4096,
                )
                return chat_completion.choices[0].message.content
            except Exception as e:
                err_str = str(e).lower()
                is_rate_limit = "rate_limit" in err_str or "429" in err_str or "too many" in err_str
                
                if is_rate_limit:
                    # Try rotating to next key
                    rotated = self._rotate_key()
                    if rotated:
                        keys_tried += 1
                        print(f"[LLM] Key rate-limited, trying next key ({keys_tried}/{total_keys})...")
                        continue
                    else:
                        # Only one key, wait and retry once
                        print(f"[LLM] Rate limited, waiting 5s before retry...")
                        time.sleep(5)
                        try:
                            chat_completion = self.client.chat.completions.create(
                                messages=messages,
                                model=model,
                                temperature=0.7,
                                max_tokens=4096,
                            )
                            return chat_completion.choices[0].message.content
                        except Exception as e2:
                            print(f"Groq API Error (after retry): {str(e2)}")
                            return f"Error calling Groq API: {str(e2)}"
                
                print(f"Groq API Error: {str(e)}")
                return f"Error calling Groq API: {str(e)}"
        
        # If we reach here, all Groq keys are rate-limited.
        # Fallback to OpenRouter if configured
        print("[LLM] All Groq API keys rate-limited. Attempting OpenRouter fallback...")
        return self._try_openrouter_fallback(messages)

    def _try_openrouter_fallback(self, messages):
        """Fallback to OpenRouter when Groq is rate limited."""
        # Use the model the user requested
        model = "nvidia/nemotron-3-super-120b-a12b:free"
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        if not openrouter_key:
            return "Error calling Groq API: All API keys are rate-limited. Please wait a minute. (No OPENROUTER_API_KEY found for fallback)."
            
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.7
                },
                timeout=30 # Prevent hanging
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"[LLM] OpenRouter fallback failed: {response.text}")
                return f"Error calling Groq API: All API keys rate-limited. OpenRouter fallback also failed ({response.status_code})."
        except Exception as e:
            print(f"[LLM] OpenRouter fallback exception: {str(e)}")
            return f"Error calling Groq API: All API keys rate-limited. OpenRouter fallback failed: {str(e)}"

