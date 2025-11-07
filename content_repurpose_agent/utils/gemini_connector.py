"""Wrapper around the Google Gemini API."""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional

import google.generativeai as genai
from dotenv import load_dotenv


class GeminiConnector:
    """Handle interactions with the Gemini API."""

    def __init__(self, model_name: str | None = None) -> None:
        # Load environment variables from a local .env file if present
        # override=True ensures we pick up updates made to .env during a running session
        load_dotenv(override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please configure it before generating content."
            )

        genai.configure(api_key=api_key)
        # Resolve model preference order with auto-discovery fallback
        env_model = os.getenv("GEMINI_MODEL")
        preferred = model_name or env_model
        discovered = self._discover_supported_models()
        self._model_names: List[str] = []
        if preferred:
            self._model_names.append(preferred)
        # Prefer common modern choices first, then discovered models
        for name in ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]:
            if name not in self._model_names:
                self._model_names.append(name)
        for name in discovered:
            if name not in self._model_names:
                self._model_names.append(name)

        self._current_model_index = 0
        self.model = genai.GenerativeModel(self._model_names[self._current_model_index])

    def _switch_to_next_model(self) -> bool:
        if self._current_model_index + 1 < len(self._model_names):
            self._current_model_index += 1
            self.model = genai.GenerativeModel(self._model_names[self._current_model_index])
            return True
        return False

    def generate_text(self, prompt: str) -> str:
        """Generate content for a single prompt."""

        if not prompt.strip():
            return ""

        try:
            result = self.model.generate_content(prompt)
        except Exception as exc:  # pragma: no cover - depends on external API
            message = str(exc)
            # Auto-fallback if current model is unavailable (404 or not supported)
            if ("404" in message or "not found" in message.lower() or "not supported" in message.lower()) and self._switch_to_next_model():
                try:
                    result = self.model.generate_content(prompt)
                except Exception as exc2:  # pragma: no cover
                    return f"Error generating content: {exc2}"
            else:
                # Suggest available models if we have them
                try:
                    available = ", ".join(self._discover_supported_models()[:10]) or "(none discovered)"
                except Exception:
                    available = "(unavailable)"
                return (
                    f"Error generating content: {exc}\n"
                    f"Tip: Set GEMINI_MODEL to one of: {available}"
                )

        text = getattr(result, "text", None)
        if not text and hasattr(result, "candidates"):
            candidate_texts = []
            for candidate in getattr(result, "candidates", []) or []:
                content = getattr(candidate, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", []) or []
                candidate_texts.extend(str(part.text) for part in parts if hasattr(part, "text"))
            text = "\n".join(candidate_texts)

        return (text or "").strip()

    def generate(self, prompts_by_platform: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Generate Gemini responses for each platform and prompt."""

        outputs: Dict[str, List[str]] = {}
        for platform, prompts in prompts_by_platform.items():
            responses = [self.generate_text(prompt) for prompt in prompts]
            outputs[platform] = responses
        return outputs

    @staticmethod
    def _discover_supported_models() -> List[str]:
        """Return model names that support generateContent for this API key/account."""
        try:
            models = genai.list_models()
        except Exception:
            return []

        names: List[str] = []
        for m in models:
            methods = set(getattr(m, "supported_generation_methods", []) or [])
            # Some SDK versions use 'generateContent' method name
            if "generateContent" in methods or "generate_content" in methods:
                names.append(getattr(m, "name", "").replace("models/", ""))
        return names

    @staticmethod
    def combine_segment_outputs(outputs: Iterable[str]) -> str:
        """Combine multiple segment responses into a single block."""

        cleaned_segments = [segment.strip() for segment in outputs if segment.strip()]
        return "\n\n".join(cleaned_segments)


__all__ = ["GeminiConnector"]

