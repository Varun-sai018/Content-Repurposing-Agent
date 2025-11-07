"""Build Gemini prompts for each platform and content segment."""

from __future__ import annotations

from typing import Dict, Iterable, List

from .templates import PLATFORMS, TEMPLATES, TONES


class PromptBuilder:
    """Create prompts for the selected platforms and tone."""

    def __init__(self, tone_display: str, platform_labels: Iterable[str]):
        if tone_display not in TONES:
            raise ValueError(f"Unsupported tone: {tone_display}")

        self.tone_key = TONES[tone_display]
        self.platform_ids = self._resolve_platforms(platform_labels)

    @staticmethod
    def _resolve_platforms(platform_labels: Iterable[str]) -> List[str]:
        resolved = []
        for label in platform_labels:
            platform_id = PLATFORMS.get(label)
            if platform_id is None:
                raise ValueError(f"Unsupported platform: {label}")
            resolved.append(platform_id)
        return resolved

    def build_prompts(self, segments: Iterable[str]) -> Dict[str, List[str]]:
        prompts: Dict[str, List[str]] = {}
        for platform_id in self.platform_ids:
            template_map = TEMPLATES[platform_id]
            if self.tone_key not in template_map:
                raise ValueError(
                    f"Tone '{self.tone_key}' is not defined for platform '{platform_id}'."
                )
            template = template_map[self.tone_key]
            prompts[platform_id] = [
                template.format(tone=self.tone_key, content=segment.strip())
                for segment in segments
                if segment.strip()
            ]
        return prompts


__all__ = ["PromptBuilder"]

