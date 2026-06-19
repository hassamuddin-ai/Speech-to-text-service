"""
src/transcription/pipeline.py
Orchestrates: AudioCapture → VAD → WhisperClient → LanguageFilter → FileHandler
Runs the main processing loop in a background thread.

Language filtering: only English and Urdu utterances are printed/saved.
Urdu text is displayed with a right-aligned RTL label in the terminal.
"""
import threading
from src.utils.text_normalizer import TextNormalizer

from rich.console import Console
from rich.text import Text
from rich.align import Align

from src.audio.capture import AudioCapture
from src.audio.utils import frames_to_wav_buffer, frames_duration_seconds
from src.vad.detector import VoiceActivityDetector
from src.transcription.whisper_client import WhisperClient
from src.transcription.language_filter import LanguageFilter, is_urdu, is_english
from src.utils.file_handler import TranscriptFileHandler
from src.utils.logger import get_logger
from src.utils.roman_urdu import to_roman_urdu

console = Console()


class TranscriptionPipeline:
    """
    Full real-time STT pipeline.
    Call start() to begin listening, stop() to shut down cleanly.

    Terminal output:
      English → left-aligned, white text,  [en] tag
      Urdu    → right-aligned, cyan text,  [اردو] tag  (RTL friendly)
      Other   → silently dropped (not printed, not saved)
    """

    def __init__(self, config: dict):
        self._config = config
        self._logger = get_logger(__name__, config)

        self._capture = AudioCapture(config)
        self._vad = VoiceActivityDetector(config)
        self._whisper = WhisperClient(config)
        self._normalizer = TextNormalizer(config.get("normalizer", {}).get("mode", "auto"))

        self._lang_filter = LanguageFilter(config)          # ← NEW
        self._file_handler = TranscriptFileHandler(config)

        self._running = False
        self._thread: threading.Thread | None = None
        self._realtime_print: bool = config["output"]["realtime_print"]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._capture.start()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._logger.info(
            "[bold green]Pipeline started[/bold green] — speak now. Press Ctrl+C to stop."
        )
        console.print("\n[bold cyan]🎙  Listening…[/bold cyan]  "
                      "[dim](English & Urdu only)[/dim]\n")

    def stop(self) -> None:
        self._logger.info("Shutting down pipeline…")
        self._running = False
        self._capture.stop()

        remaining = self._vad.flush_remaining()
        if remaining:
            self._transcribe_and_save(remaining)

        if self._thread:
            self._thread.join(timeout=5)

        self._file_handler.close()
        console.print("\n[bold yellow]Session ended.[/bold yellow]")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        while self._running:
            chunk = self._capture.get_chunk(timeout=0.3)
            if chunk is None:
                continue

            frames, should_flush = self._vad.process(chunk)

            if should_flush and frames:
                self._transcribe_and_save(frames)

    # ------------------------------------------------------------------
    # Transcription + filtering
    # ------------------------------------------------------------------

    def _transcribe_and_save(self, frames: list) -> None:
        duration = frames_duration_seconds(
            frames, self._config["audio"]["sample_rate"]
        )

        if duration < 0.3:
            self._logger.debug(f"Skipping very short segment ({duration:.2f}s)")
            return

        try:
            wav_buf = frames_to_wav_buffer(
                frames, self._config["audio"]["sample_rate"]
            )
            text, language = self._whisper.transcribe(wav_buf)
            text = self._normalizer.normalize(text)   

            if not text:
                return

            # ── Language filter ──────────────────────────────────────
            keep, norm_lang = self._lang_filter.check(text, language)

            if not keep:
                self._logger.debug(
                    f"Dropped segment (lang={language}): {text[:60]}"
                )
                return
            # ────────────────────────────────────────────────────────

            # ── Roman Urdu conversion ─────────────────────────────────
            if is_urdu(norm_lang):
                display_text = to_roman_urdu(text)   # mixed Urdu+English → Roman
            else:
                display_text = text
            # ─────────────────────────────────────────────────────────

            self._file_handler.write(display_text, language=norm_lang, duration_s=duration)

            if self._realtime_print:
                self._print_utterance(display_text, norm_lang, duration)

        except RuntimeError as e:
            self._logger.error(f"Transcription error: {e}")

    # ------------------------------------------------------------------
    # Terminal display  (language-aware)
    # ------------------------------------------------------------------

    def _print_utterance(
        self, text: str, language: str | None, duration: float
    ) -> None:
        dur = f"({duration:.1f}s)"

        if is_urdu(language):
            # ── Urdu: cyan, right-aligned, Urdu label ──────────────
            # Rich can't flip text direction, but right-align + label
            # gives a clear visual cue that this is RTL content.
            line = Text()
            line.append(f"{dur} ", style="dim")
            line.append("[اردو] ", style="bold magenta")
            line.append(text, style="cyan bold")
            console.print(Align.right(line))

        elif is_english(language):
            # ── English: white, left-aligned, [en] label ───────────
            line = Text()
            line.append("[en] ", style="bold green dim")
            line.append(text, style="white")
            line.append(f"  {dur}", style="dim")
            console.print(f"  {line}")

        else:
            # ── Language unknown but passed filter (auto-detect) ───
            line = Text()
            line.append("[?] ", style="dim yellow")
            line.append(text, style="white")
            line.append(f"  {dur}", style="dim")
            console.print(f"  {line}")