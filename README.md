# CSITEGames — QR/Host Game

This repository contains several Pygame projects. The `qr code testing` folder includes `connect.py`, a Flask+SocketIO host that generates a QR code for joining a local multiplayer duel.

Quick start (local):

1. Open a terminal in the project root:

```bash
cd "/Users/alphase_/Documents/CSITEGames/qr code testing"
```

2. Create and activate a virtualenv, install requirements:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

3. Run the host script:

```bash
python connect.py
```

Then follow the on-screen instructions: enable a phone hotspot (or put both devices on the same LAN), and scan the QR code shown on the Pygame window.

Publishing options
------------------

- Temporary public demo: run the host locally and expose it with `ngrok`:

```bash
# after starting connect.py locally
ngrok http 5000
```

Copy the forwarded `https://...` URL and use it in the QR (or use the QR scanner on the phone to open it).

- Source distribution: push the folder to GitHub so others can clone and run locally.

- Server-hosted deployment: deploy the Flask/SocketIO host to a cloud provider (Railway, Render, Heroku). Ensure WebSocket/SocketIO support and set `PORT` from the environment.

Useful files created
- `requirements.txt` — dependencies
- `run.sh` — convenience script to create venv and run the host
- `.gitignore` — common ignores

If you want, I can:
- Create a repo and push these files for you
- Generate a small `Procfile` / `Dockerfile` for easy deploy
- Show exact `git` commands to publish
