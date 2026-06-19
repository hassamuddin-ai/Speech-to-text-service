"""
src/audio/utils.py
Audio format helpers: frame list → WAV bytes for Whisper API.
"""
import io
import wave
import numpy as np


def frames_to_wav_buffer(frames: list[np.ndarray], sample_rate: int) -> io.BytesIO:
    """
    Concatenate float32 audio frames and encode as an in-memory WAV file.

    Args:
        frames: list of float32 numpy arrays (values in [-1.0, 1.0])
        sample_rate: Hz

    Returns:
        BytesIO buffer positioned at start, named 'audio.wav'
    """
    audio = np.concatenate(frames)
    pcm_bytes = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)       # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)

    buf.seek(0)
    buf.name = "audio.wav"      # Required by OpenAI SDK
    return buf


def frames_duration_seconds(frames: list[np.ndarray], sample_rate: int) -> float:
    """Return total duration in seconds for a list of audio frames."""
    total_samples = sum(len(f) for f in frames)
    return total_samples / sample_rate
