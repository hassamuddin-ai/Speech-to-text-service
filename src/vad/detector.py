"""
src/vad/detector.py
WebRTC VAD wrapper with configurable aggressiveness and silence detection.
"""
import numpy as np
import webrtcvad

from src.utils.logger import get_logger


class VoiceActivityDetector:
    """
    Wraps webrtcvad to detect speech frames.
    Emits a flush signal when silence follows a speech segment.
    """

    def __init__(self, config: dict):
        vad_cfg = config["vad"]
        audio_cfg = config["audio"]

        self._sample_rate: int = audio_cfg["sample_rate"]
        self._silence_threshold: int = vad_cfg["silence_threshold"]
        self._min_speech_frames: int = vad_cfg["min_speech_frames"]

        self._vad = webrtcvad.Vad(vad_cfg["aggressiveness"])
        self._logger = get_logger(__name__, config)

        self._speech_buffer: list[np.ndarray] = []
        self._silent_frames: int = 0
        self._speech_frames: int = 0

    def process(self, chunk: np.ndarray) -> tuple[list[np.ndarray] | None, bool]:
        """
        Feed one audio chunk.

        Returns:
            (frames, should_flush):
                - frames: buffered audio frames to transcribe (or None)
                - should_flush: True when a complete utterance is ready
        """
        pcm = (chunk * 32767).astype(np.int16).tobytes()

        try:
            is_speech = self._vad.is_speech(pcm, self._sample_rate)
        except Exception as e:
            self._logger.warning(f"VAD error (skipping frame): {e}")
            return None, False

        if is_speech:
            self._speech_buffer.append(chunk.copy())
            self._speech_frames += 1
            self._silent_frames = 0
            return None, False

        # Silence
        self._silent_frames += 1
        if self._speech_buffer:
            self._speech_buffer.append(chunk.copy())  # trailing silence

        if (
            self._silent_frames >= self._silence_threshold
            and self._speech_frames >= self._min_speech_frames
        ):
            frames = self._speech_buffer.copy()
            self._reset()
            return frames, True

        return None, False

    def flush_remaining(self) -> list[np.ndarray] | None:
        """Force-flush any buffered audio (e.g. on shutdown)."""
        if self._speech_buffer and self._speech_frames >= self._min_speech_frames:
            frames = self._speech_buffer.copy()
            self._reset()
            return frames
        return None

    def _reset(self) -> None:
        self._speech_buffer = []
        self._silent_frames = 0
        self._speech_frames = 0
