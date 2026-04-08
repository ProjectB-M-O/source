import os
import json
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# Modello Piper custom (fornito dall'utente)
PIPER_MODEL_DIR = BASE_DIR / "models" / "bmo"

# Cartella output audio (rolling cleanup)
AUDIO_OUT_DIR = BASE_DIR / "audio_out"
AUDIO_OUT_DIR.mkdir(exist_ok=True)


def _load_max_files() -> int:
    cfg_path = BASE_DIR / ".." / "Bmo.Api" / "bmo_config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return int(cfg.get("services", {}).get("ai_voice", {}).get("audio_max_files", 10))
    except Exception:
        return 10


AUDIO_MAX_FILES = _load_max_files()

# Server
HOST = "0.0.0.0"
PORT = 5050
