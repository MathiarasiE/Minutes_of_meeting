import sounddevice as sd
import numpy as np
import queue
import threading
from config import SAMPLE_RATE, CHANNELS, AUDIO_GAIN


class AudioRecorder:
    """
    Continuously records from microphone.
    Yields numpy arrays of CHUNK_SAMPLES length via a queue.
    """

    def __init__(self):
        self._q: queue.Queue = queue.Queue()
        self._buffer = np.array([], dtype=np.float32)
        self._running = False
        self._stream = None
        self._thread = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Audio] Warning: {status}")
        # Scale audio samples digitally by AUDIO_GAIN
        scaled_data = indata[:, 0] * AUDIO_GAIN
        self._q.put(scaled_data.copy())   # mono

    def start(self):
        self._running = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self._callback,
            blocksize=1024,
        )
        self._stream.start()
        print("[Recorder] Started.")

    def stop(self):
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
        print("[Recorder] Stopped.")

    def read_chunk(self, chunk_samples: int) -> np.ndarray | None:
        """
        Blocks until exactly chunk_samples are accumulated, then returns them.
        Returns None if recorder is stopped before enough samples arrive.
        """
        while self._running or not self._q.empty():
            try:
                data = self._q.get(timeout=0.5)
                self._buffer = np.concatenate([self._buffer, data])
            except queue.Empty:
                if not self._running:
                    break

            if len(self._buffer) >= chunk_samples:
                chunk = self._buffer[:chunk_samples].copy()
                self._buffer = self._buffer[chunk_samples:]
                return chunk

        # Flush remaining audio (partial last chunk)
        if len(self._buffer) > 0:
            return self._buffer.copy()

        return None