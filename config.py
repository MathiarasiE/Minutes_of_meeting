import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        os.environ.setdefault(key, value)


def _env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.lower() in ("1", "true", "yes", "on")


def _env_csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _resolve_path(value: str) -> str:
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path)


_load_env_file(ENV_PATH)

DB_PATH = _resolve_path(_env_str("DB_PATH", "meetings.db"))
AUDIO_DIR = _resolve_path(_env_str("AUDIO_DIR", "audio_chunks"))
MINUTES_DIR = _resolve_path(_env_str("MINUTES_DIR", "minutes"))
WHISPER_MODEL = _env_str("WHISPER_MODEL", "tiny")
QWEN_MODEL = _resolve_path(_env_str("QWEN_MODEL", "models/qwen2.5-1.5b-instruct.gguf"))

SAMPLE_RATE = _env_int("SAMPLE_RATE", 16000)
CHANNELS = _env_int("CHANNELS", 1)
CHUNK_SECONDS = _env_int("CHUNK_SECONDS", 30)
CHUNK_SAMPLES = SAMPLE_RATE * CHUNK_SECONDS

WHISPER_DEVICE = _env_str("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = _env_str("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_TASK = _env_str("WHISPER_TASK", "transcribe")
WHISPER_LANGUAGE = _env_str("WHISPER_LANGUAGE", "") or None
AUDIO_GAIN = _env_float("AUDIO_GAIN", 1.0)
VAD_THRESHOLD = _env_float("VAD_THRESHOLD", 0.5)

INTERMEDIATE_SUMMARY_EVERY = _env_int("INTERMEDIATE_SUMMARY_EVERY", 300)
MAX_TOKENS_SUMMARY = _env_int("MAX_TOKENS_SUMMARY", 512)
MAX_TOKENS_MOM = _env_int("MAX_TOKENS_MOM", 1024)

LLAMA_N_CTX = _env_int("LLAMA_N_CTX", 2048)
LLAMA_N_THREADS = _env_int("LLAMA_N_THREADS", 4)

USE_OLLAMA = _env_bool("USE_OLLAMA", True)
OLLAMA_URL = _env_str("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = _env_str("OLLAMA_MODEL", "qwen2.5:1.5b")

VOICE_TRIGGER_WINDOW_SECONDS = _env_float("VOICE_TRIGGER_WINDOW_SECONDS", 3.0)
VOICE_TRIGGER_TIMEOUT_SECONDS = _env_float("VOICE_TRIGGER_TIMEOUT_SECONDS", 12.0)
WAKE_WORDS = _env_csv(
    "WAKE_WORDS",
    (
        "hey buddy",
        "ok buddy",
        "hello buddy",
        "buddy record",
    ),
)

SMTP_HOST = _env_str("SMTP_HOST")
SMTP_PORT = _env_int("SMTP_PORT", 587)
SMTP_USERNAME = _env_str("SMTP_USERNAME")
SMTP_PASSWORD = _env_str("SMTP_PASSWORD")
SMTP_SENDER = _env_str("SMTP_SENDER", SMTP_USERNAME)
SMTP_USE_TLS = _env_bool("SMTP_USE_TLS", True)
MEETING_SUMMARY_RECIPIENT = _env_str("MEETING_SUMMARY_RECIPIENT")

SPEAKER_MODEL = _resolve_path(_env_str("SPEAKER_MODEL", "models/wespeaker_en_voxceleb_resnet34.onnx"))
SPEAKER_THRESHOLD = _env_float("SPEAKER_THRESHOLD", 0.6)

HF_TOKEN = _env_str("HF_TOKEN")

