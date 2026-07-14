import threading
import time
import os
from audio_recorder  import AudioRecorder
from chunker         import save_chunk_wav
from transcriber     import WhisperTranscriber
from summarizer      import QwenSummarizer
from database        import (
    create_meeting, end_meeting,
    save_chunk, save_summary,
    get_all_transcripts, get_summaries,
    get_meeting,
)
from config import CHUNK_SAMPLES, INTERMEDIATE_SUMMARY_EVERY, SPEAKER_MODEL, SPEAKER_THRESHOLD, HF_TOKEN
from tts import TTS
from doc_generator import generate_minutes_documents
from diarizer_pyannote import PyannoteDiarizer



class MeetingPipeline:

    def __init__(self, title: str = "Meeting"):
        self.title          = title
        self.meeting_id     = None
        self.recorder       = AudioRecorder()
        self.transcriber    = WhisperTranscriber()
        self.summarizer     = QwenSummarizer()
        self.diarizer       = PyannoteDiarizer(HF_TOKEN)
        self._last_speaker  = "Speaker 1"
        self.tts            = TTS()
        self._chunk_index   = 0
        self._running       = False
        self._last_summary_time = 0
        self.generated_docs = []

    # ── Internal helpers ─────────────────────────────────────────────────

    def _process_chunk(self, audio_chunk):
        """Save WAV → Transcribe with diarization → Persist to DB."""
        idx       = self._chunk_index
        self._chunk_index += 1

        audio_path = save_chunk_wav(self.meeting_id, idx, audio_chunk)
        print(f"[Pipeline] Transcribing chunk {idx} ...")
        
        segments = self.transcriber.transcribe_segments(audio_path)
        
        # Diarize the whole WAV file chunk
        diarization_segments = []
        if self.diarizer.enabled:
            diarization_segments = self.diarizer.diarize(audio_path)
        
        chunk_lines = []
        for seg in segments:
            # Align this transcript segment with Pyannote speaker timelines using overlap
            best_speaker = None
            speaker_overlaps = {}
            
            for d in diarization_segments:
                # Calculate overlap between Whisper segment [seg.start, seg.end] and Pyannote segment [d.start, d.end]
                overlap = max(0.0, min(seg.end, d["end"]) - max(seg.start, d["start"]))
                if overlap > 0.0:
                    speaker_overlaps[d["speaker"]] = speaker_overlaps.get(d["speaker"], 0.0) + overlap
            
            if speaker_overlaps:
                best_speaker = max(speaker_overlaps, key=speaker_overlaps.get)
                
            if best_speaker:
                # Map standard pyannote speaker label (e.g., SPEAKER_00) to Speaker N format
                import re
                match = re.search(r'\d+', best_speaker)
                if match:
                    num = int(match.group(0)) + 1
                    speaker_label = f"Speaker {num}"
                else:
                    speaker_label = best_speaker.replace("SPEAKER_", "Speaker ")
                self._last_speaker = speaker_label
            else:
                speaker_label = getattr(self, "_last_speaker", "Speaker 1")
                
            chunk_lines.append(f"[{speaker_label}]: {seg.text.strip()}")
            
        transcript = "\n".join(chunk_lines)
        print(f"[Pipeline] Chunk {idx} Diarized Transcript:\n{transcript[:150]}{'...' if len(transcript)>150 else ''}")

        save_chunk(self.meeting_id, idx, audio_path, transcript)
        return transcript

    def _maybe_intermediate_summary(self):
        now = time.time()
        if now - self._last_summary_time >= INTERMEDIATE_SUMMARY_EVERY:
            transcripts = get_all_transcripts(self.meeting_id)
            if transcripts:
                combined = "\n".join(transcripts)
                print("[Pipeline] Generating intermediate summary ...")
                summary = self.summarizer.intermediate_summary(combined)
                save_summary(self.meeting_id, "intermediate", summary)
                print(f"[Pipeline] Intermediate summary saved:\n{summary}\n")
            self._last_summary_time = now

    def _recording_loop(self):
        """Runs in a background thread: records → chunks → transcribes."""
        while self._running:
            chunk = self.recorder.read_chunk(CHUNK_SAMPLES)
            if chunk is None:
                break
            self._process_chunk(chunk)
            self._maybe_intermediate_summary()

    # ── Public API ────────────────────────────────────────────────────────

    def start(self):
        print(f"[Pipeline] Starting meeting: '{self.title}'")
        self.meeting_id         = create_meeting(self.title)
        self._last_summary_time = time.time()
        self._running           = True

        self.recorder.start()
        self._thread = threading.Thread(target=self._recording_loop, daemon=True)
        self._thread.start()
        print(f"[Pipeline] Recording... (meeting_id={self.meeting_id})")

    def stop(self) -> str:
        print("[Pipeline] Stopping recording ...")
        self._running = False
        self.recorder.stop()
        self._thread.join(timeout=60)

        end_meeting(self.meeting_id)

        # Final MoM
        transcripts  = get_all_transcripts(self.meeting_id)
        inter_rows   = get_summaries(self.meeting_id)
        inter_texts  = [r["content"] for r in inter_rows]
        combined     = "\n".join(transcripts)

        meeting_row = get_meeting(self.meeting_id)
        started_at = meeting_row["started_at"] if meeting_row else time.time()
        date_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at))

        print("[Pipeline] Generating final Minutes of Meeting ...")
        mom = self.summarizer.final_mom(
            combined_transcript=combined,
            intermediate_summaries=inter_texts,
            title=self.title,
            meeting_id=self.meeting_id,
            date_time=date_time_str
        )
        save_summary(self.meeting_id, "final", mom)

        # Generate MD and HTML documents
        try:
            meeting_row = get_meeting(self.meeting_id)
            started_at = meeting_row["started_at"] if meeting_row else time.time()
            txt_path, html_path, docx_path = generate_minutes_documents(
                self.meeting_id, self.title, started_at, mom
            )
            self.generated_docs = [txt_path, html_path, docx_path]
        except Exception as e:
            print(f"[Pipeline] Error generating MoM documents: {e}")
            self.generated_docs = []

        print(f"\n{'='*60}\nFINAL MINUTES OF MEETING\n{'='*60}\n{mom}\n{'='*60}")
        try:
            print("[Pipeline] Speaking final Minutes of Meeting ...")
            self.tts.speak(mom)
        except Exception as e:
            print(f"[TTS] Could not speak MoM: {e}")

        return mom