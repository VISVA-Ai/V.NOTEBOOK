# Handles LLM interactions
import os
import time
from dotenv import load_dotenv
import litellm
from core.personas import Personas

# Load .env from backend/ or project root
_backend_dir = os.path.dirname(os.path.dirname(__file__))
_project_root = os.path.dirname(_backend_dir)
load_dotenv(os.path.join(_backend_dir, ".env"))   # backend/.env
load_dotenv(os.path.join(_project_root, ".env"))   # project root/.env

class LLMHandler:
    def __init__(self):
        # LiteLLM automatically uses os.environ for API keys
        # We just ensure dotenv is loaded.
        print("[LLM] Initialized via LiteLLM")

    def reload_keys(self):
        """Re-read .env and refresh environment variables for litellm."""
        load_dotenv(os.path.join(_backend_dir, ".env"), override=True)
        load_dotenv(os.path.join(_project_root, ".env"), override=True)
        print("[LLM] Reloaded environment variables for API keys")

    def get_response(self, prompt, model="gemini/gemini-1.5-pro-latest", system_prompt=None, chat_history=None, mode="Fast Mode"):
        """
        Generates response from LLM using litellm router.
        """
        if not model:
            model = "gemini/gemini-1.5-pro-latest"
            
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
        
        # Try getting completion
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except litellm.exceptions.RateLimitError as e:
            print(f"[LLM] Rate Limited: {str(e)}")
            return f"Error: The API key for {model} is rate-limited. Please try again later or configure a different provider in Settings."
        except litellm.exceptions.AuthenticationError as e:
            print(f"[LLM] Auth Error: {str(e)}")
            return f"Error: Authentication failed for {model}. Please check your API key in Settings."
        except Exception as e:
            print(f"[LLM] API Error: {str(e)}")
            return f"Error calling {model} API: {str(e)}"
