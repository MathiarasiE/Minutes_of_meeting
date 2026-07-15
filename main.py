import sys
import time
import signal
import os
import re
import tempfile
import warnings

# Suppress UserWarnings (such as torchcodec/ffmpeg loading tracebacks from pyannote)
warnings.filterwarnings("ignore", category=UserWarning)

import sounddevice as sd
import soundfile as sf

from database  import init_db, list_meetings, get_all_transcripts, get_summaries, get_meeting
from emailer import send_email
from doc_generator import markdown_to_html
import html
from pipeline  import MeetingPipeline
from transcriber import WhisperTranscriber
from tts import TTS
from config import (
    MEETING_SUMMARY_RECIPIENT,
    SAMPLE_RATE,
    CHANNELS,
    VOICE_TRIGGER_WINDOW_SECONDS,
    VOICE_TRIGGER_TIMEOUT_SECONDS,
    WAKE_WORDS,
)


pipeline: MeetingPipeline | None = None


START_RECORD_PHRASES = (
    "start record",
    "start recording",
    "begin recording",
    "begin record",
    "record now",
    "start meeting",
    "begin meeting",
)


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _has_start_record_intent(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return False

    if any(phrase in normalized for phrase in START_RECORD_PHRASES):
        return True

    start_verbs = ("start", "begin", "commence")
    record_terms = ("record", "recording", "meeting", "capture")
    return (
        any(verb in normalized for verb in start_verbs)
        and any(term in normalized for term in record_terms)
    )


def _send_summary_text(meeting_id: int, summary: str, recipient: str, attachments: list[str] = None):
    meeting = get_meeting(meeting_id)
    title = meeting["title"] if meeting else f"Meeting {meeting_id}"
    started_at = meeting["started_at"] if meeting else time.time()
    date_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at))
    
    subject = f"Meeting Summary: {title}"
    body = f"K S RANGASAMY COLLEGE OF TECHNOLOGY - TRAIT CENTER\n\nMINUTES OF MEETING: {title}\nDate: {date_time_str}\n\n{summary}"
    
    parsed_content = markdown_to_html(summary)
    
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        .email-content h2 {{
            color: #1e3a8a !important;
            font-size: 16px !important;
            font-weight: 600 !important;
            margin-top: 24px !important;
            margin-bottom: 12px !important;
            border-bottom: 2px solid #e2e8f0 !important;
            padding-bottom: 6px !important;
        }}
        .email-content h3 {{
            color: #1e3a8a !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            margin-top: 20px !important;
            margin-bottom: 10px !important;
        }}
        .email-content p {{
            margin: 0 0 12px 0 !important;
            color: #334155 !important;
            line-height: 1.6 !important;
        }}
        .email-content ul, .email-content ol {{
            margin: 0 0 16px 0 !important;
            padding-left: 20px !important;
            color: #334155 !important;
        }}
        .email-content li {{
            margin-bottom: 6px !important;
            line-height: 1.5 !important;
        }}
        .email-content .task-list {{
            list-style-type: none !important;
            padding-left: 0 !important;
        }}
        .email-content .task-item {{
            margin-bottom: 8px !important;
            padding: 8px 12px !important;
            border-radius: 4px !important;
            background-color: #f8fafc !important;
            border: 1px solid #e2e8f0 !important;
            line-height: 1.4 !important;
            display: block !important;
        }}
        .email-content .checkbox {{
            display: inline-block !important;
            width: 14px !important;
            height: 14px !important;
            border: 2px solid #cbd5e1 !important;
            border-radius: 3px !important;
            background-color: #ffffff !important;
            margin-right: 8px !important;
            vertical-align: middle !important;
            text-align: center !important;
        }}
        .email-content .checkbox.checked {{
            background-color: #1e3a8a !important;
            border-color: #1e3a8a !important;
            color: #ffffff !important;
            font-size: 10px !important;
            font-weight: bold !important;
            line-height: 14px !important;
        }}
        .email-content .task-item.checked {{
            text-decoration: line-through !important;
            color: #64748b !important;
            background-color: #f1f5f9 !important;
        }}
    </style>
    <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">
</head>
<body style="margin: 0; padding: 20px 0; background-color: #f8fafc; font-family: 'Lora', Georgia, serif; width: 100% !important;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc;">
        <tr>
            <td align="center" style="padding: 20px 10px;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.025); border: 1px solid #e2e8f0; border-top: 6px solid #1e3a8a; overflow: hidden; border-collapse: collapse;">
                    <!-- HEADER -->
                    <tr>
                        <td style="background-color: #ffffff; padding: 32px 32px 24px 32px; text-align: left; border-bottom: 2px solid #e2e8f0;">
                            <div style="font-size: 15px; font-weight: 800; color: #1e3a8a; letter-spacing: 0.03em; text-transform: uppercase; margin-bottom: 4px; font-family: inherit;">
                                K S RANGASAMY COLLEGE OF TECHNOLOGY
                            </div>
                            <div style="font-size: 12px; font-weight: 700; color: #64748b; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 20px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; font-family: inherit;">
                                TRAIT CENTER
                            </div>
                            <span style="display: inline-block; background-color: #eff6ff; color: #1e3a8a; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px;">
                                Meeting Summary
                            </span>
                            <h1 style="margin: 0; font-size: 22px; font-weight: 700; color: #0f172a; letter-spacing: -0.025em; line-height: 1.3; font-family: inherit;">
                                {html.escape(title)}
                            </h1>
                        </td>
                    </tr>
                    <!-- METADATA -->
                    <tr>
                        <td style="padding: 16px 32px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td width="50%" style="font-size: 12px; color: #64748b; font-family: inherit;">
                                        <strong style="color: #0f172a;">Meeting ID:</strong> #{meeting_id}
                                    </td>
                                    <td width="50%" align="right" style="font-size: 12px; color: #64748b; font-family: inherit;">
                                        <strong style="color: #0f172a;">Date & Time:</strong> {date_time_str}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- CONTENT -->
                    <tr>
                        <td style="padding: 32px; font-size: 15px; line-height: 1.6; color: #334155; font-family: inherit;">
                            <div class="email-content" style="margin: 0;">
                                {parsed_content}
                            </div>
                        </td>
                    </tr>
                    <!-- FOOTER -->
                    <tr>
                        <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 24px; text-align: center; font-size: 12px; color: #64748b; line-height: 1.5; font-family: inherit;">
                            Generated automatically by Meet Meeting Assistant.<br>
                            <strong style="color: #334155;">K S Rangasamy College of Technology — TRAIT Center</strong>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
    
    if attachments:
        filtered = [a for a in attachments if a.endswith('.docx')]
        attachments.clear()
        attachments.extend(filtered)
        
    send_email(recipient, subject, body, html_body=html_body, attachments=attachments)


def _capture_phrase_to_text(transcriber: WhisperTranscriber) -> str:
    from config import AUDIO_GAIN
    frames = int(SAMPLE_RATE * VOICE_TRIGGER_WINDOW_SECONDS)
    audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
    sd.wait()

    # Scale raw recorded voice trigger audio digitally by AUDIO_GAIN
    audio_scaled = audio * AUDIO_GAIN

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        sf.write(tmp_path, audio_scaled, SAMPLE_RATE)
        return transcriber.transcribe(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def signal_handler(sig, frame):
    print("\n[Main] Interrupt received. Stopping ...")
    if pipeline:
        summary = pipeline.stop()
        if MEETING_SUMMARY_RECIPIENT:
            try:
                attachments = getattr(pipeline, "generated_docs", None)
                _send_summary_text(pipeline.meeting_id, summary, MEETING_SUMMARY_RECIPIENT, attachments=attachments)
                print(f"[Email] Meeting summary sent to {MEETING_SUMMARY_RECIPIENT}.")
                if attachments:
                    print(f"[Email] Attached files: {', '.join(os.path.basename(a) for a in attachments)}")
            except Exception as e:
                print(f"[Email] Error: {e}")
    sys.exit(0)


def cmd_record(title: str):
    global pipeline
    signal.signal(signal.SIGINT, signal_handler)

    pipeline = MeetingPipeline(title=title)
    pipeline.start()

    print("Recording... Press Ctrl+C to stop and generate MoM.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        summary = pipeline.stop()
        if MEETING_SUMMARY_RECIPIENT:
            try:
                attachments = getattr(pipeline, "generated_docs", None)
                _send_summary_text(pipeline.meeting_id, summary, MEETING_SUMMARY_RECIPIENT, attachments=attachments)
                print(f"[Email] Meeting summary sent to {MEETING_SUMMARY_RECIPIENT}.")
                if attachments:
                    print(f"[Email] Attached files: {', '.join(os.path.basename(a) for a in attachments)}")
            except Exception as e:
                print(f"[Email] Error: {e}")


def cmd_listen(title: str):
    print("[Voice] Listening for wake word...")
    print(f"[Voice] Wake words: {', '.join(WAKE_WORDS)}")
    print("[Voice] Say wake word then say 'start record' (or similar). Press Ctrl+C to exit.")

    transcriber = WhisperTranscriber()
    armed_until = 0.0

    try:
        while True:
            transcript = _capture_phrase_to_text(transcriber)
            normalized = _normalize_text(transcript)
            if not normalized:
                continue

            print(f"[Voice] Heard: {normalized}")
            now = time.time()

            wake_hit = any(_normalize_text(wake) in normalized for wake in WAKE_WORDS)
            start_hit = _has_start_record_intent(normalized)

            if wake_hit and start_hit:
                print("[Voice] Wake word + start command detected. Starting recording...")
                cmd_record(title)
                return

            if wake_hit:
                armed_until = now + VOICE_TRIGGER_TIMEOUT_SECONDS
                print("[Voice] Wake word detected. Waiting for start-record command...")
                continue

            if now <= armed_until and start_hit:
                print("[Voice] Start command detected. Starting recording...")
                cmd_record(title)
                return
    except KeyboardInterrupt:
        print("\n[Voice] Exiting voice listener.")


def cmd_list():
    rows = list_meetings()
    if not rows:
        print("No meetings found.")
        return
    print(f"\n{'ID':<5} {'Title':<30} {'Started':<25} {'Ended'}")
    print("-" * 75)
    for r in rows:
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["started_at"]))
        ended   = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["ended_at"])) if r["ended_at"] else "ongoing"
        print(f"{r['id']:<5} {r['title']:<30} {started:<25} {ended}")


def cmd_show(meeting_id: int):
    transcripts = get_all_transcripts(meeting_id)
    summaries   = get_summaries(meeting_id)

    print(f"\n=== Transcripts for meeting {meeting_id} ===")
    for i, t in enumerate(transcripts):
        print(f"\n[Chunk {i}]\n{t}")

    print(f"\n=== Summaries for meeting {meeting_id} ===")
    for s in summaries:
        ts = time.strftime("%H:%M:%S", time.localtime(s["created_at"]))
        print(f"\n[{s['kind'].upper()} @ {ts}]\n{s['content']}")


def _get_preferred_summary(meeting_id: int) -> str | None:
    summaries = get_summaries(meeting_id)
    if not summaries:
        return None

    for s in summaries:
        if s["kind"] == "final":
            return s["content"]

    return "\n\n".join(r["content"] for r in summaries)


def cmd_speak(meeting_id: int):
    final = _get_preferred_summary(meeting_id)
    if final is None:
        print("No summaries found for that meeting.")
        return

    try:
        tts = TTS()
        print("Speaking meeting summary...")
        tts.speak(final)
    except Exception as e:
        print(f"[TTS] Error: {e}")


def cmd_email(meeting_id: int, recipient: str | None = None):
    recipient = recipient or MEETING_SUMMARY_RECIPIENT
    if not recipient:
        print("Recipient email missing. Pass it as an argument or set MEETING_SUMMARY_RECIPIENT.")
        return

    summary = _get_preferred_summary(meeting_id)
    if summary is None:
        print("No summaries found for that meeting.")
        return

    attachments = []
    try:
        import glob
        from config import MINUTES_DIR
        pattern = os.path.join(MINUTES_DIR, f"Minutes_of_Meeting_ID_{meeting_id}_*")
        attachments = glob.glob(pattern)
    except Exception as e:
        print(f"[Email] Warning, could not search for attachments: {e}")

    try:
        _send_summary_text(meeting_id, summary, recipient, attachments=attachments)
        print(f"Meeting summary sent to {recipient}.")
        if attachments:
            print(f"Attached files: {', '.join(os.path.basename(a) for a in attachments)}")
    except Exception as e:
        print(f"[Email] Error: {e}")


def print_help():
    print("""
Usage:
    python main.py record [title]  Start recording a meeting
    python main.py listen [title]  Wait for wake word then start recording by voice
    python main.py list            List all past meetings
    python main.py show <id>       Show transcripts & summaries for a meeting
    python main.py speak <id>      Speak final summary for a meeting
    python main.py email <id> [to] Send final summary to an email address
    python main.py help            Show this help
""")


if __name__ == "__main__":
    init_db()

    args = sys.argv[1:]
    if not args:
        title = f"Meeting {time.strftime('%Y-%m-%d %H:%M')}"
        cmd_listen(title)
    elif args[0] == "help":
        print_help()
    elif args[0] == "record":
        title = " ".join(args[1:]) or f"Meeting {time.strftime('%Y-%m-%d %H:%M')}"
        cmd_record(title)
    elif args[0] == "listen":
        title = " ".join(args[1:]) or f"Meeting {time.strftime('%Y-%m-%d %H:%M')}"
        cmd_listen(title)
    elif args[0] == "list":
        cmd_list()
    elif args[0] == "show" and len(args) > 1:
        cmd_show(int(args[1]))
    elif args[0] == "speak" and len(args) > 1:
        cmd_speak(int(args[1]))
    elif args[0] == "email" and len(args) > 1:
        recipient = args[2] if len(args) > 2 else None
        cmd_email(int(args[1]), recipient)
    else:
        print_help()
