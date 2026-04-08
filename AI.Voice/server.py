import logging
import logging.handlers
import os
from flask import Flask, request, Response, jsonify
from pipeline import PiperPipeline
from config import HOST, PORT

log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

logger.info("Inizializzazione Piper TTS pipeline...")
pipeline = PiperPipeline()
logger.info("Pipeline pronta. Server in avvio...")


@app.post("/speak")
def speak():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Il campo 'text' è obbligatorio."}), 400

    logger.info(f"Sintesi: {text!r}")
    try:
        audio = pipeline.synthesize(text)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error("Errore durante la sintesi:\n" + tb)
        return jsonify({"error": str(e), "traceback": tb}), 500

    return Response(audio, mimetype="audio/wav")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, threaded=False)
