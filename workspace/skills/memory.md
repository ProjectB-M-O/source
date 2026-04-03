# Memoria Persistente

Puoi salvare e recuperare informazioni tra sessioni diverse usando il database SQLite integrato.

## Tool disponibili

- `save_memory(key, value, category?)` — Salva o aggiorna una voce
  - `category` consigliati: `user`, `task`, `note`, `context`, `preference`
- `query_memory(query)` — Cerca per key, value o categoria (max 20 risultati)

## Quando usarla

- **Informazioni sull'utente**: nome, preferenze, abitudini, contesto professionale
- **Task**: obiettivi in corso, cose da fare, progressi
- **Note**: osservazioni importanti per conversazioni future
- **Preferenze**: come l'utente vuole che tu risponda, stile di comunicazione

## Esempio

```
save_memory("user_name", "Matteo", "user")
save_memory("user_prefers_italian", "true", "preference")
query_memory("user")  → restituisce tutte le voci con 'user' in key/value/categoria
```
