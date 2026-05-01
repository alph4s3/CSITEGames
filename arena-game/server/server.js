/**
 * Arena - Multiplayer Game Server
 *
 * Architecture:
 *   - Express serves static client files (host + controller views)
 *   - Socket.IO handles real-time messaging between host (laptop) and controllers (phones)
 *   - The server is authoritative: it runs the game loop, applies physics,
 *     and broadcasts game state to the host. Controllers only send inputs.
 *
 * Event protocol:
 *   Host -> Server:
 *     'create-room'      - Host requests a new room
 *     'start-game'       - Begin gameplay
 *     'reset-game'       - Return to lobby
 *
 *   Controller -> Server:
 *     'join-room'        - { roomId, name, playerId? } - join (or rejoin) a room
 *     'player-input'     - { left, right, jump } - current input state
 *
 *   Server -> Host:
 *     'room-created'     - { roomId }
 *     'players-update'   - { players[] }
 *     'game-state-update'- full game state (60 Hz)
 *     'coin-collected'   - { playerId, x, y } for visual fx
 *
 *   Server -> Controller:
 *     'joined-room'      - { roomId, playerId, color, name, slotIndex }
 *     'room-error'       - { message }
 *     'player-status'    - { score, gameStarted, gameOver, winner }
 *
 *   Server -> All in room:
 *     'game-started', 'game-reset', 'room-closed'
 */

const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  // Allow CORS - useful if you ever serve client from a different origin
  cors: { origin: '*' },
});

const PORT = process.env.PORT || 3000;

// ---- Static file serving --------------------------------------------------
// Host view: laptop / large screen
app.use('/host', express.static(path.join(__dirname, '..', 'client', 'host')));
// Controller view: mobile phone (served from /controller AND from /join?room=XXXX)
app.use('/controller', express.static(path.join(__dirname, '..', 'client', 'controller')));

// Root redirects to host
app.get('/', (req, res) => res.redirect('/host/'));

// /join?room=XXXX - the QR code target. Serves the controller HTML.
app.get('/join', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'client', 'controller', 'index.html'));
});

// Health check (helps with platforms like Render)
app.get('/healthz', (req, res) => res.json({ ok: true, rooms: rooms.size }));

// ---- Game configuration ---------------------------------------------------
const TICK_RATE = 60;                  // physics ticks per second
const TICK_MS = 1000 / TICK_RATE;
const PLAYER_COLORS = ['#ff5e5e', '#4fc3f7', '#7ed957', '#ffca28'];
const MAX_PLAYERS = PLAYER_COLORS.length;
const WIN_SCORE = 10;
const COIN_SIZE = 16;
const PLAYER_SIZE = 36;

const GRAVITY = 0.6;
const MOVE_SPEED = 5;
const JUMP_VELOCITY = -13;
const FRICTION = 0.82;
const MAX_FALL_SPEED = 18;

const WORLD_WIDTH = 1280;
const WORLD_HEIGHT = 720;

// ---- Room state -----------------------------------------------------------
/**
 * rooms: Map<roomId, {
 *   id, hostSocketId, players: Map<playerId, Player>, state, loopInterval, coinSpawnInterval
 * }>
 */
const rooms = new Map();

function generateRoomId() {
  // 4-character A-Z0-9 code (avoid 0/O, 1/I/L for legibility)
  const chars = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
  let id;
  do {
    id = '';
    for (let i = 0; i < 4; i++) id += chars[Math.floor(Math.random() * chars.length)];
  } while (rooms.has(id));
  return id;
}

function generatePlayerId() {
  return Math.random().toString(36).substring(2, 10);
}

function createRoom(hostSocketId) {
  const roomId = generateRoomId();
  const room = {
    id: roomId,
    hostSocketId,
    players: new Map(),
    state: {
      gameStarted: false,
      gameOver: false,
      winner: null,
      coins: [],
      // Hand-crafted platform layout - a nice arena
      platforms: [
        { x: 0, y: 680, w: WORLD_WIDTH, h: 40 },     // ground
        { x: 180, y: 540, w: 220, h: 20 },           // lower left
        { x: 880, y: 540, w: 220, h: 20 },           // lower right
        { x: 520, y: 460, w: 240, h: 20 },           // middle
        { x: 80,  y: 380, w: 180, h: 20 },           // mid left
        { x: 1020, y: 380, w: 180, h: 20 },          // mid right
        { x: 380, y: 280, w: 200, h: 20 },           // upper left
        { x: 700, y: 280, w: 200, h: 20 },           // upper right
        { x: 540, y: 160, w: 200, h: 20 },           // top
      ],
      worldWidth: WORLD_WIDTH,
      worldHeight: WORLD_HEIGHT,
    },
    loopInterval: null,
    coinSpawnInterval: null,
  };
  rooms.set(roomId, room);
  return room;
}

function destroyRoom(roomId) {
  const room = rooms.get(roomId);
  if (!room) return;
  if (room.loopInterval) clearInterval(room.loopInterval);
  if (room.coinSpawnInterval) clearInterval(room.coinSpawnInterval);
  rooms.delete(roomId);
}

// ---- Game logic -----------------------------------------------------------
function spawnCoin(room) {
  const platforms = room.state.platforms;
  const p = platforms[Math.floor(Math.random() * platforms.length)];
  const x = p.x + 20 + Math.random() * Math.max(0, p.w - 40 - COIN_SIZE);
  const y = p.y - COIN_SIZE - 8;
  room.state.coins.push({ id: Math.random().toString(36).slice(2, 10), x, y });
  // cap total
  if (room.state.coins.length > 8) room.state.coins.shift();
}

function startGameLoop(room) {
  if (room.loopInterval) return;
  // initial coins
  for (let i = 0; i < 4; i++) spawnCoin(room);

  room.loopInterval = setInterval(() => updateGame(room), TICK_MS);
  room.coinSpawnInterval = setInterval(() => {
    if (room.state.gameStarted && !room.state.gameOver && room.state.coins.length < 6) {
      spawnCoin(room);
    }
  }, 2200);
}

function stopGameLoop(room) {
  if (room.loopInterval) clearInterval(room.loopInterval);
  if (room.coinSpawnInterval) clearInterval(room.coinSpawnInterval);
  room.loopInterval = null;
  room.coinSpawnInterval = null;
}

function rectsOverlap(ax, ay, aw, ah, bx, by, bw, bh) {
  return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
}

function updateGame(room) {
  if (!room.state.gameStarted || room.state.gameOver) {
    return;
  }

  for (const player of room.players.values()) {
    if (!player.connected) continue;

    // ---- Apply input to velocity ----
    if (player.input.left)       player.vx = -MOVE_SPEED;
    else if (player.input.right) player.vx = MOVE_SPEED;
    else                         player.vx *= FRICTION;

    if (Math.abs(player.vx) < 0.05) player.vx = 0;

    // facing direction (for eyes)
    if (player.vx < -0.1) player.facing = -1;
    else if (player.vx > 0.1) player.facing = 1;

    if (player.input.jump && player.onGround) {
      player.vy = JUMP_VELOCITY;
      player.onGround = false;
    }

    // gravity
    player.vy += GRAVITY;
    if (player.vy > MAX_FALL_SPEED) player.vy = MAX_FALL_SPEED;

    // ---- Move and resolve platform collisions axis-by-axis (more robust) ----
    // X axis
    player.x += player.vx;
    for (const plat of room.state.platforms) {
      if (rectsOverlap(player.x, player.y, PLAYER_SIZE, PLAYER_SIZE, plat.x, plat.y, plat.w, plat.h)) {
        if (player.vx > 0) player.x = plat.x - PLAYER_SIZE;
        else if (player.vx < 0) player.x = plat.x + plat.w;
        player.vx = 0;
      }
    }
    // World horizontal bounds
    if (player.x < 0) { player.x = 0; player.vx = 0; }
    if (player.x + PLAYER_SIZE > WORLD_WIDTH) {
      player.x = WORLD_WIDTH - PLAYER_SIZE;
      player.vx = 0;
    }

    // Y axis
    player.y += player.vy;
    player.onGround = false;
    for (const plat of room.state.platforms) {
      if (rectsOverlap(player.x, player.y, PLAYER_SIZE, PLAYER_SIZE, plat.x, plat.y, plat.w, plat.h)) {
        if (player.vy > 0) {
          player.y = plat.y - PLAYER_SIZE;
          player.vy = 0;
          player.onGround = true;
        } else if (player.vy < 0) {
          player.y = plat.y + plat.h;
          player.vy = 0;
        }
      }
    }

    // Fell off world (failsafe) - respawn
    if (player.y > WORLD_HEIGHT + 200) {
      player.x = 100 + Math.random() * (WORLD_WIDTH - 200);
      player.y = -50;
      player.vx = 0;
      player.vy = 0;
    }

    // ---- Coin collection ----
    for (let i = room.state.coins.length - 1; i >= 0; i--) {
      const c = room.state.coins[i];
      if (rectsOverlap(player.x, player.y, PLAYER_SIZE, PLAYER_SIZE, c.x, c.y, COIN_SIZE, COIN_SIZE)) {
        room.state.coins.splice(i, 1);
        player.score += 1;
        // notify host so it can play a popup/sound
        io.to(room.hostSocketId).emit('coin-collected', {
          playerId: player.id, x: c.x, y: c.y,
        });
        if (player.score >= WIN_SCORE) {
          room.state.gameOver = true;
          room.state.winner = { id: player.id, name: player.name, color: player.color };
        }
      }
    }
  }

  broadcastState(room);

  // After broadcasting a winning state, stop the loop (host will show game-over)
  if (room.state.gameOver) {
    stopGameLoop(room);
  }
}

function publicPlayer(p) {
  return {
    id: p.id,
    name: p.name,
    color: p.color,
    x: p.x,
    y: p.y,
    vx: p.vx,
    vy: p.vy,
    score: p.score,
    facing: p.facing,
    connected: p.connected,
    onGround: p.onGround,
  };
}

function buildPublicState(room) {
  return {
    gameStarted: room.state.gameStarted,
    gameOver: room.state.gameOver,
    winner: room.state.winner,
    platforms: room.state.platforms,
    coins: room.state.coins,
    worldWidth: room.state.worldWidth,
    worldHeight: room.state.worldHeight,
    players: Array.from(room.players.values()).map(publicPlayer),
  };
}

function broadcastState(room) {
  const state = buildPublicState(room);
  io.to(room.hostSocketId).emit('game-state-update', state);

  // Lightweight per-player status for controllers
  for (const p of room.players.values()) {
    if (p.connected && p.socketId) {
      io.to(p.socketId).emit('player-status', {
        score: p.score,
        gameStarted: room.state.gameStarted,
        gameOver: room.state.gameOver,
        winner: room.state.winner,
      });
    }
  }
}

function broadcastPlayersList(room) {
  io.to(room.hostSocketId).emit('players-update', {
    players: Array.from(room.players.values()).map(p => ({
      id: p.id, name: p.name, color: p.color,
      connected: p.connected, score: p.score,
    })),
  });
}

// ---- Socket handlers ------------------------------------------------------
io.on('connection', (socket) => {
  console.log(`[connect] ${socket.id}`);

  // ----- Host: create a fresh room -----
  socket.on('create-room', () => {
    const room = createRoom(socket.id);
    socket.join(room.id);
    socket.data.role = 'host';
    socket.data.roomId = room.id;
    socket.emit('room-created', { roomId: room.id });
    console.log(`[room] created ${room.id} by host ${socket.id}`);
  });

  // ----- Controller: join (or rejoin) a room -----
  socket.on('join-room', ({ roomId, name, playerId }) => {
    roomId = (roomId || '').toUpperCase().trim();
    const room = rooms.get(roomId);
    if (!room) {
      socket.emit('room-error', { message: 'Room not found' });
      return;
    }

    // Reconnection path: same playerId already exists
    let player = playerId ? room.players.get(playerId) : null;

    if (player) {
      // re-attach this socket
      player.connected = true;
      player.socketId = socket.id;
      // If they reconnect mid-game, keep their position
    } else {
      if (room.players.size >= MAX_PLAYERS) {
        socket.emit('room-error', { message: `Room is full (${MAX_PLAYERS} max)` });
        return;
      }
      const slotIndex = room.players.size;
      const id = generatePlayerId();
      player = {
        id,
        socketId: socket.id,
        name: (name || `Player ${slotIndex + 1}`).slice(0, 12),
        color: PLAYER_COLORS[slotIndex % PLAYER_COLORS.length],
        slotIndex,
        x: 200 + slotIndex * 120,
        y: 400,
        vx: 0,
        vy: 0,
        onGround: false,
        score: 0,
        facing: 1,
        connected: true,
        input: { left: false, right: false, jump: false },
      };
      room.players.set(id, player);
    }

    socket.join(roomId);
    socket.data.role = 'controller';
    socket.data.roomId = roomId;
    socket.data.playerId = player.id;

    socket.emit('joined-room', {
      roomId,
      playerId: player.id,
      color: player.color,
      name: player.name,
      slotIndex: player.slotIndex,
      gameStarted: room.state.gameStarted,
      gameOver: room.state.gameOver,
    });

    broadcastPlayersList(room);
    broadcastState(room);
    console.log(`[room ${roomId}] ${player.name} joined (${player.id})`);
  });

  // ----- Host: start the game -----
  socket.on('start-game', () => {
    const room = rooms.get(socket.data.roomId);
    if (!room || room.hostSocketId !== socket.id) return;
    if (room.players.size === 0) return;

    // Reset positions and scores
    let i = 0;
    for (const p of room.players.values()) {
      p.x = 180 + i * 140;
      p.y = 400;
      p.vx = 0;
      p.vy = 0;
      p.score = 0;
      p.input = { left: false, right: false, jump: false };
      i++;
    }
    room.state.coins = [];
    room.state.gameStarted = true;
    room.state.gameOver = false;
    room.state.winner = null;

    startGameLoop(room);
    io.to(room.id).emit('game-started');
    broadcastState(room);
    console.log(`[room ${room.id}] game started`);
  });

  // ----- Host: back to lobby / play again -----
  socket.on('reset-game', () => {
    const room = rooms.get(socket.data.roomId);
    if (!room || room.hostSocketId !== socket.id) return;
    stopGameLoop(room);
    room.state.gameStarted = false;
    room.state.gameOver = false;
    room.state.winner = null;
    room.state.coins = [];
    for (const p of room.players.values()) {
      p.score = 0;
      p.x = 200; p.y = 400; p.vx = 0; p.vy = 0;
      p.input = { left: false, right: false, jump: false };
    }
    io.to(room.id).emit('game-reset');
    broadcastPlayersList(room);
    broadcastState(room);
  });

  // ----- Controller: input -----
  socket.on('player-input', (input) => {
    const room = rooms.get(socket.data.roomId);
    if (!room) return;
    const player = room.players.get(socket.data.playerId);
    if (!player) return;
    // Sanitize - we only care about three booleans
    player.input.left  = !!(input && input.left);
    player.input.right = !!(input && input.right);
    player.input.jump  = !!(input && input.jump);
  });

  // ----- Disconnect handling -----
  socket.on('disconnect', (reason) => {
    console.log(`[disconnect] ${socket.id} (${reason})`);
    const roomId = socket.data.roomId;
    if (!roomId) return;
    const room = rooms.get(roomId);
    if (!room) return;

    if (socket.data.role === 'host' && room.hostSocketId === socket.id) {
      // Host vanished. Give a short grace period in case they refresh, then close.
      console.log(`[room ${roomId}] host disconnected, closing in 30s if not reclaimed`);
      stopGameLoop(room);
      const closeTimer = setTimeout(() => {
        const r = rooms.get(roomId);
        if (r && r.hostSocketId === socket.id) {
          io.to(roomId).emit('room-closed');
          destroyRoom(roomId);
          console.log(`[room ${roomId}] closed (host did not reconnect)`);
        }
      }, 30_000);
      room._closeTimer = closeTimer;
    } else if (socket.data.role === 'controller') {
      const player = room.players.get(socket.data.playerId);
      if (player) {
        player.connected = false;
        player.input = { left: false, right: false, jump: false };
        broadcastPlayersList(room);
      }
    }
  });
});

server.listen(PORT, () => {
  console.log(`\n🎮 Arena server listening on http://localhost:${PORT}`);
  console.log(`   Host view:       http://localhost:${PORT}/host/`);
  console.log(`   Controller view: http://localhost:${PORT}/join?room=XXXX\n`);
});