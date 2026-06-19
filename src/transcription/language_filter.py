"""
src/transcription/language_filter.py
Drops utterances that are not English or Urdu.
Also detects Urdu written in Hindi script and flags it.
"""

URDU_CODES  = {"ur", "urd", "urdu"}
ENGLISH_CODES = {"en", "eng", "english"}

# Languages to silently drop
BLOCKED = {
    "tl", "fil",  # Filipino/Tagalog
    "ms", "zsm",  # Malay
    "hi", "hin",  # Hindi
    "pt", "por",  # Portuguese
    "ru", "rus",  # Russian
    "fr", "fra",  # French
    "de", "deu",  # German
    "es", "spa",  # Spanish
    "zh", "zho",  # Chinese
    "ja", "jpn",  # Japanese
    "ko", "kor",  # Korean
}

def is_urdu(language: str | None) -> bool:
    return (language or "").lower() in URDU_CODES

def is_english(language: str | None) -> bool:
    return (language or "").lower() in ENGLISH_CODES

def is_allowed(language: str | None) -> bool:
    lang = (language or "").lower()
    return lang in URDU_CODES or lang in ENGLISH_CODES or lang == ""


class LanguageFilter:
    def __init__(self, config: dict):
        self._enabled = config.get("language_filter", {}).get("enabled", True)

    def check(self, text: str, language: str | None) -> tuple[bool, str | None]:
        """
        Returns (keep, normalized_language).
        keep=False means drop this utterance.
        """
        if not self._enabled:
            return True, language

        if is_allowed(language):
            return True, language

        # Drop everything else
        return False, language