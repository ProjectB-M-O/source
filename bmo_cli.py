#!/usr/bin/env python3
"""
bmo CLI — B.M.O. Project Command Line Interface
Usage:
  bmo --help          Show this help
  bmo -onboard        Re-run onboarding wizard (preserves data)
  bmo -config         Interactive config editor (live + restart-required keys)
  bmo --dev on|off    Toggle dev_mode in bmo_config.json
"""

import sys
import os
from pathlib import Path

# Add project root to path so we can import start.py
sys.path.insert(0, str(Path(__file__).parent.absolute()))

import start as _s

# Re-export color constants for convenience
CY  = _s.CY
CG  = _s.CG
CYL = _s.CYL
CR2 = _s.CR2
CR  = _s.CR
CB  = _s.CB


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _mask_secret(value: str) -> str:
    """Mask sensitive values, showing only the last 4 chars."""
    if not value:
        return "(non impostata)"
    if len(value) <= 4:
        return "****"
    return value[:3] + "..." + value[-4:]


def _is_secret_key(key_name: str) -> bool:
    upper = key_name.upper()
    return any(word in upper for word in ("KEY", "SECRET", "TOKEN"))


def _display_value(key_name: str, value) -> str:
    """Format a value for menu display (mask secrets)."""
    if _is_secret_key(key_name) and isinstance(value, str):
        return _mask_secret(value)
    return repr(value) if isinstance(value, str) else str(value)


def _parse_bool(raw: str) -> bool:
    """Parse a user-supplied boolean string."""
    return raw.strip().lower() in ("true", "1", "si", "yes", "y", "on")


def _coerce_value(current, raw: str):
    """Coerce raw string to the same type as current value."""
    if isinstance(current, bool):
        return _parse_bool(raw)
    if isinstance(current, int):
        return int(raw)
    if isinstance(current, float):
        return float(raw)
    return raw


def _nested_get(d: dict, dotted_key: str):
    """Get a value from a nested dict using dotted key notation."""
    keys = dotted_key.split(".")
    node = d
    for k in keys:
        if isinstance(node, dict) and k in node:
            node = node[k]
        else:
            return None
    return node


def _nested_set(d: dict, dotted_key: str, value):
    """Set a value in a nested dict using dotted key notation."""
    keys = dotted_key.split(".")
    node = d
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    node[keys[-1]] = value


# ─── --help ───────────────────────────────────────────────────────────────────

def cmd_help():
    print(f"""
{CY}{CB}bmo{CR} — B.M.O. Project CLI

{CB}Comandi:{CR}

  {CG}bmo --help{CR}
      Mostra questo messaggio di aiuto.

  {CG}bmo --dev on|off{CR}
      Attiva o disattiva dev_mode in bmo_config.json.
      Nessun restart necessario.

  {CG}bmo -onboard{CR}
      Riesegue il wizard di configurazione iniziale.
      I dati esistenti vengono preservati come default.
      Riavvia automaticamente i servizi al termine.

  {CG}bmo -config{CR}
      Editor interattivo di configurazione.
      Mostra tutte le chiavi raggruppate in:
        - Chiavi live (effetto immediato)
        - Chiavi che richiedono restart
        - Credenziali (.env)
      Se vengono modificate chiavi che richiedono restart,
      i servizi vengono riavviati automaticamente.
""")


# ─── --dev on|off ─────────────────────────────────────────────────────────────

def cmd_dev(args: list):
    if not args:
        print(f"{CR2}Uso: bmo --dev on|off{CR}")
        sys.exit(1)

    raw = args[0].strip().lower()
    if raw in ("on", "true", "1", "si", "yes", "y"):
        value = True
        label = "on"
    elif raw in ("off", "false", "0", "no", "n"):
        value = False
        label = "off"
    else:
        print(f"{CR2}Valore non valido '{raw}'. Usa: on / off{CR}")
        sys.exit(1)

    config = _s.load_config()
    config["dev_mode"] = value
    _s.save_config(config)
    print(f"  {CG}✓{CR} dev_mode = {label}")


# ─── -onboard ─────────────────────────────────────────────────────────────────

def cmd_onboard():
    _s.print_header()
    config = _s.load_config()
    env    = _s.load_env(_s.ENV_PATH)

    print(f"\n{CB}{CY}Riconfigurazione B.M.O.{CR} — i dati esistenti non vengono cancellati.\n")

    config, env = _s.onboard(config, env)
    _s.sync_ai_env(config, env)
    _s.sync_dashboard_env(config)
    _s.save_config(config)
    _s.save_env(_s.ENV_PATH, env)

    _s.check_dependencies()
    _s.setup_voice_venv_if_enabled(config)
    _s.start_services(config)

    print(f"\n  {CG}✓{CR} Riconfigurazione completata. "
          f"Chiudi i vecchi terminali di servizio se ancora aperti.")


# ─── -config ──────────────────────────────────────────────────────────────────

# Menu items: (display_label, config_key_or_env_key, section)
# section: "live" | "restart" | "env"
_MENU_ITEMS = [
    # Live keys
    ("agent.name",                 "agent.name",                  "live"),
    ("agent.model",                "agent.model",                 "live"),
    ("agent.max_tool_iterations",  "agent.max_tool_iterations",   "live"),
    ("tools.enabled",              "tools.enabled",               "live"),
    ("tools.log_all",              "tools.log_all",               "live"),
    ("tools.show_in_chat",         "tools.show_in_chat",          "live"),
    ("context.max_tokens",         "context.max_tokens",          "live"),
    ("context.pruning_threshold",  "context.pruning_threshold",   "live"),
    ("context.compaction_enabled", "context.compaction_enabled",  "live"),
    ("dev_mode",                   "dev_mode",                    "live"),
    # Restart-required keys
    ("services.ai_brain.port",     "services.ai_brain.port",      "restart"),
    ("services.bmo_api.port",      "services.bmo_api.port",       "restart"),
    ("services.dashboard.port",    "services.dashboard.port",     "restart"),
    ("services.ai_voice.port",     "services.ai_voice.port",      "restart"),
    ("workspace_path",             "workspace_path",              "restart"),
    # Credentials (.env)
    ("OPENROUTER_API_KEY",         "OPENROUTER_API_KEY",          "env"),
    ("DOTNET_API_URL",             "DOTNET_API_URL",              "env"),
    ("WORKSPACE_PATH",             "WORKSPACE_PATH",              "env"),
    ("CONFIG_PATH",                "CONFIG_PATH",                 "env"),
]


def _get_item_value(item_key: str, section: str, config: dict, env: dict):
    if section == "env":
        return env.get(item_key, "")
    return _nested_get(config, item_key)


def _set_item_value(item_key: str, section: str, config: dict, env: dict, new_value):
    if section == "env":
        env[item_key] = new_value
    else:
        _nested_set(config, item_key, new_value)


def _print_menu(config: dict, env: dict):
    print(f"\n{CB}=== B.M.O. Config Editor ==={CR}\n")

    current_section = None
    section_headers = {
        "live":    f"[{CG}LIVE{CR} — nessun restart]",
        "restart": f"[{CYL}⚠ RICHIEDE RESTART{CR}]",
        "env":     f"[{CY}🔑 CREDENZIALI (.env){CR}]",
    }

    for idx, (label, key, section) in enumerate(_MENU_ITEMS, start=1):
        if section != current_section:
            current_section = section
            print(f"{section_headers[section]}")

        value = _get_item_value(key, section, config, env)
        display = _display_value(key, value)
        print(f"  {CYL}{idx:2}.{CR} {label:<30} = {display}")

    print(f"\n  {CYL} 0.{CR} Salva ed esci\n")


def cmd_config():
    config = _s.load_config()
    env    = _s.load_env(_s.ENV_PATH)

    restart_required_keys = set()  # track which restart keys were changed

    while True:
        _print_menu(config, env)

        raw = input(f"  {CYL}Seleziona numero (0 per uscire):{CR} ").strip()

        if raw == "0" or raw == "":
            break

        try:
            choice = int(raw)
        except ValueError:
            print(f"  {CR2}Inserisci un numero valido.{CR}")
            continue

        if choice < 1 or choice > len(_MENU_ITEMS):
            print(f"  {CR2}Numero fuori range (1-{len(_MENU_ITEMS)}).{CR}")
            continue

        label, key, section = _MENU_ITEMS[choice - 1]
        current = _get_item_value(key, section, config, env)

        # Show current value (masked if secret)
        display = _display_value(key, current)
        print(f"\n  Valore attuale di {CY}{label}{CR}: {display}")

        # Prompt for new value
        new_raw = input(f"  {CYL}Nuovo valore{CR} (Invio = mantieni): ").strip()

        if not new_raw:
            print(f"  Valore invariato.")
            continue

        try:
            new_value = _coerce_value(current, new_raw)
        except (ValueError, TypeError) as e:
            print(f"  {CR2}Valore non valido: {e}{CR}")
            continue

        _set_item_value(key, section, config, env, new_value)

        if section == "restart":
            restart_required_keys.add(key)

        print(f"  {CG}✓{CR} {label} = {_display_value(key, new_value)}")

    # Save
    _s.save_config(config)
    _s.save_env(_s.ENV_PATH, env)

    if restart_required_keys:
        print(f"\n  {CYL}⚠{CR} Hai modificato chiavi che richiedono restart. "
              f"Avvio nuovi terminali di servizio... "
              f"Chiudi i vecchi terminali manualmente.")
        _s.start_services(config)
    else:
        print(f"\n  {CG}✓{CR} Configurazione salvata.")


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "-help"):
        cmd_help()
        return

    cmd = args[0]
    rest = args[1:]

    if cmd == "--dev":
        cmd_dev(rest)
    elif cmd == "-onboard":
        cmd_onboard()
    elif cmd == "-config":
        cmd_config()
    else:
        print(f"{CR2}Comando sconosciuto: {cmd}{CR}")
        print(f"Usa {CG}bmo --help{CR} per la lista dei comandi.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {CYL}Operazione annullata.{CR}\n")
        sys.exit(0)
