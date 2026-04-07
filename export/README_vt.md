# BMO Voice Pipeline

Pipeline TTS per il progetto BMO: converte testo → voce BMO usando Piper TTS + RVC.

---

## Struttura

```
BMO_P/
├── inference/          ← gira sul BE (Linux)
│   ├── config.py       ← impostazioni (pitch, porte, path)
│   ├── pipeline.py     ← classe BMOVoicePipeline
│   ├── server.py       ← API HTTP Flask
│   ├── download_models.py
│   └── requirements.txt
└── training/           ← gira sulla macchina Windows
    ├── prepare_dataset.py
    ├── start_training.bat
    └── requirements_train.txt
```

---

## Setup Inference (Linux — BE)

### 1. Crea venv e installa dipendenze

```bash
cd inference/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Scarica modello Piper

```bash
python download_models.py
```

### 3. Scarica modello RVC BMO (manuale)

Vai su: https://voice-models.com/model/1KbUSXbX4ee
Scarica `.pth` e `.index` → mettili in `inference/models/rvc/`
Rinominali `bmo.pth` e `bmo.index`

### 4. Avvia il server

```bash
python server.py
```

Il server gira su `http://0.0.0.0:5050`

---

## Chiamata dal BE

```python
import requests

r = requests.post("http://localhost:5050/speak", json={"text": "Hello! I am BMO!"})
with open("risposta.wav", "wb") as f:
    f.write(r.content)
```

---

## Regolazione qualità / latenza

In `config.py`:

| Parametro | Default | Note |
|---|---|---|
| `RVC_PITCH_SHIFT` | 4 | Alza/abbassa la voce (prova 3–6) |
| `f0_method` in pipeline.py | `rmvpe` | Cambia in `pm` per meno latenza |

---

## Setup Training (Windows — solo se vuoi migliorare il modello)

> Salta questa sezione se il modello da voice-models.com ti basta.

### 1. Installa RVC WebUI

```bat
git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git rvc-webui
cd rvc-webui
pip install -r requirements.txt
```

Scarica i pretrained model da: https://huggingface.co/lj1995/VoiceConversionWebUI
Metti `f0G40k.pth` e `f0D40k.pth` in `rvc-webui/pretrained_v2/`

### 2. Prepara il dataset

```bat
python prepare_dataset.py --input C:\path\to\bmo_clips\ --output .\dataset\bmo\
```

Consigliato: 10+ minuti di audio BMO pulito (no musica, no sovrapposizioni).

### 3. Avvia il training

```bat
start_training.bat
```

Durata stimata con GPU mid-range: ~30-60 minuti per 150 epoche.

### 4. Usa il modello addestrato

Copia `rvc-webui/logs/bmo_finetuned/bmo_finetuned_e150_s*.pth`
in `inference/models/rvc/bmo.pth` (sovrascrive il precedente).

---

## Note architettura

```
[BE: risposta LLM] → POST /speak → [Piper TTS] → [RVC BMO] → WAV → [Robot: playback]
```

- Piper e RVC girano sul BE, il robot riceve solo audio
- I modelli vengono caricati una volta all'avvio → latenza solo sulla prima chiamata
