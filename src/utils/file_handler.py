"""
src/utils/file_handler.py
Handles all transcript persistence — JSON and/or plain text.
Each session gets its own timestamped file pair.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from src.utils.logger import get_logger


class TranscriptFileHandler:
    """
    Writes transcript utterances to disk in real-time.
    Supports JSON (structured) and/or TXT (human-readable) output.
    """

    def __init__(self, config: dict):
        self._cfg = config["output"]
        self._fmt: str = self._cfg["format"]  # json | txt | both
        self._logger = get_logger(__name__, config)

        output_dir = Path(self._cfg["transcripts_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self._cfg.get("filename_prefix", "session")
        base = output_dir / f"{prefix}_{timestamp}"

        self._json_path = base.with_suffix(".json") if self._fmt in ("json", "both") else None
        self._txt_path = base.with_suffix(".txt") if self._fmt in ("txt", "both") else None

        self._utterances: list[dict] = []
        self._session_start = datetime.utcnow().isoformat()

        self._logger.info(f"Transcript session started → {base}.*")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write(self, text: str, language: str | None = None, duration_s: float | None = None) -> None:
        """Append one utterance and flush to disk immediately."""
        utterance = {
            "timestamp": datetime.utcnow().isoformat(),
            "text": text.strip(),
            "language": language,
            "duration_s": round(duration_s, 3) if duration_s is not None else None,
        }
        self._utterances.append(utterance)

        if self._json_path:
            self._flush_json()
        if self._txt_path:
            self._flush_txt(utterance)

        self._logger.debug(f"Utterance saved [{language}]: {text[:60]}...")

    def close(self) -> None:
        """Finalize files at end of session."""
        if self._json_path:
            self._flush_json(final=True)
        self._logger.info(
            f"Session closed. {len(self._utterances)} utterance(s) saved."
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _flush_json(self, final: bool = False) -> None:
        payload = {
            "session_start": self._session_start,
            "session_end": datetime.utcnow().isoformat() if final else None,
            "utterance_count": len(self._utterances),
            "utterances": self._utterances,
        }
        try:
            with open(self._json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError as e:
            self._logger.error(f"Failed to write JSON transcript: {e}")

    def _flush_txt(self, utterance: dict) -> None:
        line = f"[{utterance['timestamp']}] {utterance['text']}\n"
        try:
            with open(self._txt_path, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            self._logger.error(f"Failed to write TXT transcript: {e}")
