import os
import sys

class PyannoteDiarizer:
    """
    Wraps pyannote.audio for speaker diarization.
    Requires PyTorch and a valid Hugging Face token.
    """

    def __init__(self, hf_token: str | None):
        self.enabled = False
        self._pipeline = None

        if not hf_token:
            print("[PyannoteDiarizer] WARNING: 'HF_TOKEN' is not configured in .env. Diarization will be disabled.")
            return

        try:
            import torch
            from pyannote.audio import Pipeline
        except ImportError as e:
            print(f"[PyannoteDiarizer] WARNING: Required package missing ({e}). Diarization will be disabled.")
            return

        try:
            print("[PyannoteDiarizer] Initializing pyannote pipeline...")
            # Load the pyannote speaker diarization pipeline
            try:
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    token=hf_token
                )
            except TypeError:
                self._pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=hf_token
                )
            
            # Send to GPU if available, otherwise CPU
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._pipeline.to(device)
            print(f"[PyannoteDiarizer] Pipeline loaded on device: {device}")
            self.enabled = True
        except Exception as e:
            print(f"[PyannoteDiarizer] WARNING: Failed to initialize pipeline: {e}")
            print("[PyannoteDiarizer] Please ensure you accepted the user agreements for:")
            print("  1. https://huggingface.co/pyannote/speaker-diarization-3.1")
            print("  2. https://huggingface.co/pyannote/segmentation-3.0")
            self.enabled = False

    def diarize(self, audio_path: str) -> list[dict]:
        """
        Runs speaker diarization on a WAV file.
        Returns a list of dicts: [{'start': float, 'end': float, 'speaker': str}]
        """
        if not self.enabled or self._pipeline is None:
            return []

        try:
            print(f"[PyannoteDiarizer] Running diarization on {audio_path}...")
            diarization = self._pipeline(audio_path)
            
            results = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                results.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
            print(f"[PyannoteDiarizer] Found {len(results)} speaker segments.")
            return results
        except Exception as e:
            print(f"[PyannoteDiarizer] Error during diarization: {e}")
            return []
