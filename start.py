#!/usr/bin/env python3
"""
B.M.O. Project Launcher
Avvia tutti i servizi in terminali separati.
Supporta Windows, Linux e macOS.
"""

import os
import sys
import json
import platform
import subprocess
import time
import webbrowser
import shutil
import socket
import urllib.request
import zipfile
import tarfile
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.absolute()
CONFIG_PATH = ROOT / "Bmo.Api" / "bmo_config.json"
ENV_PATH    = ROOT / "AI.Brain" / ".env"
DASH_ENV    = ROOT / "dashboard-bmo" / ".env.local"
DOTNET_DIR  = ROOT / ".dotnet"   # installazione .NET SDK locale
NODE_DIR    = ROOT / ".node"     # installazione Node.js locale
VOICE_DIR   = ROOT / "AI.Voice"  # server TTS (Flask + Piper + RVC)

SYSTEM = platform.system()  # "Windows" | "Linux" | "Darwin"

# ─── ANSI colors (skip on plain Windows console) ─────────────────────────────
_use_color = (
    SYSTEM != "Windows"
    or os.environ.get("ANSICON")
    or os.environ.get("WT_SESSION")
    or os.environ.get("TERM_PROGRAM")
)
CR  = "\033[0m"  if _use_color else ""
CY  = "\033[96m" if _use_color else ""   # cyan
CG  = "\033[92m" if _use_color else ""   # green
CYL = "\033[93m" if _use_color else ""   # yellow
CR2 = "\033[91m" if _use_color else ""   # red
CB  = "\033[1m"  if _use_color else ""   # bold


# ─── Header ──────────────────────────────────────────────────────────────────
def print_header():
    print(f"""
{CY}{CB}
  ██████╗     ███╗   ███╗     ██████╗
  ██╔══██╗    ████╗ ████║    ██╔═══██╗
  ██████╔╝    ██╔████╔██║    ██║   ██║
  ██╔══██╗    ██║╚██╔╝██║    ██║   ██║
  ██████╔╝██╗ ██║ ╚═╝ ██║██╗╚██████╔╝
  ╚═════╝ ╚═╝ ╚═╝     ╚═╝╚═╝ ╚═════╝
{CR}  {CB}Project Launcher{CR}  |  {SYSTEM}
""")


# ─── Dependency helpers ───────────────────────────────────────────────────────
def _step(msg: str): print(f"  {CY}»{CR} {msg}")
def _ok(msg: str):   print(f"  {CG}✓{CR} {msg}")
def _warn(msg: str): print(f"  {CYL}⚠{CR} {msg}")
def _err(msg: str):  print(f"  {CR2}✗{CR} {msg}")


# ─── Internet check ──────────────────────────────────────────────────────────
def _has_internet() -> bool:
    """Prova una connessione TCP a Google DNS (8.8.8.8:53) — rapido e affidabile."""
    try:
        socket.setdefaulttimeout(5)
        with socket.create_connection(("8.8.8.8", 53)):
            return True
    except OSError:
        return False


def _require_internet():
    """
    Controlla la connessione Internet.
    Se assente, stampa il messaggio di errore ed esce.
    Chiamata solo quando un download è effettivamente necessario.
    """
    _step("Verifica connessione Internet...")
    if _has_internet():
        _ok("Connessione Internet attiva")
    else:
        _err("Nessuna connessione Internet rilevata.")
        print(f"\n  {CR2}Alcune dipendenze mancano e devono essere scaricate.")
        print(f"  Connettiti a Internet e riavvia il launcher.{CR}\n")
        sys.exit(1)


# ─── Local tool paths ─────────────────────────────────────────────────────────
def _dotnet_local_exe() -> Path:
    return DOTNET_DIR / ("dotnet.exe" if SYSTEM == "Windows" else "dotnet")


def _node_local_exe() -> Path:
    if SYSTEM == "Windows":
        return NODE_DIR / "node.exe"
    return NODE_DIR / "bin" / "node"


def _npm_local_cmd() -> Path:
    if SYSTEM == "Windows":
        return NODE_DIR / "npm.cmd"
    return NODE_DIR / "bin" / "npm"


# ─── 1. Python version ───────────────────────────────────────────────────────
def check_python_version():
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 10):
        _err(f"Python {major}.{minor} rilevato — richiesto ≥ 3.10")
        print(f"  Scarica Python da: https://www.python.org/downloads/")
        sys.exit(1)
    _ok(f"Python {major}.{minor}")


# ─── 2. Python venv + dipendenze ─────────────────────────────────────────────
def setup_python_venv():
    venv_dir = ROOT / "AI.Brain" / ".venv"
    req_file = ROOT / "AI.Brain" / "requirements.txt"

    if SYSTEM == "Windows":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
        py_exe  = venv_dir / "Scripts" / "python.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"
        py_exe  = venv_dir / "bin" / "python"

    # Crea il venv se non esiste
    if not venv_dir.exists():
        _step("Creazione virtual environment Python (AI.Brain/.venv)...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        _ok("Virtual environment creato")

    # Verifica se le dipendenze sono già installate
    probe = subprocess.run(
        [str(py_exe), "-c", "import fastapi"],
        capture_output=True
    )
    if probe.returncode != 0:
        _require_internet()
        _step("Installazione dipendenze Python (requirements.txt)...")
        subprocess.run(
            [str(pip_exe), "install", "-r", str(req_file)],
            check=True
        )
        _ok("Dipendenze Python installate")
    else:
        _ok("Dipendenze Python già installate")


# ─── 3. AI.Voice venv (opzionale) ────────────────────────────────────────────
def _voice_py_exe() -> Path:
    venv = VOICE_DIR / "venv"
    return venv / ("Scripts/python.exe" if SYSTEM == "Windows" else "bin/python")


def setup_voice_venv():
    """Crea il venv per AI.Voice e installa le dipendenze (flask + piper-tts)."""
    venv_dir = VOICE_DIR / "venv"
    req_file = VOICE_DIR / "requirements.txt"
    py_exe   = _voice_py_exe()

    if SYSTEM == "Windows":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"

    # Crea il venv se non esiste
    if not venv_dir.exists():
        _step("Creazione virtual environment AI.Voice...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        _ok("Virtual environment AI.Voice creato")

    # Controlla se le dipendenze sono già installate
    probe = subprocess.run(
        [str(py_exe), "-c", "import flask; import piper"],
        capture_output=True
    )
    if probe.returncode == 0:
        _ok("Dipendenze AI.Voice già installate")
    else:
        _require_internet()
        _step("Installazione dipendenze AI.Voice (flask + piper-tts)...")
        subprocess.run([str(pip_exe), "install", "-r", str(req_file)], check=True)
        _ok("Dipendenze AI.Voice installate")

    # Verifica modello Piper custom in models/bmo/
    bmo_model_dir = VOICE_DIR / "models" / "bmo"
    bmo_model_dir.mkdir(parents=True, exist_ok=True)
    onnx_files = list(bmo_model_dir.glob("*.onnx"))

    if not onnx_files:
        print(f"\n  {CR2}Nessun modello Piper trovato in AI.Voice/models/bmo/{CR}")
        print(f"  {CY}Copia i file del tuo modello addestrato:{CR}")
        print(f"    {CYL}  model.onnx{CR}       — il modello ONNX")
        print(f"    {CYL}  model.onnx.json{CR}  — la config Piper")
        print(f"\n  Il server AI.Voice non partirà senza questi file.\n")
        input(f"  {CG}Premi INVIO quando i file sono pronti...{CR} ")
        # Verifica di nuovo dopo il prompt
        onnx_files = list(bmo_model_dir.glob("*.onnx"))
        if not onnx_files:
            _warn("Modello ancora non trovato — il server TTS potrebbe non funzionare.")
        else:
            _ok(f"Modello Piper trovato: {onnx_files[0].name}")
    else:
        _ok(f"Modello Piper trovato: {onnx_files[0].name}")


def setup_voice_venv_if_enabled(config: dict):
    if config.get("services", {}).get("ai_voice", {}).get("enabled", False):
        print(f"\n{CB}── AI.Voice (TTS) ───────────────────────────────────────{CR}\n")
        setup_voice_venv()
        print()


# ─── 3. .NET SDK 10 ──────────────────────────────────────────────────────────
def check_dotnet() -> bool:
    """
    Verifica che .NET SDK ≥ 10 sia disponibile (locale o di sistema).
    Se mancante o troppo vecchio, installa localmente in .dotnet/.
    """
    # Prova prima l'eseguibile locale, poi quello di sistema
    candidates = []
    if _dotnet_local_exe().exists():
        candidates.append(str(_dotnet_local_exe()))
    if shutil.which("dotnet"):
        candidates.append("dotnet")

    for exe in candidates:
        result = subprocess.run([exe, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            ver = result.stdout.strip()
            major = int(ver.split(".")[0]) if ver.split(".")[0].isdigit() else 0
            if major >= 10:
                _ok(f".NET SDK {ver}")
                return True
            _warn(f".NET SDK {ver} trovato — richiesto ≥ 10, installo localmente...")
            break
    else:
        _step(".NET SDK non trovato — installazione locale in .dotnet/ ...")

    return _install_dotnet_local()


def _install_dotnet_local() -> bool:
    _require_internet()
    DOTNET_DIR.mkdir(exist_ok=True)

    if SYSTEM == "Windows":
        script = ROOT / "_dotnet-install.ps1"
        url    = "https://dot.net/v1/dotnet-install.ps1"
    else:
        script = ROOT / "_dotnet-install.sh"
        url    = "https://dot.net/v1/dotnet-install.sh"

    _step("Download script di installazione .NET...")
    try:
        urllib.request.urlretrieve(url, str(script))
    except Exception as e:
        _err(f"Download fallito: {e}")
        _err("Installa manualmente: https://dotnet.microsoft.com/download/dotnet/10.0")
        return False

    _step("Installazione .NET SDK 10 in .dotnet/ (prima volta: qualche minuto)...")
    try:
        if SYSTEM == "Windows":
            result = subprocess.run([
                "powershell", "-ExecutionPolicy", "Bypass",
                "-File", str(script),
                "-InstallDir", str(DOTNET_DIR),
                "-Channel", "10.0",
            ])
        else:
            os.chmod(str(script), 0o755)
            result = subprocess.run([
                "bash", str(script),
                "--install-dir", str(DOTNET_DIR),
                "--channel", "10.0",
            ])
    finally:
        script.unlink(missing_ok=True)  # pulizia script temporaneo

    if result.returncode != 0:
        _err("Installazione .NET fallita.")
        _err("Installa manualmente: https://dotnet.microsoft.com/download/dotnet/10.0")
        return False

    _ok(".NET SDK 10 installato in .dotnet/")
    return True


# ─── 4. Node.js ──────────────────────────────────────────────────────────────
def check_node() -> bool:
    """
    Verifica che Node.js ≥ 18 sia disponibile (locale o di sistema).
    Se mancante o troppo vecchio, installa la versione portable in .node/.
    """
    candidates = []
    if _node_local_exe().exists():
        candidates.append(str(_node_local_exe()))
    if shutil.which("node"):
        candidates.append("node")

    for exe in candidates:
        result = subprocess.run([exe, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            ver = result.stdout.strip().lstrip("v")
            major = int(ver.split(".")[0]) if ver.split(".")[0].isdigit() else 0
            if major >= 18:
                _ok(f"Node.js v{ver}")
                return True
            _warn(f"Node.js v{ver} trovato — richiesto ≥ 18, installo localmente...")
            break
    else:
        _step("Node.js non trovato — installazione portable in .node/ ...")

    return _install_node_local()


def _install_node_local() -> bool:
    _require_internet()
    NODE_VERSION = "22.14.0"  # LTS

    machine = platform.machine().lower()
    if SYSTEM == "Windows":
        arch  = "arm64" if "arm" in machine else "x64"
        fname = f"node-v{NODE_VERSION}-win-{arch}.zip"
        inner = f"node-v{NODE_VERSION}-win-{arch}"
        url   = f"https://nodejs.org/dist/v{NODE_VERSION}/{fname}"
    elif SYSTEM == "Darwin":
        arch  = "arm64" if "arm" in machine else "x64"
        fname = f"node-v{NODE_VERSION}-darwin-{arch}.tar.gz"
        inner = f"node-v{NODE_VERSION}-darwin-{arch}"
        url   = f"https://nodejs.org/dist/v{NODE_VERSION}/{fname}"
    else:
        arch  = "arm64" if ("aarch64" in machine or "arm" in machine) else "x64"
        fname = f"node-v{NODE_VERSION}-linux-{arch}.tar.xz"
        inner = f"node-v{NODE_VERSION}-linux-{arch}"
        url   = f"https://nodejs.org/dist/v{NODE_VERSION}/{fname}"

    archive = ROOT / fname
    _step(f"Download Node.js v{NODE_VERSION} ({arch})...")
    try:
        urllib.request.urlretrieve(url, str(archive))
    except Exception as e:
        _err(f"Download fallito: {e}")
        _err("Installa manualmente: https://nodejs.org/")
        return False

    _step("Estrazione Node.js in .node/ ...")
    try:
        if SYSTEM == "Windows":
            with zipfile.ZipFile(str(archive), "r") as zf:
                zf.extractall(str(ROOT))
        else:
            with tarfile.open(str(archive), "r:*") as tf:
                try:
                    tf.extractall(str(ROOT), filter="data")
                except TypeError:
                    tf.extractall(str(ROOT))  # Python < 3.12

        extracted = ROOT / inner
        if extracted.exists():
            if NODE_DIR.exists():
                shutil.rmtree(str(NODE_DIR))
            extracted.rename(NODE_DIR)
        else:
            _err("Cartella estratta non trovata.")
            return False
    except Exception as e:
        _err(f"Estrazione fallita: {e}")
        return False
    finally:
        archive.unlink(missing_ok=True)  # pulizia archivio temporaneo

    _ok(f"Node.js v{NODE_VERSION} installato in .node/")
    return True


# ─── 5. npm install dashboard ─────────────────────────────────────────────────
def setup_node_modules():
    nm  = ROOT / "dashboard-bmo" / "node_modules"
    pkg = ROOT / "dashboard-bmo" / "package.json"

    if not pkg.exists():
        _warn("dashboard-bmo/package.json non trovato — skip npm install")
        return

    if nm.exists() and any(nm.iterdir()):
        _ok("Dipendenze npm già installate")
        return

    _require_internet()
    _step("Installazione dipendenze npm del dashboard (prima volta: qualche minuto)...")
    npm = str(_npm_local_cmd()) if _npm_local_cmd().exists() else (
        "npm.cmd" if SYSTEM == "Windows" else "npm"
    )
    result = subprocess.run([npm, "install"], cwd=str(ROOT / "dashboard-bmo"))
    if result.returncode == 0:
        _ok("Dipendenze npm installate")
    else:
        _err("npm install fallito — il dashboard potrebbe non avviarsi correttamente")


# ─── Entry point dipendenze ───────────────────────────────────────────────────
def check_dependencies() -> dict:
    """
    Controlla e installa tutte le dipendenze necessarie.
    Ritorna {"dotnet": bool, "node": bool}.
    """
    print(f"\n{CB}── Verifica dipendenze ──────────────────────────────────{CR}\n")

    check_python_version()
    setup_python_venv()

    dotnet_ok = check_dotnet()
    if not dotnet_ok:
        _warn("Bmo.Api (.NET) non potrà avviarsi — installa .NET SDK 10 manualmente")
        print(f"  {CR2}  → https://dotnet.microsoft.com/download/dotnet/10.0{CR}")

    node_ok = check_node()
    if not node_ok:
        _warn("Dashboard (Node.js) non potrà avviarsi — installa Node.js manualmente")
        print(f"  {CR2}  → https://nodejs.org/{CR}")
    else:
        setup_node_modules()

    print()
    return {"dotnet": dotnet_ok, "node": node_ok}


# ─── Config I/O ──────────────────────────────────────────────────────────────
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(f"{CR2}ERRORE: {CONFIG_PATH} non trovato.{CR}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ─── .env I/O ────────────────────────────────────────────────────────────────
def load_env(path: Path) -> dict:
    env: dict = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip()
    return env


def save_env(path: Path, env: dict):
    with open(path, "w", encoding="utf-8") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")


# ─── Default service ports ────────────────────────────────────────────────────
_DEFAULT_SERVICES = {
    "ai_brain":  {"port": 8000},
    "bmo_api":   {"port": 5271},
    "dashboard": {"port": 3000},
    "ai_voice":  {"enabled": False, "port": 5050},
}


def ensure_services(config: dict) -> bool:
    """Aggiunge il blocco services se mancante. Ritorna True se modificato."""
    modified = False
    svc = config.setdefault("services", {})
    for name, defaults in _DEFAULT_SERVICES.items():
        if name not in svc:
            svc[name] = defaults
            modified = True
    return modified


# ─── Prompt helper ───────────────────────────────────────────────────────────
def ask(label: str, default: str = "", required: bool = False) -> str:
    hint = f" [{default}]" if default else ""
    while True:
        val = input(f"  {CYL}{label}{hint}{CR}: ").strip()
        if not val:
            val = default
        if val or not required:
            return val
        print(f"  {CR2}Campo obbligatorio.{CR}")


# ─── Onboarding wizard ───────────────────────────────────────────────────────
def onboard(config: dict, env: dict) -> tuple[dict, dict]:
    print(f"\n{CB}{CY}=== Prima configurazione B.M.O. ==={CR}")
    print("  Configuriamo insieme il tuo agente.\n")

    # Modello
    cur_model = config.get("agent", {}).get("model", "google/gemini-2.0-flash-001")
    new_model = ask("Modello AI (OpenRouter)", default=cur_model)
    config.setdefault("agent", {})["model"] = new_model

    # API key (obbligatoria, va in .env)
    print(f"\n  {CY}Inserisci la tua API key di OpenRouter.")
    print(f"  Puoi ottenerla su: https://openrouter.ai/keys{CR}")
    api_key = ask("OPENROUTER_API_KEY", required=True)
    env["OPENROUTER_API_KEY"] = api_key

    # Porte (opzionali)
    print(f"\n  {CY}Porte dei servizi (Invio = default):{CR}")
    svc = config.setdefault("services", {})
    for key, label, default in [
        ("ai_brain",  "AI.Brain  (FastAPI)",  "8000"),
        ("bmo_api",   "Bmo.Api   (.NET)  ",   "5271"),
        ("dashboard", "Dashboard (Next.js)",  "3000"),
    ]:
        cur = str(svc.get(key, {}).get("port", default))
        val = ask(f"Porta {label}", default=cur)
        svc[key] = {"port": int(val)}

    # AI.Voice — server TTS opzionale
    print(f"\n  {CY}AI.Voice — Server TTS (Piper voce custom):{CR}")
    print( "  Richiede un modello Piper ONNX addestrato (model.onnx + model.onnx.json).")
    print( "  Necessario solo se vuoi che BMO risponda con la voce sintetizzata.")
    voice_yn = input(f"  {CYL}Installare il server TTS? [s/N]:{CR} ").strip().lower()
    voice_enabled = voice_yn in ("s", "si", "y", "yes")
    if voice_enabled:
        voice_port_str = ask("Porta AI.Voice (TTS)", default="5050")
        svc["ai_voice"] = {"enabled": True, "port": int(voice_port_str)}
    else:
        svc.setdefault("ai_voice", {"enabled": False, "port": 5050})

    config["onboard_done"] = True
    return config, env


# ─── Settings editor ─────────────────────────────────────────────────────────
def modify_settings(config: dict, env: dict) -> tuple[dict, dict]:
    print(f"\n{CB}{CY}=== Modifica impostazioni ==={CR}")
    print("  Premi Invio per mantenere il valore attuale.\n")

    # Modello
    cur = config.get("agent", {}).get("model", "")
    val = ask("Modello AI", default=cur)
    if val:
        config.setdefault("agent", {})["model"] = val

    # API key
    cur_key = env.get("OPENROUTER_API_KEY", "")
    masked = ("*" * max(0, len(cur_key) - 4) + cur_key[-4:]) if cur_key else "non impostata"
    print(f"\n  API key attuale: {masked}")
    new_key = input(f"  {CYL}Nuova OPENROUTER_API_KEY{CR} (Invio per non cambiare): ").strip()
    if new_key:
        env["OPENROUTER_API_KEY"] = new_key

    # Porte
    print(f"\n  {CY}Porte (Invio per non cambiare):{CR}")
    svc = config.setdefault("services", {})
    for key, label in [
        ("ai_brain",  "AI.Brain  "),
        ("bmo_api",   "Bmo.Api   "),
        ("dashboard", "Dashboard "),
    ]:
        cur = str(svc.get(key, {}).get("port", ""))
        val = ask(f"Porta {label}", default=cur)
        if val:
            svc.setdefault(key, {})["port"] = int(val)

    # AI.Voice toggle
    voice_cfg     = svc.get("ai_voice", {})
    voice_enabled = voice_cfg.get("enabled", False)
    stato         = f"{CG}attivo{CR}" if voice_enabled else f"{CYL}disattivato{CR}"
    print(f"\n  AI.Voice (TTS): {stato}")
    toggle = input(
        f"  {CYL}{'Disattivare' if voice_enabled else 'Attivare'} AI.Voice?{CR} [s/N]: "
    ).strip().lower()
    if toggle in ("s", "si", "y", "yes"):
        voice_enabled = not voice_enabled
        svc.setdefault("ai_voice", {})["enabled"] = voice_enabled
        if voice_enabled:
            val = ask("Porta AI.Voice", default=str(voice_cfg.get("port", 5050)))
            svc["ai_voice"]["port"] = int(val)

    return config, env


# ─── Sync derived env files ──────────────────────────────────────────────────
def sync_ai_env(config: dict, env: dict):
    """Aggiorna DOTNET_API_URL in AI.Brain/.env in base alla porta bmo_api."""
    api_port = config["services"]["bmo_api"]["port"]
    env["DOTNET_API_URL"]  = f"http://localhost:{api_port}"
    env.setdefault("WORKSPACE_PATH", "../workspace")
    env.setdefault("CONFIG_PATH",    "../Bmo.Api/bmo_config.json")


def sync_dashboard_env(config: dict):
    """Crea/aggiorna dashboard-bmo/.env.local con NEXT_PUBLIC_BMO_API_URL."""
    api_port = config["services"]["bmo_api"]["port"]
    dash_env = load_env(DASH_ENV)
    dash_env["NEXT_PUBLIC_BMO_API_URL"] = f"http://localhost:{api_port}"
    save_env(DASH_ENV, dash_env)


# ─── Cross-platform terminal launcher ────────────────────────────────────────
def _find_linux_terminal():
    """Restituisce una funzione (title, cmd, cwd) -> [args] per il terminale disponibile."""
    candidates = [
        ("gnome-terminal", lambda t, c, d:
            ["gnome-terminal", f"--title={t}", "--",
             "bash", "-c", f'cd "{d}" && {c}; exec bash']),
        ("konsole", lambda t, c, d:
            ["konsole", f"--title={t}", "-e",
             "bash", "-c", f'cd "{d}" && {c}; exec bash']),
        ("xfce4-terminal", lambda t, c, d:
            ["xfce4-terminal", f"--title={t}", "-x",
             "bash", "-c", f'cd "{d}" && {c}; exec bash']),
        ("tilix", lambda t, c, d:
            ["tilix", "-t", t, "-e",
             f'bash -c \'cd "{d}" && {c}; exec bash\'']),
        ("xterm", lambda t, c, d:
            ["xterm", "-title", t, "-e",
             "bash", "-c", f'cd "{d}" && {c}; exec bash']),
    ]
    for name, builder in candidates:
        if shutil.which(name):
            return builder
    return None


def launch_terminal(title: str, command: str, cwd: Path):
    """Apre un nuovo terminale con `command` in `cwd`."""
    cwd_str = str(cwd)

    if SYSTEM == "Windows":
        if shutil.which("wt"):
            # Windows Terminal
            subprocess.Popen([
                "wt", "--title", title,
                "--startingDirectory", cwd_str,
                "cmd", "/k", command,
            ])
        else:
            # Finestra cmd classica
            subprocess.Popen(
                f'start "{title}" cmd /k "{command}"',
                shell=True,
                cwd=cwd_str,
            )

    elif SYSTEM == "Darwin":
        script = (
            f'tell application "Terminal" to do script '
            f'"cd \\"{cwd_str}\\" && {command}"'
        )
        subprocess.Popen(["osascript", "-e", script])

    else:  # Linux
        builder = _find_linux_terminal()
        if builder:
            args = builder(title, command, cwd_str)
            subprocess.Popen(args)
        else:
            # Fallback: background + log file
            log = ROOT / f"{title.replace(' ', '_').replace('|', '').strip()}.log"
            print(f"  {CYL}Nessun terminale GUI trovato per '{title}'. "
                  f"Output → {log}{CR}")
            with open(log, "w") as lf:
                subprocess.Popen(
                    f'cd "{cwd_str}" && {command}',
                    shell=True, stdout=lf, stderr=lf,
                )


# ─── Python venv path ────────────────────────────────────────────────────────
def get_python_exe() -> str:
    venv = ROOT / "AI.Brain" / ".venv"
    exe  = venv / ("Scripts/python.exe" if SYSTEM == "Windows" else "bin/python")
    return str(exe) if exe.exists() else sys.executable


# ─── Start services ──────────────────────────────────────────────────────────
def start_services(config: dict):
    svc        = config["services"]
    python_exe = get_python_exe()

    ai_port   = svc["ai_brain"]["port"]
    api_port  = svc["bmo_api"]["port"]
    dash_port = svc["dashboard"]["port"]

    print(f"\n{CB}Avvio servizi...{CR}\n")

    # 1 — AI.Brain  (Python / FastAPI)
    ai_cmd = f'"{python_exe}" -m uvicorn app:app --reload --host 0.0.0.0 --port {ai_port}'
    print(f"  {CG}▶{CR} AI.Brain        → http://localhost:{ai_port}")
    launch_terminal("B.M.O. | AI.Brain", ai_cmd, ROOT / "AI.Brain")
    time.sleep(0.4)

    # 2 — Bmo.Api  (.NET) — usa eseguibile locale se installato
    dotnet_exe = (
        str(_dotnet_local_exe())
        if _dotnet_local_exe().exists()
        else "dotnet"
    )
    api_cmd = f'"{dotnet_exe}" run --launch-profile http --urls "http://localhost:{api_port}"'
    print(f"  {CG}▶{CR} Bmo.Api (.NET)  → http://localhost:{api_port}")
    launch_terminal("B.M.O. | API Gateway", api_cmd, ROOT / "Bmo.Api")
    time.sleep(0.4)

    # 3 — AI.Voice (Flask TTS) — opzionale
    voice_cfg = svc.get("ai_voice", {})
    if voice_cfg.get("enabled", False):
        voice_port = voice_cfg.get("port", 5050)
        voice_py   = _voice_py_exe()
        if voice_py.exists():
            voice_cmd = f'"{voice_py}" server.py'
            print(f"  {CG}▶{CR} AI.Voice (TTS) → http://localhost:{voice_port}")
            launch_terminal("B.M.O. | AI.Voice", voice_cmd, VOICE_DIR)
            time.sleep(0.4)
        else:
            _warn("AI.Voice venv non trovato — esegui start.py per installarlo")

    # 4 — Dashboard  (Next.js) — usa npm locale se installato
    #     Se node è locale, prefissa il PATH nel comando del terminale
    #     così npm può trovare node durante l'esecuzione di next dev
    if _npm_local_cmd().exists():
        npm_cmd  = str(_npm_local_cmd())
        node_bin = str(NODE_DIR) if SYSTEM == "Windows" else str(NODE_DIR / "bin")
        if SYSTEM == "Windows":
            path_prefix = f'set "PATH={node_bin};%PATH%" && '
        else:
            path_prefix = f'export PATH="{node_bin}:$PATH" && '
        dash_cmd = f'{path_prefix}"{npm_cmd}" run dev -- --port {dash_port}'
    else:
        dash_cmd = f'npm run dev -- --port {dash_port}'

    print(f"  {CG}▶{CR} Dashboard       → http://localhost:{dash_port}")
    launch_terminal("B.M.O. | Dashboard", dash_cmd, ROOT / "dashboard-bmo")

    # Apertura browser
    dash_url = f"http://localhost:{dash_port}"
    print(f"\n  {CY}Apertura browser tra 5 secondi → {dash_url}{CR}")
    time.sleep(5)
    webbrowser.open(dash_url)

    print(f"\n  {CG}{CB}Tutti i servizi sono stati avviati.{CR}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print_header()

    check_dependencies()

    config = load_config()
    env    = load_env(ENV_PATH)

    # Aggiunge services block se mancante
    if ensure_services(config):
        save_config(config)

    first_run = not config.get("onboard_done", False)

    if first_run:
        config, env = onboard(config, env)
        sync_ai_env(config, env)
        sync_dashboard_env(config)
        save_config(config)
        save_env(ENV_PATH, env)
        print(f"\n  {CG}Configurazione salvata con successo.{CR}")
        setup_voice_venv_if_enabled(config)

    else:
        model = config.get("agent", {}).get("model", "?")
        print(f"  Configurazione trovata. Modello: {CY}{model}{CR}")
        answer = input(f"  {CYL}Vuoi modificare le impostazioni?{CR} [s/N]: ").strip().lower()
        if answer in ("s", "si", "y", "yes"):
            config, env = modify_settings(config, env)
            sync_ai_env(config, env)
            sync_dashboard_env(config)
            save_config(config)
            save_env(ENV_PATH, env)
            print(f"\n  {CG}Impostazioni aggiornate.{CR}")
            setup_voice_venv_if_enabled(config)
        else:
            # Sincronizza comunque .env.local (in caso di config già corretta)
            sync_dashboard_env(config)
            # Installa AI.Voice se abilitato e venv mancante
            setup_voice_venv_if_enabled(config)

    start_services(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {CYL}Avvio annullato.{CR}\n")
        sys.exit(0)
