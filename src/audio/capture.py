"""
src/audio/capture.py
Microphone capture using PyAudio — more reliable on WSL2/PulseAudio.
"""
import queue
import threading
import numpy as np
import pyaudio

from src.utils.logger import get_logger


class AudioCapture:
    def __init__(self, config: dict):
        audio_cfg = config["audio"]
        self._sample_rate: int = audio_cfg["sample_rate"]
        self._channels: int = audio_cfg["channels"]
        self._chunk_size: int = int(
            self._sample_rate * audio_cfg["chunk_ms"] / 1000
        )
        self._logger = get_logger(__name__, config)
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._pa = None
        self._stream = None

    def start(self) -> None:
        self._logger.info(
            f"Opening mic stream — {self._sample_rate}Hz, "
            f"{self._chunk_size} samples/chunk"
        )
        self._pa = pyaudio.PyAudio()

        # Find pulse device
        device_index = None
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if "pulse" in info["name"].lower() and info["maxInputChannels"] > 0:
                device_index = i
                break

        self._logger.info(f"Using device index: {device_index}")

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self._chunk_size,
        )

        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                raw = self._stream.read(self._chunk_size, exception_on_overflow=False)
                pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
                self._queue.put(pcm)
            except Exception as e:
                self._logger.warning(f"Audio read error: {e}")

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()
        self._logger.info("Mic stream closed.")

    def get_chunk(self, timeout: float = 0.5) -> np.ndarray | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        