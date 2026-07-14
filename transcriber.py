from functools import lru_cache

from faster_whisper import WhisperModel

from config import WHISPER_COMPUTE_TYPE, WHISPER_DEVICE, WHISPER_MODEL, WHISPER_TASK, WHISPER_LANGUAGE


class WhisperTranscriber:
    """
    Wraps faster-whisper for local transcription.
    Downloads the requested Whisper model on first use.
    """

    def __init__(self):
        self._model = self._load_model()

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_model() -> WhisperModel:
        return WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )

    def transcribe(self, audio_path: str) -> str:
        """
        Run faster-whisper on a WAV file and return the transcript string.
        """
        try:
            segments, _info = self._model.transcribe(
                audio_path,
                beam_size=1,
                language=WHISPER_LANGUAGE,
                task=WHISPER_TASK,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as e:
            print(f"[Whisper] Exception: {e}")
            return ""

    def transcribe_segments(self, audio_path: str) -> list:
        """
        Run faster-whisper on a WAV file and return list of segments with timestamp info.
        """
        try:
            segments, _info = self._model.transcribe(
                audio_path,
                beam_size=1,
                language=WHISPER_LANGUAGE,
                task=WHISPER_TASK,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            return list(segments)
        except Exception as e:
            print(f"[Whisper] Exception in transcribe_segments: {e}")
            return []