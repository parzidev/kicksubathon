## Project overview

This repository implements a local Kick.com subathon timer server intended to be added into OBS as a Browser Source and controlled from a web control panel. It listens to live Kick events via a Pusher WebSocket channel and converts them into time extensions on a countdown timer. The server pushes real-time updates to connected browser clients using Socket.IO.

### High-level architecture
- **Flask HTTP server**: Serves two pages — `timer.html` (overlay for OBS) and `control.html` (control panel) — and REST endpoints for starting/stopping and adjusting the timer.
- **Flask-SocketIO**: Maintains real-time connections to browsers to broadcast timer updates and event notifications.
- **Kick WebSocket listener**: Connects to Kick's Pusher WS endpoint to subscribe to channel/chatroom events (subscriptions, gifted subs, and “Kicks”). On relevant events, it adds time to the timer and notifies clients.
- **In-memory state**: Timer state and recent events are stored in-process in a global `timer_data` dictionary.
- **OBS integration**: `timer.html` displays the remaining time and event notifications; it is designed to be added as a Browser Source in OBS.

### Data flow
1. Kick event arrives over WebSocket → parsed → mapped to a time delta.
2. Timer end time is updated in memory → event is appended to the recent events list.
3. Server emits `timer_update` and `new_event` via Socket.IO → clients update UI.
4. A background loop also emits regular `timer_update` ticks while the timer runs.


## Code structure
- `server.py`: Main application including Flask routes, Socket.IO event handlers, the Kick WebSocket listener, in-memory timer state, and the main entrypoint.
- `templates/timer.html`: The overlay for OBS; shows remaining time and toast-like event notifications.
- `templates/control.html`: Control panel UI to start/stop the timer, add manual time, and view recent events; also displays the OBS URL to copy.
- `run.bat`: Windows helper to check Python, install dependencies from `requirements.txt`, and run the server.


## Key modules and interactions

### Flask and Socket.IO
- Initializes Flask app and Socket.IO with permissive CORS; pushes periodic timer updates to clients.
- Emits `timer_update` on connect and whenever state changes.

```python
# server.py
app = Flask(__name__)
app.config['SECRET_KEY'] = 'subathon_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*")
```

- REST endpoints:
  - `GET /` → `timer.html`
  - `GET /control` → `control.html`
  - `GET /api/status` → Returns timer/config/events summary
  - `POST /api/start` → Starts timer with minutes
  - `POST /api/add_time` → Adds seconds with optional message
  - `POST /api/stop` → Stops timer
  - `POST /api/config` → Updates subathon config (minutes per event, max, etc.)

```python
# server.py (selected routes)
@app.route('/')
def index():
    return render_template('timer.html')

@app.route('/control')
def control():
    return render_template('control.html')

@app.route('/api/status')
def api_status():
    return jsonify({'timer': get_timer_status(), 'config': SUBATHON_CONFIG, 'events': timer_data['events'][:10]})
```

### Timer state and broadcasting
- Global `timer_data` holds:
  - `end_time`, `is_running`, `total_seconds` (unused), and recent `events` (capped at 50).
- Helpers:
  - `add_time(seconds, message, event_type)` updates end time and appends event.
  - `get_timer_status()` formats remaining time for clients.
- A background thread runs `timer_broadcast_loop()` to emit updates while running.

```python
# server.py (selected logic)
if not timer_data['is_running']:
    timer_data['end_time'] = datetime.now() + timedelta(seconds=SUBATHON_CONFIG['initial_minutes'] * 60)
    timer_data['is_running'] = True
...
socketio.emit('timer_update', get_timer_status())
socketio.emit('new_event', event)
```

### Kick.com WebSocket listener
- Uses `websocket-client` to connect to Kick’s Pusher endpoint, subscribes to several channel names, and processes events that map to time additions.

```python
# server.py (selected)
WS_URL = "wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679?protocol=7&client=js&version=8.4.0&flash=false"
HEADERS = {"Origin": "https://kick.com", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
...
class KickSubathonListener:
    def on_message(self, ws, message):
        data = json.loads(message)
        event = data.get("event")
        if event == "App\\Events\\SubscriptionEvent":
            add_time(SUBATHON_CONFIG['sub_minutes'] * 60, f"{username} abone oldu!", 'subscription')
        elif event == "App\\Events\\GiftedSubscriptionsEvent":
            add_time(SUBATHON_CONFIG['gift_sub_minutes'] * quantity * 60, f"{gifter} {quantity} abonelik hediye etti!", 'gift_subscription')
        elif event == "KicksGifted":
            add_time(amount * SUBATHON_CONFIG['kick_seconds_per_unit'], f"{username} {amount} Kick gönderdi!", 'kick')
```


## Third-party integrations

- **Flask + Flask-SocketIO**
  - **purpose**: Web server and real-time push to clients.
  - **where**: Initialization and usage throughout `server.py`.
  - **config**: `SECRET_KEY` required; a message queue (e.g., Redis) is recommended for scaling beyond a single process.
  - **environment variables (recommended)**:
    - `FLASK_SECRET_KEY`
    - `SOCKETIO_CORS_ORIGINS` (restrict to your OBS/control origins)
  - **risks**: Using Werkzeug with `allow_unsafe_werkzeug=True` in production is unsafe; use a proper WSGI/ASGI server with an async worker (eventlet/gevent) for Socket.IO.

- **websocket-client (Kick Pusher WS)**
  - **purpose**: Listen to live Kick channel events to extend the timer.
  - **where**: `KickSubathonListener` in `server.py`.
  - **config**: `WS_URL` and `HEADERS` are hard-coded; channel IDs are provided at runtime via stdin.
  - **environment variables (recommended)**:
    - `KICK_CHANNEL_ID`, `KICK_CHATROOM_ID` (provide via env or CLI flags rather than interactive input)
    - `KICK_PUSHER_URL` and `KICK_PUSHER_HEADERS_JSON` if customization is needed
  - **risks**:
    - Reliance on undocumented/implicit Pusher channels → vendor lock with potential breakage if Kick changes formats or auth.
    - Headers spoof an origin; ensure usage complies with platform ToS.

- **Socket.IO browser client (CDN)**
  - **purpose**: Real-time client connections.
  - **where**: Included via `<script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>` in both templates.
  - **risks**:
    - CDN supply-chain risk; no SRI integrity attributes are used.
    - Version pin is present but external; consider vendoring or using a trusted CDN + integrity.

- **OBS**
  - **purpose**: Renders `timer.html` in stream overlay and `control.html` for management (usually a separate browser).
  - **where**: Access via `http://localhost:5000/` (overlay) and `/control` (panel).


## Configuration and behavior

- `SUBATHON_CONFIG` keys (defaults):
  - `initial_minutes`: 30
  - `sub_minutes`: 30
  - `gift_sub_minutes`: 30
  - `kick_seconds_per_unit`: 5
  - `max_minutes`: 180

- Manual overrides:
  - `POST /api/config` updates any of the above without validation.
  - `POST /api/start` can specify starting minutes.
  - `POST /api/add_time` adds arbitrary seconds with an optional message.


## Security and vulnerability audit

- **Hard-coded secret**
  - **issue**: `app.config['SECRET_KEY']` is hard-coded and weak.
  - **risk**: Enables cookie tampering/session forgery; bad practice even if sessions aren’t heavily used.
  - **fix**:
    - Read from `FLASK_SECRET_KEY` env var; generate a strong value (32+ random bytes hex/Base64).
    - Do not commit secrets.

- **No authentication/authorization**
  - **issue**: All control endpoints (`/api/start`, `/api/add_time`, `/api/stop`, `/api/config`) are unauthenticated.
  - **risk**: Anyone with network access can manipulate the timer if bound to `0.0.0.0`.
  - **fix options (pick at least one)**:
    - Require an admin bearer token header (env-provided secret) and verify on all POST endpoints.
    - Add simple HTTP Basic Auth on `/control` and protect API routes accordingly.
    - Restrict binding to `127.0.0.1` and access control panel locally only; expose overlay read-only.

- **Overly permissive CORS and network binding**
  - **issue**: `SocketIO(..., cors_allowed_origins="*")` and server runs on `0.0.0.0`.
  - **risk**: Cross-origin abuse and broader attack surface.
  - **fix**:
    - Restrict `cors_allowed_origins` to specific origins (OBS overlay origin, control panel origin).
    - Bind to `127.0.0.1` by default; only expose externally behind a reverse proxy with TLS and auth.

- **CSRF and method protections**
  - **issue**: JSON POST endpoints lack CSRF protection.
  - **risk**: If control panel is accessible via browser, a malicious site could trigger state changes.
  - **fix**:
    - Require a bearer token header; avoid cookie-based auth unless you add CSRF tokens.

- **Input validation missing**
  - **issue**: `minutes`/`seconds` and config updates are not validated.
  - **risk**: DoS by setting huge times/max or negative values.
  - **fix**:
    - Validate and clamp inputs (e.g., `0 < minutes <= 24*60`, `0 < seconds <= 3600`, reasonable max caps).
    - Validate `SUBATHON_CONFIG` types and ranges.

- **XSS risks in templates**
  - **issue**: User-derived strings (e.g., Kick usernames/messages) are inserted into the DOM via `innerHTML` in both templates for event messages.
  - **risk**: Reflected/stored XSS if content isn't sanitized.
  - **fix**:
    - Use `textContent` to insert user strings, or sanitize with a trusted library.
    - Avoid assembling HTML via string concatenation for untrusted data.

- **Thread safety and race conditions**
  - **issue**: Global `timer_data` is mutated from multiple threads (WS listener, broadcast loop, Flask handlers) without locking.
  - **risk**: Inconsistent state, rare crashes.
  - **fix**:
    - Introduce a `threading.Lock` guarding all reads/writes of `timer_data` and `SUBATHON_CONFIG`.

- **Reconnect spawning threads**
  - **issue**: In `on_close`, calling `self.start()` may create multiple listener threads over time.
  - **risk**: Thread leaks and duplicated handling.
  - **fix**:
    - Centralize the reconnect loop within a single thread; avoid recursion into `start()`; ensure only one WS thread runs.

- **Dependency and supply-chain concerns**
  - **issue**: No `requirements.txt` in repo while `run.bat` expects it; versions are not pinned.
  - **risks**: Non-reproducible installs; potential transitive vulnerabilities.
  - **fix**:
    - Add a pinned `requirements.txt` (see below) and scan with `pip-audit`.

- **Production server flags**
  - **issue**: `allow_unsafe_werkzeug=True` disables safety checks; fine for dev, not prod.
  - **fix**:
    - Use `socketio.run(app, host="127.0.0.1", port=5000)` for local dev; for prod use gunicorn + eventlet/gevent.


## Recommended requirements.txt

Pin and review these versions (adjust Python minor version as needed):

```text
flask==3.0.3
flask-socketio==5.3.6
python-socketio[client]==5.10.0
websocket-client==1.8.0
jinja2==3.1.4
werkzeug==3.0.3
eventlet==0.35.2  # or gevent==24.2.1 + gevent-websocket==0.10.1
```

Optional tools:
```text
pip-audit==2.7.3
python-dotenv==1.0.1
```


## Onboarding and setup

- **Prerequisites**
  - Python 3.10+ and pip
  - Windows (for `run.bat`), or any OS using `python server.py`
  - OBS installed

- **Install**
  - Create and activate a virtual environment.
  - Add a `requirements.txt` (above) and run `pip install -r requirements.txt`.

- **Configuration**
  - Provide `FLASK_SECRET_KEY` env var.
  - Strongly recommended: `ADMIN_TOKEN` env var for protecting control APIs.
  - Optional: `KICK_CHANNEL_ID`, `KICK_CHATROOM_ID` env vars; otherwise you will be prompted at runtime.

- **Run**
  - Windows: double-click `run.bat` once `requirements.txt` exists.
  - Cross-platform: `python server.py` and follow the prompts to enter Kick `channel_id` and `chatroom_id`.
  - Access:
    - OBS overlay: `http://localhost:5000/`
    - Control panel: `http://localhost:5000/control`

- **Pitfalls**
  - `requirements.txt` is missing; add it or `run.bat` will do nothing meaningful.
  - If you bind to `0.0.0.0` without auth, anyone on your LAN can control the timer.
  - Ensure your firewall allows local connections if using OBS on another machine.


## Deployment and infrastructure

- **Local/dev**
  - Bind to `127.0.0.1` and access from the same machine.
  - Keep `debug=False` (already set) and do not rely on Werkzeug for prod.

- **Production**
  - Front the app with Nginx (TLS) → Gunicorn (with `eventlet` or `gevent`) → Flask-SocketIO app.
  - Configure reverse proxy for WebSockets (`Upgrade`/`Connection` headers).
  - Restrict access to `/control` and POST APIs (token or basic auth).
  - Set env vars via systemd or container secrets.
  - Consider Redis as a message queue for Socket.IO if scaling to multiple workers/instances.

- **Observability**
  - Add structured logging for events and errors.
  - Health endpoint (read-only) can expose minimal status.


## Migration and vendor-lock considerations

- The Kick Pusher protocol and event payloads are unofficial/subject to change. Future changes can break the listener without notice.
- Abstract the listener behind an interface so you can:
  - Swap implementations (Kick, Twitch, YouTube) without touching timer logic.
  - Unit test event → time mapping independent of network code.


## Roadmap and next steps

- **Must-fix before scaling (high priority)**
  - Replace hard-coded `SECRET_KEY` with `FLASK_SECRET_KEY` env var.
  - Add authentication to control endpoints (bearer token) and restrict CORS.
  - Validate and clamp all inputs (`/api/start`, `/api/add_time`, `/api/config`).
  - Remove `allow_unsafe_werkzeug=True` in production; run behind gunicorn+eventlet.
  - Sanitize DOM writes in templates; use `textContent` for user-derived strings.
  - Add a `requirements.txt` with pinned versions; run `pip-audit`.
  - Introduce a `threading.Lock` around `timer_data` and `SUBATHON_CONFIG` accesses.

- **Short term (days)**
  - Add `.env` support (`python-dotenv`) and document required env vars.
  - Add SRI integrity to Socket.IO CDN or self-host the script.
  - Centralize reconnect logic to avoid thread leaks.
  - Add simple unit tests for `add_time` and `get_timer_status`.

- **Mid term (weeks)**
  - Abstract event sources; create an interface for different platforms.
  - Add persistent storage for recent events (SQLite) if you need history across restarts.
  - Add Redis-backed message queue for Socket.IO to support multi-process scaling.

- **Long term**
  - Containerize with Docker; add CI to build/test and scan dependencies.
  - Implement a proper auth UI and role model for multi-user control.
  - Telemetry and operational dashboards (Grafana/Prometheus) for uptime and event rate.


## Suggested code changes (summary)

- Replace secret and add env loading:
```python
import os
from dotenv import load_dotenv
load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(32).hex())
```

- Protect control APIs (example bearer token check):
```python
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN')

def require_admin(req):
    return ADMIN_TOKEN and req.headers.get('Authorization') == f"Bearer {ADMIN_TOKEN}"

@app.route('/api/stop', methods=['POST'])
def api_stop():
    if not require_admin(request):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    # ... existing logic ...
```

- Sanitize DOM writes: use `textContent` in templates instead of building HTML with untrusted strings.
- Add a global `threading.Lock` and wrap all reads/writes to shared state.
- Restrict `cors_allowed_origins` and default to `host='127.0.0.1'` for dev.

---

If you want, I can implement the security hardening (auth, env config, locking, XSS fixes) and add a pinned `requirements.txt` in a follow-up.
