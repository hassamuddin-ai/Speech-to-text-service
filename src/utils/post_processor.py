"""
src/utils/post_processor.py
====================================================
Post-processes transcribed text:
- Urdu → Roman Urdu (English words kept as-is)
- Saves processed output to file
- Returns formatted text for UI display
"""

import json
from datetime import datetime
from pathlib import Path

from src.utils.roman_urdu import to_roman_urdu


class PostProcessor:
    """
    Applies post-processing to transcribed text and saves results.

    Usage:
        pp = PostProcessor(output_dir="output/processed")
        result = pp.process("مجھے glossary چاہیے", lang="ur")
        # result.original  → "مجھے glossary چاہیے"
        # result.processed → "mujhe glossary chahiye"
    """

    def __init__(self, output_dir: str = "output/processed"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._txt_path  = self._output_dir / f"roman_urdu_{timestamp}.txt"
        self._json_path = self._output_dir / f"roman_urdu_{timestamp}.json"
        self._entries: list[dict] = []

    def process(self, text: str, lang: str | None = None) -> "ProcessedResult":
        """
        Process a single utterance.
        Returns a ProcessedResult with original and processed text.
        """
        is_urdu = lang and lang.lower() in ("ur", "urd", "urdu")

        if is_urdu:
            processed = to_roman_urdu(text)
        else:
            processed = text  # English — no change needed

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "language": lang,
            "original": text,
            "processed": processed,
            "was_transliterated": is_urdu,
        }
        self._entries.append(entry)
        self._flush(entry)

        return ProcessedResult(
            original=text,
            processed=processed,
            language=lang,
            was_transliterated=bool(is_urdu),
        )

    def _flush(self, entry: dict) -> None:
        """Write entry to both txt and json files immediately."""
        # TXT — human readable
        try:
            with open(self._txt_path, "a", encoding="utf-8") as f:
                ts = entry["timestamp"]
                lang = entry["language"] or "?"
                if entry["was_transliterated"]:
                    f.write(f"[{ts}] [{lang}]\n")
                    f.write(f"  Urdu:   {entry['original']}\n")
                    f.write(f"  Roman:  {entry['processed']}\n\n")
                else:
                    f.write(f"[{ts}] [{lang}] {entry['processed']}\n")
        except OSError as e:
            print(f"Failed to write TXT: {e}")

        # JSON — structured
        try:
            payload = {
                "session_start": self._entries[0]["timestamp"] if self._entries else "",
                "total_entries": len(self._entries),
                "entries": self._entries,
            }
            with open(self._json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Failed to write JSON: {e}")

    @property
    def txt_path(self) -> Path:
        return self._txt_path

    @property
    def json_path(self) -> Path:
        return self._json_path


class ProcessedResult:
    """Holds the result of post-processing a single utterance."""

    def __init__(
        self,
        original: str,
        processed: str,
        language: str | None,
        was_transliterated: bool,
    ):
        self.original = original
        self.processed = processed
        self.language = language
        self.was_transliterated = was_transliterated

    def display(self) -> str:
        """Format for UI display."""
        if self.was_transliterated:
            lang_tag = "[اردو → Roman]"
            return (
                f"🗣️ {lang_tag}\n"
                f"**Urdu:** {self.original}\n"
                f"**Roman:** {self.processed}"
            )
        else:
            return f"🗣️ [en] {self.processed}"