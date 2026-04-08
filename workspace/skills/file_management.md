# File Management

You can read, write, and list files in your workspace via dedicated tools.

## Available tools

- `read_file(path)` — Reads the contents of a file
- `write_file(path, content)` — Creates or overwrites a file
- `list_files(path?)` — Lists files and folders in a directory

## Important notes

- All files live under `workspace/files/` — you cannot escape this sandbox
- Use files to store complex information, code, structured notes, and JSON data
- You can create subfolders by using `/` in the path (e.g. `notes/2026/april.md`)
