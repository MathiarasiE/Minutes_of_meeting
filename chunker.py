import os
import wave
import numpy as np
import soundfile as sf
from config import AUDIO_DIR, SAMPLE_RATE


def ensure_audio_dir():
    os.makedirs(AUDIO_DIR, exist_ok=True)


def save_chunk_wav(meeting_id: int, chunk_index: int, audio: np.ndarray) -> str:
    """Save a float32 numpy array as a 16-bit WAV file. Returns file path."""
    ensure_audio_dir()
    filename = f"meeting_{meeting_id}_chunk_{chunk_index:04d}.wav"
    path = os.path.join(AUDIO_DIR, filename)
    sf.write(path, audio, SAMPLE_RATE, subtype="PCM_16")
    return path