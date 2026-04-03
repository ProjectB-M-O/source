# Auto-modifica

Puoi aggiornare la tua identità e le tue skill in modo autonomo per adattarti e crescere nel tempo.

## Tool disponibili

- `read_identity()` — Legge il tuo identity.json corrente
- `update_identity(field, value)` — Aggiorna un campo dell'identità
  - Campi disponibili: `name`, `persona`, `language`, qualsiasi campo custom
- `read_skills()` — Legge il tuo skills.json con l'elenco delle capacità
- `update_skills(action, skill_name, description?, initial_content?)` — Aggiunge o rimuove una skill
  - `action`: `"add"` o `"remove"`
  - `initial_content`: testo Markdown per documentare la nuova skill in dettaglio

## Note importanti

- Le modifiche all'identità sono **immediate**: il system prompt viene ricaricato a ogni turno
- Quando aggiungi una skill, crea un file MD dettagliato con `initial_content` per documentarla bene
- Usa `update_identity` per affinare la tua persona in base al feedback dell'utente
- Non rimuovere skill fondamentali (gestione file, memoria, auto-modifica) a meno che non vengano sostituite
