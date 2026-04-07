import os
import torch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# RVC model (già esportato)
RVC_MODEL_PATH = os.path.join(BASE_DIR, "../export/bmo_rvc_model/bmo_infer.pth")
RVC_INDEX_PATH = os.path.join(BASE_DIR, "../export/bmo_rvc_model/bmo.index")

# Pitch shift: alza la voce (BMO ha una voce acuta). Prova valori 3–6.
RVC_PITCH_SHIFT = 4

# Metodo f0: "rmvpe" = più qualità, "pm" = più veloce
RVC_F0_METHOD = "rmvpe"

# Piper TTS
PIPER_MODEL_DIR = os.path.join(BASE_DIR, "models", "piper")
PIPER_VOICE = "en_US-lessac-medium"

# Device: auto-detect CUDA, fallback CPU
DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"

# Server
HOST = "0.0.0.0"
PORT = 5050
