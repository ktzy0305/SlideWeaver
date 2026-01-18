"""Configuration settings for PowerPoint Generator."""

from pathlib import Path
from typing import Any

import yaml

# =============================================================================
# Path Configuration (always relative to project structure)
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "configs" / "config.yaml"

# Directory paths
DATA_DIR = PROJECT_ROOT / "data"
CATALOG_PATH = DATA_DIR / "visualisation_store" / "catalog.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
SESSIONS_DIR = PROJECT_ROOT / "sessions"
JS_CONVERTER_SCRIPT = PROJECT_ROOT / "js" / "html2pptx" / "cli.cjs"
PROMPTS_DIR = Path(__file__).parent / "prompts"


# =============================================================================
# Config Loading
# =============================================================================


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_config(key: str, default: Any = None) -> Any:
    """Get a config value by dot-notation key (e.g., 'api.port')."""
    config = load_config()
    keys = key.split(".")
    value = config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    return value if value is not None else default


# =============================================================================
# Convenience accessors
# =============================================================================


def get_api_host() -> str:
    return get_config("api.host", "0.0.0.0")


def get_api_port() -> int:
    return get_config("api.port", 8000)


def get_api_base_url() -> str:
    return f"http://localhost:{get_api_port()}"


def get_default_audience() -> str:
    return get_config("defaults.audience", "General business audience")


def get_default_tone() -> str:
    return get_config("defaults.tone", "executive")


def get_default_model_id() -> str:
    return get_config("defaults.model_id", "gpt-5-mini")


def get_max_words_per_slide() -> int:
    return get_config("slides.max_words_per_slide", 75)


def get_converter_timeout() -> int:
    return get_config("timeouts.converter", 120)


def get_allowed_image_extensions() -> set[str]:
    extensions = get_config("uploads.allowed_extensions", [])
    return (
        set(extensions)
        if extensions
        else {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
    )


def get_max_image_size_mb() -> int:
    return get_config("uploads.max_image_size_mb", 10)
