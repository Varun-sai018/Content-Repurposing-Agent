"""FastAPI backend for the Content Repurposing Agent."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator

from utils import db
from utils.gemini_connector import GeminiConnector
from utils.input_handler import DEFAULT_MAX_WORDS, enforce_word_limit
from utils.prompt_builder import PromptBuilder
from utils.segmentation import split_into_segments
from utils.templates import PLATFORMS, TONES


logger = logging.getLogger("content_repurpose_agent.backend")

app = FastAPI(title="Content Repurposing Agent API", version="1.0.0")


class GenerateRequest(BaseModel):
    text: Optional[str] = Field(
        default=None,
        description="Raw text input to be segmented. If segments are provided, this is optional.",
    )
    segments: Optional[List[str]] = Field(
        default=None,
        description="Predefined segments to repurpose. Overrides automatic segmentation if provided.",
    )
    tone: str = Field(..., description="Display tone name (e.g., 'Professional').")
    platforms: List[str] = Field(
        ..., description="List of platform display names (e.g., ['LinkedIn', 'Instagram'])."
    )
    project_title: Optional[str] = Field(
        default=None,
        description="Optional title used when saving results to the database.",
    )
    save: bool = Field(
        default=False,
        description="Persist generated outputs to the SQLite database when True.",
    )
    user_id: Optional[int] = Field(
        default=None,
        description="Optional ID of the authenticated user saving content.",
    )

    @validator("tone")
    def validate_tone(cls, value: str) -> str:
        if value not in TONES:
            raise ValueError(f"Unsupported tone '{value}'. Expected one of {list(TONES)}")
        return value

    @validator("platforms")
    def validate_platforms(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("At least one platform is required.")
        unknown = [platform for platform in value if platform not in PLATFORMS]
        if unknown:
            raise ValueError(
                f"Unsupported platform(s): {unknown}. Expected one of {list(PLATFORMS)}"
            )
        return value

    @validator("segments", each_item=True)
    def validate_segment_content(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Segments must contain text.")
        return value


class GenerateResponse(BaseModel):
    tone: str
    platforms: List[str]
    segment_count: int
    outputs: Dict[str, str]
    saved: bool = False


@app.on_event("startup")
def init_database() -> None:
    try:
        db.init_db()
    except Exception as exc:  # pragma: no cover - initialization failure is fatal
        logger.error("Failed to initialize database: %s", exc)
        raise


@app.get("/health", tags=["system"])
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse, tags=["generation"])
def generate_content(payload: GenerateRequest) -> GenerateResponse:
    # Determine source segments
    segments: List[str]

    if payload.segments:
        segments = [segment.strip() for segment in payload.segments if segment.strip()]
    else:
        if not payload.text or not payload.text.strip():
            raise HTTPException(status_code=400, detail="Provide either text or segments to repurpose.")

        limited_text, _ = enforce_word_limit(payload.text, DEFAULT_MAX_WORDS)
        segments = split_into_segments(limited_text)
        if not segments:
            segments = [limited_text]

    # Build prompts and call Gemini
    try:
        prompt_builder = PromptBuilder(payload.tone, payload.platforms)
        prompts = prompt_builder.build_prompts(segments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        connector = GeminiConnector()
    except EnvironmentError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    outputs: Dict[str, str] = {}
    for platform_id, prompt_list in prompts.items():
        responses = [connector.generate_text(prompt) for prompt in prompt_list]
        outputs[platform_id] = GeminiConnector.combine_segment_outputs(responses)

    # Optionally persist results
    saved = False
    if payload.save:
        if not payload.project_title or not payload.project_title.strip():
            raise HTTPException(status_code=400, detail="Project title is required when save=True.")
        if payload.user_id is not None:
            user = db.get_user_by_id(payload.user_id)
            if not user:
                raise HTTPException(status_code=400, detail="Invalid user_id provided.")
        db.save_to_db(payload.project_title, payload.tone, outputs, user_id=payload.user_id)
        saved = True

    return GenerateResponse(
        tone=payload.tone,
        platforms=payload.platforms,
        segment_count=len(segments),
        outputs=outputs,
        saved=saved,
    )


__all__ = ["app"]

