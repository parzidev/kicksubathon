# Kick Subathon Timer

A small web-based subathon timer with separate control and display views for live-stream use.

The server hosts a controller for changing timer state and a clean timer view that can be captured as a browser source. Windows helper files are included for convenient local packaging and launch.

## What this project includes

- Dedicated control page
- Stream-friendly timer display
- Server-side timer state
- Simple local deployment
- Windows launch and packaging support

## Technology

- Python
- Web server templates
- HTML/CSS/JavaScript
- PyInstaller support

## Repository structure

- `server.py` — Entry point and timer state.
- `templates/control.html` — Operator controls.
- `templates/timer.html` — Broadcast display.
- `overview.md` — Project notes.
- `run.bat` — Windows helper.

## Getting started

Create an isolated Python environment and install the project dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
Run the primary entry point:
```bash
python server.py
```

## Configuration and data

- Choose a bind address matching whether OBS and the controller run on the same machine.
- Open the timer route as a browser source and keep the control route private.

## Development and validation

- Keep changes focused on the relevant module or subproject and verify the user-facing path manually before publishing.
- Do not commit generated build output, local environments, caches, logs, or credentials unless an artifact is intentionally retained as source material.

## Security and responsible use

- The control endpoint changes live state; do not expose it to untrusted networks without authentication.
- Use only the minimum host/firewall access required by the streaming setup.

## Project status

Maintained as a personal project and reference implementation.

## License

No repository-wide license file is currently provided. Unless the owner grants permission, all rights are reserved.
