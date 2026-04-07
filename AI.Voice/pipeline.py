import io
import os
import wave
import tempfile
import logging

from piper.voice import PiperVoice
from rvc_python.infer import RVCInference

from config import (
    RVC_MODEL_PATH, RVC_INDEX_PATH, RVC_PITCH_SHIFT, RVC_F0_METHOD,
    PIPER_MODEL_DIR, PIPER_VOICE, DEVICE,
)

logger = logging.getLogger(__name__)


class BMOVoicePipeline:
    def __init__(self):
        logger.info("Caricamento Piper TTS...")
        model_path = os.path.join(PIPER_MODEL_DIR, f"{PIPER_VOICE}.onnx")
        config_path = os.path.join(PIPER_MODEL_DIR, f"{PIPER_VOICE}.onnx.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Modello Piper non trovato: {model_path}\n"
                "Esegui prima: python download_models.py"
            )

        self.tts = PiperVoice.load(model_path, config_path=config_path)
        logger.info("Piper TTS caricato.")

        logger.info(f"Caricamento RVC (device={DEVICE})...")
        self.rvc = RVCInference(device=DEVICE)
        self.rvc.f0up_key = RVC_PITCH_SHIFT
        self.rvc.f0method = RVC_F0_METHOD
        self.rvc.load_model(RVC_MODEL_PATH, index_path=RVC_INDEX_PATH)
        logger.info("RVC caricato.")

    def synthesize(self, text: str) -> bytes:
        """Testo → WAV con voce BMO."""
        tts_path = None
        rvc_path = None
        try:
            # Step 1: Piper TTS → BytesIO (evita problemi con file temp su Windows)
            logger.info("Step 1: Piper TTS synthesis...")
            buf = io.BytesIO()
            wav_out = wave.open(buf, "wb")
            self.tts.synthesize_wav(text, wav_out)
            wav_out.close()
            tts_wav_data = buf.getvalue()
            logger.info(f"Step 1 OK: {len(tts_wav_data)} bytes TTS WAV")

            # Step 2: scrivi su file temp per RVC
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(tts_wav_data)
                tts_path = f.name

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                rvc_path = f.name

            logger.info("Step 2: RVC inference...")
            self.rvc.infer_file(tts_path, rvc_path)

            with open(rvc_path, "rb") as f:
                result = f.read()
            logger.info(f"Step 2 OK: {len(result)} bytes RVC WAV")
            return result

        finally:
            if tts_path and os.path.exists(tts_path):
                os.unlink(tts_path)
            if rvc_path and os.path.exists(rvc_path):
                os.unlink(rvc_path)
