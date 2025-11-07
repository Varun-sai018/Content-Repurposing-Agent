"""Load and parse input/output schema files for dynamic UI generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA_DIR = Path(__file__).resolve().parent.parent
INPUT_SCHEMA_PATH = SCHEMA_DIR / "input.json"
OUTPUT_SCHEMA_PATH = SCHEMA_DIR / "output.json"


def load_input_schema() -> List[Dict[str, Any]]:
    """Load and return the input schema from input.json."""
    try:
        with open(INPUT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {INPUT_SCHEMA_PATH}: {exc}") from exc


def load_output_schema() -> List[Dict[str, Any]]:
    """Load and return the output schema from output.json."""
    try:
        with open(OUTPUT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {OUTPUT_SCHEMA_PATH}: {exc}") from exc


def get_field_by_key(schema: List[Dict[str, Any]], key: str) -> Optional[Dict[str, Any]]:
    """Find a schema field by its key."""
    for field in schema:
        if field.get("key") == key:
            return field
    return None


def get_options_for_field(schema: List[Dict[str, Any]], key: str) -> Optional[List[str]]:
    """Extract options list for a select/multiselect field."""
    field = get_field_by_key(schema, key)
    if not field:
        return None
    return field.get("options")


__all__ = [
    "load_input_schema",
    "load_output_schema",
    "get_field_by_key",
    "get_options_for_field",
    "INPUT_SCHEMA_PATH",
    "OUTPUT_SCHEMA_PATH",
]

