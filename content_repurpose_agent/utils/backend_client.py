"""HTTP client for communicating with the FastAPI backend."""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


class BackendClient:
    """Client for interacting with the FastAPI backend."""

    def __init__(self, base_url: str = BACKEND_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def health_check(self) -> bool:
        """Check if the backend is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def ask_question(self, question: str) -> str:
        """Send a question to the /ask endpoint and return the answer."""
        try:
            response = requests.post(
                f"{self.base_url}/ask",
                json={"question": question},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.RequestException as exc:
            raise RuntimeError(f"Backend request failed: {exc}") from exc

    def generate_content(
        self,
        text: Optional[str] = None,
        segments: Optional[List[str]] = None,
        tone: str = "Professional",
        platforms: List[str] = None,
        project_title: Optional[str] = None,
        save: bool = False,
        user_id: Optional[int] = None,
    ) -> Dict:
        """Generate content via the /generate endpoint."""
        if platforms is None:
            platforms = ["LinkedIn"]

        payload = {
            "tone": tone,
            "platforms": platforms,
            "save": save,
        }
        if text:
            payload["text"] = text
        if segments:
            payload["segments"] = segments
        if project_title:
            payload["project_title"] = project_title
        if user_id is not None:
            payload["user_id"] = user_id

        try:
            response = requests.post(
                f"{self.base_url}/generate",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Backend request failed: {exc}") from exc


__all__ = ["BackendClient", "BACKEND_URL"]

