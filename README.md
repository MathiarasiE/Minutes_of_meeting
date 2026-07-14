# Meet

Local meeting recorder that captures microphone audio, transcribes it, stores transcripts in SQLite, and generates summaries and a final minutes-of-meeting report.

## Features

- Records audio from your microphone in chunks.
- Transcribes speech locally with `faster-whisper`.
- Stores meetings, transcripts, and summaries in `meetings.db`.
- Uses `llama-cpp-python` for intermediate and final meeting summaries.

## Requirements

- Python 3.11+
- A working microphone
- Optional: a local Qwen GGUF model at `models/qwen2.5-1.5b-instruct.gguf` for higher-quality summaries

On first run, `faster-whisper` downloads the Whisper model named `tiny` automatically.
If the Qwen model is missing, the app still runs and uses a simple fallback summary.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Runtime settings live in `.env`. Edit that file to change model names, audio settings, Ollama settings, wake words, or email settings.

## Usage

List stored meetings:

```powershell
python main.py list
```

Start recording a meeting:

```powershell
python main.py record "Team Sync"
```

Start in voice-trigger mode (default if no command is given):

```powershell
python main.py listen "Team Sync"
```

In voice-trigger mode, say a wake word (for example: `hey meet`, `ok meet`, or `meet`) and then say `start record`, `start recording`, `begin recording`, or similar phrasing.

Stop recording with `Ctrl+C`. The app will save the final minutes of meeting automatically.

Show a saved meeting:

```powershell
python main.py show 1
```

Send a saved meeting summary by email:

```powershell
python main.py email 1 person@example.com
```

To automatically email the final summary when a recording stops, set the default recipient and SMTP settings in `.env`:

```env
MEETING_SUMMARY_RECIPIENT=person@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_SENDER=your-email@gmail.com
```

## Project Layout

- `main.py` - CLI entrypoint
- `emailer.py` - SMTP email sending
- `pipeline.py` - recording, transcription, and summarization flow
- `audio_recorder.py` - microphone capture
- `chunker.py` - WAV chunk persistence
- `transcriber.py` - `faster-whisper` wrapper
- `summarizer.py` - local LLM summarization
- `database.py` - SQLite persistence
- `.env` - paths, model, audio, Ollama, wake word, and email settings
- `config.py` - `.env` loader and typed config values

## Notes

- Audio chunks are written to `audio_chunks/`.
- Meeting data is stored in `meetings.db`.
- The Whisper model name is configured in `.env`.
