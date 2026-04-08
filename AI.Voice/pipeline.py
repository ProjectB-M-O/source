"""
pipeline.py — Sintesi vocale Piper TTS pura.
Cerca il primo .onnx nella cartella models/bmo/ e lo usa come modello.
"""
import io
import logging
import time
import wave
from pathlib import Path

from piper.voice import PiperVoice

from config import PIPER_MODEL_DIR, AUDIO_OUT_DIR, AUDIO_MAX_FILES

logger = logging.getLogger(__name__)


def _find_model() -> tuple[Path, Path]:
    """Trova il primo .onnx e il corrispondente .onnx.json in models/bmo/."""
    onnx_files = list(PIPER_MODEL_DIR.glob("*.onnx"))
    if not onnx_files:
        raise FileNotFoundError(
            f"Nessun modello .onnx trovato in {PIPER_MODEL_DIR}. "
            "Copia il tuo modello Piper (model.onnx + model.onnx.json) nella cartella."
        )
    model_path = onnx_files[0]
    config_path = Path(str(model_path) + ".json")
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config Piper mancante: {config_path}. "
            "Assicurati che il file .onnx.json sia nella stessa cartella del modello."
        )
    return model_path, config_path


def _cleanup_audio_out():
    """Mantiene al massimo AUDIO_MAX_FILES file in audio_out/, rimuove i più vecchi."""
    files = sorted(AUDIO_OUT_DIR.glob("*.wav"), key=lambda f: f.stat().st_mtime)
    to_delete = len(files) - AUDIO_MAX_FILES
    if to_delete > 0:
        for f in files[:to_delete]:
            try:
                f.unlink()
                logger.info(f"Audio rimosso (cleanup): {f.name}")
            except Exception as e:
                logger.warning(f"Impossibile rimuovere {f.name}: {e}")


class PiperPipeline:
    def __init__(self):
        model_path, config_path = _find_model()
        logger.info(f"Caricamento modello Piper: {model_path.name}")
        self.voice = PiperVoice.load(str(model_path), config_path=str(config_path))
        logger.info("Modello Piper caricato.")

    def synthesize(self, text: str) -> bytes:
        """Sintetizza testo → WAV bytes, salva in audio_out/."""
        _cleanup_audio_out()

        buf = io.BytesIO()
        wav_out = wave.open(buf, "wb")
        self.voice.synthesize_wav(text, wav_out)
        wav_out.close()
        wav_bytes = buf.getvalue()

        # Salva su disco
        filename = f"audio_{int(time.time() * 1000)}.wav"
        out_path = AUDIO_OUT_DIR / filename
        out_path.write_bytes(wav_bytes)
        logger.info(f"Audio salvato: {filename} ({len(wav_bytes)} bytes)")

        return wav_bytes
