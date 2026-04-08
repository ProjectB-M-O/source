# Persistent Memory

You can store and retrieve information across different sessions using the built-in SQLite database.

## Available tools

- `save_memory(key, value, category?)` — Saves or updates an entry
  - recommended `category` values: `user`, `task`, `note`, `context`, `preference`
- `query_memory(query)` — Searches by key, value, or category (max 20 results)

## When to use it

- **User information**: name, preferences, habits, professional context
- **Tasks**: current goals, todos, progress
- **Notes**: important observations for future conversations
- **Preferences**: how the user wants you to respond, communication style

## Example

```
save_memory("user_name", "Matteo", "user")
save_memory("user_prefers_english", "true", "preference")
query_memory("user")  → returns all entries with 'user' in key/value/category
```
