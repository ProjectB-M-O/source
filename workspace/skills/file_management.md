# Gestione File

Puoi leggere, scrivere ed elencare file nella tua workspace tramite tool dedicati.

## Tool disponibili

- `read_file(path)` — Legge il contenuto di un file
- `write_file(path, content)` — Crea o sovrascrive un file
- `list_files(path?)` — Elenca file e cartelle in una directory

## Note importanti

- Tutti i file vivono in `workspace/files/` — non puoi uscire da questa sandbox
- Usa i file per salvare informazioni complesse, codice, note strutturate, dati JSON
- Puoi creare sotto-cartelle passando un path con `/` (es. `notes/2026/april.md`)
