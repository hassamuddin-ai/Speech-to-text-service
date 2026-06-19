"""
config/loader.py
Loads and validates settings from settings.yaml + .env
"""
import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()

_CONFIG_PATH = Path(__file__).parent / "settings.yaml"


def load_config() -> dict:
    """Load config from YAML, inject env vars, and validate."""
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    # Inject API key from environment
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set. Add it to your .env file.")
    config["groq_api_key"] = api_key



    _validate(config)
    return config


def _validate(config: dict) -> None:
    """Raise ValueError for invalid config values."""
    chunk_ms = config["audio"]["chunk_ms"]
    if chunk_ms not in (10, 20, 30):
        raise ValueError(f"audio.chunk_ms must be 10, 20, or 30 (got {chunk_ms})")

    agg = config["vad"]["aggressiveness"]
    if agg not in range(4):
        raise ValueError(f"vad.aggressiveness must be 0–3 (got {agg})")

    fmt = config["output"]["format"]
    if fmt not in ("json", "txt", "both"):
        raise ValueError(f"output.format must be json | txt | both (got {fmt})")
