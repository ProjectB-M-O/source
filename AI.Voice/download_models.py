"""
Scarica il modello Piper TTS (en_US-lessac-medium) da HuggingFace.
Esegui una volta sola prima di avviare il server.
"""
import os
import urllib.request

PIPER_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "piper")
os.makedirs(PIPER_MODEL_DIR, exist_ok=True)

BASE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
    "/en/en_US/lessac/medium"
)
FILES = [
    "en_US-lessac-medium.onnx",
    "en_US-lessac-medium.onnx.json",
]


def download():
    for filename in FILES:
        dest = os.path.join(PIPER_MODEL_DIR, filename)
        if os.path.exists(dest):
            print(f"  Già presente: {filename}")
            continue
        url = f"{BASE_URL}/{filename}"
        print(f"  Download {filename} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"  OK {filename}")


if __name__ == "__main__":
    print("Scaricamento modelli Piper TTS...")
    download()
    print("Fatto.")
