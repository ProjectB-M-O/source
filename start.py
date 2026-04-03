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
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.absolute()
CONFIG_PATH = ROOT / "Bmo.Api" / "bmo_config.json"
ENV_PATH    = ROOT / "AI.Brain" / ".env"
DASH_ENV    = ROOT / "dashboard-bmo" / ".env.local"

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

    # 2 — Bmo.Api  (.NET)
    api_cmd = f'dotnet run --launch-profile http --urls "http://localhost:{api_port}"'
    print(f"  {CG}▶{CR} Bmo.Api (.NET)  → http://localhost:{api_port}")
    launch_terminal("B.M.O. | API Gateway", api_cmd, ROOT / "Bmo.Api")
    time.sleep(0.4)

    # 3 — Dashboard  (Next.js)
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
        else:
            # Sincronizza comunque .env.local (in caso di config già corretta)
            sync_dashboard_env(config)

    start_services(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {CYL}Avvio annullato.{CR}\n")
        sys.exit(0)
