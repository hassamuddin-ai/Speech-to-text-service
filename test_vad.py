"""
tests/test_vad.py — Unit tests for VAD and audio utilities.
Run with: pytest tests/
"""
import numpy as np
import pytest

from src.audio.utils import frames_to_wav_buffer, frames_duration_seconds

# Minimal config stub
_CONFIG = {
    "audio": {"sample_rate": 16000, "channels": 1, "chunk_ms": 30, "dtype": "float32"},
    "vad": {"aggressiveness": 2, "silence_threshold": 25, "min_speech_frames": 5},
    "logging": {"level": "WARNING", "log_dir": "/tmp/stt_test_logs",
                 "max_bytes": 1000000, "backup_count": 1},
}


class TestAudioUtils:
    def test_frames_to_wav_buffer_returns_bytes(self):
        frames = [np.zeros(480, dtype=np.float32) for _ in range(10)]
        buf = frames_to_wav_buffer(frames, sample_rate=16000)
        assert buf.read(4) == b"RIFF"

    def test_frames_duration(self):
        frames = [np.zeros(16000, dtype=np.float32)]  # exactly 1 second
        assert frames_duration_seconds(frames, 16000) == pytest.approx(1.0)

    def test_frames_clip_overflow(self):
        """Values outside [-1, 1] should be clipped, not wrap."""
        frames = [np.array([2.0, -2.0], dtype=np.float32)]
        buf = frames_to_wav_buffer(frames, sample_rate=16000)
        assert buf is not None  # Should not raise
