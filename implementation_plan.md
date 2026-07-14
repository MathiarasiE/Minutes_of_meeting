# Implementation Plan - Automatic Speaker Enrollment & Diarization

Implement dynamic speaker enrollment during meetings by extracting speaker embeddings at the segment level and indexing speaker profiles. This enables Minutes of Meeting documents to distinguish speakers cleanly as `[Speaker 1]`, `[Speaker 2]`, etc.

## User Review Required

> [!IMPORTANT]
> **Dependency Install:** This implementation adds the `sherpa-onnx` package to the system dependencies. `sherpa-onnx` contains lightweight precompiled ONNX runtimes for Windows, removing the need for PyTorch, CUDA, or C++ compile configurations.
>
> **Model Auto-Download:** On the first run, the system will download the pre-trained English speaker recognition model `wespeaker_en_voxceleb_resnet34.onnx` (~90MB) from the Next-Gen Kaldi GitHub release server.
>
> **Robust Fallback:** If `sherpa-onnx` is missing or fails to initialize, the pipeline gracefully falls back to labeling all segments under `Speaker 1` (or using raw transcription segments) to prevent the transcription system from crashing.

## Open Questions

None at this stage. The proposed threshold of `0.6` is the standard recommended setting for speaker embedding cosine-similarity verification using the Wespeaker ResNet34 model.

---

## Proposed Changes

### Configuration Layer

#### [MODIFY] [config.py](file:///e:/Meet/config.py)
* Add configuration defaults for speaker embedding models:
  * `SPEAKER_MODEL`: Default path to `models/wespeaker_en_voxceleb_resnet34.onnx`.
  * `SPEAKER_THRESHOLD`: Default verification similarity score threshold (`0.6`).

#### [MODIFY] [.env](file:///e:/Meet/.env)
* Append default speaker configuration settings:
  ```env
  SPEAKER_MODEL=models/wespeaker_en_voxceleb_resnet34.onnx
  SPEAKER_THRESHOLD=0.6
  ```

---

### Speaker Recognition Layer

#### [NEW] [speaker_identifier.py](file:///e:/Meet/speaker_identifier.py)
* Create a dedicated class `SpeakerIdentifier` wrapping the `sherpa-onnx` embedding extractor and manager APIs.
* Implement verification checks to download the `.onnx` model automatically on first startup.
* Add fallback behavior so that any failures in imports/loading are caught, disabling diarization rather than crashing the system.
* Provide an `identify_speaker(audio_samples, sample_rate)` method to perform dynamic lookup and enrollment (i.e. generating `Speaker X` profiles on mismatch).

---

### Transcription & Recording Pipeline

#### [MODIFY] [transcriber.py](file:///e:/Meet/transcriber.py)
* Add a `transcribe_segments(audio_path)` method to return individual segment objects (`Segment`) containing text along with `start` and `end` times relative to the WAV file.

#### [MODIFY] [pipeline.py](file:///e:/Meet/pipeline.py)
* Initialize `SpeakerIdentifier` upon pipeline construction.
* In `_process_chunk(audio_chunk)`:
  1. Retrieve raw transcript segments using `transcribe_segments()`.
  2. Load the chunk's WAV audio.
  3. Slice the audio array for each segment timeline.
  4. Query the `SpeakerIdentifier` with the segment slice.
  5. Prepend the recognized speaker ID label (e.g. `[Speaker 1]: text...`) to each segment.
  6. Reconstruct the final chunk transcript with line breaks separating speakers.

---

### Dependency Settings

#### [MODIFY] [requirements.txt](file:///e:/Meet/requirements.txt)
* Append the new package dependency:
  ```txt
  sherpa-onnx>=1.8.0
  ```

---

## Verification Plan

### Automated Tests
We will write a scratch test script under `scratch/test_diarizer.py` that mocks audio chunks and processes them through the diarization pipeline, confirming:
- The model downloads and loads successfully.
- Subsequent segments of the same simulated voice register as the same speaker.
- Two distinct voice clips create different speaker profiles.

### Manual Verification
1. Run `python main.py record "Speaker Test"`.
2. Speak clearly, alternate with another speaker, and verify that the console logs show `[SpeakerIdentifier] No match found. Registering Speaker 1` and `Registering Speaker 2`.
3. Stop the meeting using `Ctrl+C` and check the generated final minutes files (both `.txt` and `.html`) to ensure transcripts are labeled with speaker identifiers (e.g. `[Speaker 1]`, `[Speaker 2]`).
