# ⚔️ Arena — Phone-Controller Multiplayer Game

A real-time browser game where a **laptop is the display** and **phones are the controllers**. Players scan a QR code to join — no apps, no installs.

- 🎮 2–4 players compete to collect coins on a platformer arena
- 📱 Phones become wireless controllers (left / right / jump)
- 🖥️ Laptop renders the game and shows live scores
- 🌐 Works over the internet (not just LAN), once deployed

---

## How it works

```
 ┌──────────────────┐         WebSocket         ┌──────────────────┐
 │   Laptop (host)  │ <───────────────────────> │     Server       │
 │  - QR code       │     game-state-update     │  Node + Socket.IO│
 │  - Game canvas   │                           │  Authoritative   │
 │  - Scoreboard    │                           │  game loop @60Hz │
 └──────────────────┘                           └──────────────────┘
                                                       ▲
                              player-input             │
                                                       │
                             ┌─────────┐   ┌─────────┐
                             │ Phone 1 │   │ Phone 2 │  (controllers)
                             └─────────┘   └─────────┘
```

The **server is authoritative**. Phones only send button states; the server simulates physics and broadcasts the world to the host.

---

## Project structure

```
arena-game/
├── package.json
├── server/
│   └── server.js              # Express + Socket.IO + game loop
├── client/
│   ├── host/                  # Laptop view (QR + canvas)
│   │   ├── index.html
│   │   ├── host.js
│   │   └── style.css
│   └── controller/            # Phone view (touch buttons)
│       ├── index.html
│       ├── controller.js
│       └── style.css
└── README.md
```

---

## Run locally

**Requires Node.js 18 or newer.**

```bash
# 1. Install dependencies
npm install

# 2. Start the server
npm start
```

You'll see:
```
🎮 Arena server listening on http://localhost:3000
   Host view:       http://localhost:3000/host/
   Controller view: http://localhost:3000/join?room=XXXX
```

### Testing on your laptop only

1. Open `http://localhost:3000/host/` in your laptop browser → you see the QR code.
2. Open another browser tab/window and visit the join URL shown beneath the QR code → that tab is now a "phone".
3. You can keep adding more tabs to simulate up to 4 players.

### Testing with real phones (same Wi-Fi)

The QR code points at `http://localhost:3000/...` which won't work from a phone. Two easy options:

**Option A — Use your computer's LAN IP**

1. Find your IP (e.g. `192.168.1.42`):
   - **macOS**: `ipconfig getifaddr en0`
   - **Windows**: `ipconfig` → look for "IPv4 Address"
   - **Linux**: `hostname -I`
2. On your laptop browser, visit `http://192.168.1.42:3000/host/` (replacing the IP).
3. Now the QR code uses that LAN address, and your phone (on the same Wi-Fi) can scan and connect.

**Option B — Use ngrok or Cloudflare Tunnel** (works from anywhere)

```bash
# In a second terminal, with the server already running:
npx ngrok http 3000
```

Open the `https://...ngrok-free.app/host/` URL on your laptop. The QR code will use the public URL, so any phone on any network can join.

---

## Deploy to production (free, in 5 minutes)

WebSockets need a real Node host — **not Vercel** (its serverless functions don't keep persistent connections). Use one of these:

### 🚀 Render (recommended, free)

1. Push this repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Web Service** → connect your repo.
3. Settings:
   - **Build command**: `npm install`
   - **Start command**: `npm start`
   - **Environment**: Node
4. Click **Create Web Service**. After ~1 minute you'll get a URL like `https://arena-game.onrender.com`.
5. Open `https://arena-game.onrender.com/host/` — done. The QR code will encode the public URL automatically.

### 🚂 Railway

1. Push to GitHub, sign in at [railway.app](https://railway.app).
2. **New Project** → **Deploy from GitHub repo** → select repo.
3. Railway auto-detects Node and runs `npm start`. You'll get a public URL.

### 🪂 Fly.io

```bash
brew install flyctl              # or appropriate installer
fly launch                       # accept defaults; choose a region
fly deploy
```

### About Vercel

Don't use Vercel for this. WebSockets through serverless functions are flaky and time-limited. The platforms above keep a long-lived Node process.

---

## Game rules

- 2–4 players spawn on a multi-tier platformer arena.
- Coins spawn randomly on platforms. Touching a coin = +1.
- **First player to 10 coins wins.**
- If a player falls off the world, they respawn from the top.

### Controls

| Action | Phone     | Keyboard (testing) |
|--------|-----------|--------------------|
| Move   | ◀ / ▶ buttons | A/D or ← / →  |
| Jump   | JUMP button   | W, ↑, or Space|

---

## Customization ideas

The server constants are at the top of `server/server.js`:

```js
const WIN_SCORE      = 10;     // change winning score
const MAX_PLAYERS    = 4;      // already capped by # of colors
const GRAVITY        = 0.6;
const MOVE_SPEED     = 5;
const JUMP_VELOCITY  = -13;    // more negative = higher jump
```

Edit `room.state.platforms` to redesign the arena, or add new game mechanics by changing the loop in `updateGame()`.

---

## Implementation notes

- **Authoritative server**: phones send only `{left, right, jump}` booleans; physics runs server-side at 60 Hz, then state is broadcast to the host.
- **Reconnection**: phones save their `playerId` to `localStorage` and silently rejoin if they lose connection. The host gets a 30-second grace window if they refresh.
- **Player limit**: Capped at 4 players (matching available colors); 5th joiner gets a friendly error.
- **No app required**: everything runs in the mobile browser, including QR scanning (the phone's native camera handles that).
- **CORS**: Open by default for easy development; restrict in `server.js` (`cors: { origin: ... }`) for production if needed.

---

## License

MIT