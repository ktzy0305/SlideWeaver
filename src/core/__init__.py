"""Core module for PowerPoint Generator business logic."""

from core.config import (
    CATALOG_PATH,
    DEFAULT_OUTPUT_DIR,
    JS_CONVERTER_SCRIPT,
    PROJECT_ROOT,
    PROMPTS_DIR,
    SESSIONS_DIR,
    get_api_base_url,
    get_api_host,
    get_api_port,
    get_default_audience,
    get_default_model_id,
    get_default_tone,
)

__all__ = [
    "CATALOG_PATH",
    "DEFAULT_OUTPUT_DIR",
    "JS_CONVERTER_SCRIPT",
    "PROJECT_ROOT",
    "PROMPTS_DIR",
    "SESSIONS_DIR",
    "get_api_base_url",
    "get_api_host",
    "get_api_port",
    "get_default_audience",
    "get_default_model_id",
    "get_default_tone",
]
