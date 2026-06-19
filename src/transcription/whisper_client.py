"""
src/transcription/whisper_client.py
Thin, retry-capable wrapper around the Groq Whisper transcription API.
"""
import io
import time

from groq import Groq
from groq import BadRequestError, AuthenticationError
import httpx

from src.utils.logger import get_logger


class WhisperClient:
    MAX_RETRIES = 3
    BACKOFF_BASE = 1.5

    def __init__(self, config: dict):
        self._cfg = config["whisper"]
        self._sample_rate: int = config["audio"]["sample_rate"]
        self._logger = get_logger(__name__, config)
        self._client = Groq(api_key=config["groq_api_key"])

    def transcribe(self, wav_buffer: io.BytesIO) -> tuple[str, str | None]:
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self._client.audio.transcriptions.create(
                    model=self._cfg["model"],
                    file=wav_buffer,
                    language=self._cfg.get("language"),
                    response_format=self._cfg["response_format"],
                    temperature=self._cfg.get("temperature", 0.0),
                )
                text, language = self._parse(response)
                self._logger.debug(f"Groq Whisper [{language}]: {text[:80]}")
                return text, language

            except AuthenticationError as e:
                # No point retrying — key is wrong
                raise RuntimeError(f"Groq auth failed — check your GROQ_API_KEY: {e}") from e

            except httpx.TimeoutException as e:
                wait = self.BACKOFF_BASE ** attempt
                self._logger.warning(f"Timeout, retrying in {wait}s… ({e})")
                time.sleep(wait)
                wav_buffer.seek(0)

            except Exception as e:
                self._logger.error(f"Groq error (attempt {attempt}): {e}")
                if attempt == self.MAX_RETRIES:
                    raise RuntimeError(f"Groq Whisper failed after {self.MAX_RETRIES} attempts: {e}") from e
                time.sleep(self.BACKOFF_BASE)
                wav_buffer.seek(0)

        raise RuntimeError("Transcription failed: max retries exceeded")

    def _parse(self, response) -> tuple[str, str | None]:
        if isinstance(response, str):
            return response.strip(), None
        text = getattr(response, "text", "").strip()
        language = getattr(response, "language", None)
        return text, language