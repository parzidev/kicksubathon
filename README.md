# Kicksubathon

> Engineering README reviewed from the repository state on 2026-09-05. Observed facts are separated from items that still need manual verification.

**Repository:** [parzidev/kicksubathon](https://github.com/parzidev/kicksubathon)  
**Visibility:** public  
**Default branch:** `main`  
**Latest GitHub push observed:** `2026-08-29T09:12:18Z`  
**Scanned HEAD:** `67695689b51b6c0b3383b5f5c79571c4304cea5d`  
**Repository description:** Not set on GitHub.

## Purpose and scope

A small web-based subathon timer with separate control and display views for live-stream use.

The repository currently contains **9** source-tree files, including **3** code-like files. This README describes the repository as it exists in the scanned snapshot; it is not a claim that every historical or runtime path is still active.

## Capability inventory

### README evidence

The source README exposes these sections: `Kick Subathon Timer`, `What this project includes`, `Technology`, `Repository structure`, `Getting started`, `Configuration and data`, `Development and validation`, `Security and responsible use`, `Project status`, `License`.

### Detected technology profile

| `HTML` | 2 code-like files |
| `Python` | 1 code-like files |

### Project structure

Top-level paths observed:

- `.gitignore`
- `README.md`
- `overview.md`
- `requirements.txt`
- `run.bat`
- `sabaton-server.spec`
- `server.py`
- `templates`

Key entrypoint candidates:

- `run.bat`
- `sabaton-server.spec`
- `server.py`

## Architecture and runtime shape

| Area | Observed evidence |
| --- | --- |
| Entrypoint candidates | `run.bat`, `sabaton-server.spec`, `server.py` |
| Build/config manifests | `requirements.txt` |

Interpretation boundary: filenames and manifests show where a component may start, but they do not prove deployment topology, request flow, persistence semantics, or production readiness. Those items should be confirmed against the implementation before making operational claims about the project.

## Code-level signals

The following patterns were extracted from readable code files. They are navigation aids for the next human review, not a substitute for reading the implementation:

**Integration/framework keywords:** `Flask`, `Kick`, `WebSocket`

**Route-like declarations:**

- `@app.route('/')`
- `@app.route('/control')`
- `@app.route('/api/status')`
- `@app.route('/api/start', methods=['POST'])`
- `@app.route('/api/add_time', methods=['POST'])`
- `@app.route('/api/stop', methods=['POST'])`
- `@app.route('/api/config', methods=['POST'])`
- `@app.route('/api/ui', methods=['GET', 'POST'])`
- `@app.route('/api/rewards', methods=['GET', 'POST'])`
- `@app.route('/api/kick_tiers', methods=['GET', 'POST'])`
- `@app.route('/api/test/sub', methods=['POST'])`
- `@app.route('/api/test/giftsub', methods=['POST'])`

**Named functions/classes/types observed:** `resource_path`, `clamp_int`, `sanitize_config`, `sanitize_ui_config`, `sanitize_rewards_payload`, `sanitize_kick_tiers_payload`, `try_process_reward_payload`, `KickSubathonListener`, `__init__`, `start`, `on_open`, `on_message`, `on_error`, `on_close`, `add_time`, `get_timer_status`, `index`, `control`, `api_status`, `api_start`, `api_add_time`, `api_stop`, `api_config`, `api_ui`, `api_rewards`, `api_kick_tiers`, `api_test_sub`, `api_test_giftsub`, `handle_connect`, `timer_broadcast_loop`, `main`, `updateCountdown`, `updateEventsList`, `startTimer`, `stopTimer`, `addTime`, `loadUI`, `saveUI`, `setInput`, `setNumber`, `setColor`, `loadConfig`, `saveConfig`, `loadRewards`, `saveRewards`, `testSub`, `testGiftSub`, `loadKickTiers`, `saveKickTiers`, `applyUI`, `handleTimerUpdate`, `eventKey`, `processEventsBatch`, `showEventNotification`, `handleKickEvent`, `spawnKickToken`, `animateToken`, `renderKickCombo`, `hideKickCombo`, `showSubPanel`

**Top-level import/module signals:** `json`, `websocket`, `threading`, `time`, `datetime`, `flask`, `flask_socketio`, `os`, `sys`

## Setup and operation

The most relevant source README material is reproduced below:

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

Static setup/deployment evidence:

- Docker files: none detected
- Build/config manifests: `requirements.txt`
- Configuration-like paths: none detected

### Command evidence

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

```bash
python server.py
```

## API, integrations, and data flow

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

Before publishing a public README, confirm the following from code and deployment configuration:

- inbound routes, ports, webhooks, and authentication middleware;
- outbound providers, rate limits, retries, and failure behavior;
- persistence files/databases and backup/restore expectations;
- whether any endpoint can mutate external state.

## Configuration and secrets

Detected names (names only; values were intentionally excluded):

No conventional environment-variable names were detected in the sampled manifests/entrypoints.

Configuration paths observed:

- None detected in the static scan.

Do not paste real tokens, passwords, private keys, cookies, or production URLs into this README or a public README. Replace them with placeholders and document where the operator should provision them.

## Security and privacy

## Security and responsible use

- The control endpoint changes live state; do not expose it to untrusted networks without authentication.
- Use only the minimum host/firewall access required by the streaming setup.

Minimum publication checklist:

- document trust boundaries and the intended network exposure;
- explain authentication and authorization separately;
- state whether logs, uploads, identifiers, or third-party data are retained;
- include a responsible-use note where the project interacts with Steam, Kick, Riot, Spotify, Cloudflare, or other external platforms;
- keep example configuration values synthetic.

## Validation and maintenance

## Development and validation

- Keep changes focused on the relevant module or subproject and verify the user-facing path manually before publishing.
- Do not commit generated build output, local environments, caches, logs, or credentials unless an artifact is intentionally retained as source material.

Test-like paths were detected, but no tests were executed during this documentation-only scan.

Test-like paths observed:

- `sabaton-server.spec`

CI/workflow and maintenance evidence should be verified before adding badges or claiming release guarantees.

## Known gaps and verification notes

- Repository snapshot was available for static inspection.
- This was a static documentation scan; no repository code, containers, network services, or test suites were executed.
- “Detected” means a filename, README section, manifest, or sampled entrypoint matched the scanner; it is not a security audit.
- README sections may describe an older state than the current code. Compare the published README with the latest default-branch files before committing it upstream.

## Reference README material (sanitized)

The relevant source README is retained below as reference material, with credential-shaped values removed.

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
