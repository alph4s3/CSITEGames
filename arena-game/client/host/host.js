/**
 * HOST CLIENT
 * Runs on the laptop / large screen. Responsibilities:
 *   1. Ask server for a fresh room and display QR code
 *   2. Show connected players in lobby
 *   3. Render the game (canvas) using server-broadcast state
 *   4. NEVER simulate physics locally - server is authoritative
 */

const socket = io();

// DOM refs
const lobby           = document.getElementById('lobby');
const gameScreen      = document.getElementById('game');
const gameOverScreen  = document.getElementById('game-over');
const startBtn        = document.getElementById('start-btn');
const roomCodeEl      = document.getElementById('room-code');
const joinUrlEl       = document.getElementById('join-url');
const qrEl            = document.getElementById('qrcode');
const playersListEl   = document.getElementById('players-list');
const playerCountEl   = document.getElementById('player-count');
const winnerTextEl    = document.getElementById('winner-text');
const backToLobbyBtn  = document.getElementById('back-to-lobby');
const finalScoresEl   = document.getElementById('final-scores');
const canvas          = document.getElementById('canvas');
const ctx             = canvas.getContext('2d');
const hud             = document.getElementById('hud');

let roomId = null;
let players = [];        // from `players-update`
let gameState = null;    // from `game-state-update`
const popups = [];       // floating "+1" effects on coin pickups

// ---------------------------------------------------------------------------
// Connect to server and request a room
// ---------------------------------------------------------------------------
socket.on('connect', () => {
  if (!roomId) socket.emit('create-room');
});

socket.on('room-created', ({ roomId: rid }) => {
  roomId = rid;
  const joinUrl = `${window.location.origin}/join?room=${rid}`;
  roomCodeEl.textContent = rid;
  joinUrlEl.textContent = joinUrl.replace(/^https?:\/\//, '');

  // Generate QR code for the join URL
  qrEl.innerHTML = '';
  QRCode.toCanvas(joinUrl, { width: 300, margin: 2, color: { dark: '#0b132b', light: '#ffffff' } },
    (err, c) => {
      if (err) console.error(err);
      else qrEl.appendChild(c);
    });
});

socket.on('players-update', ({ players: list }) => {
  players = list;
  renderPlayersList();
  startBtn.disabled = !list.some(p => p.connected);
});

socket.on('game-started', () => {
  hideAll();
  gameScreen.classList.remove('hidden');
});

socket.on('game-reset', () => {
  hideAll();
  lobby.classList.remove('hidden');
});

socket.on('game-state-update', (state) => {
  gameState = state;
});

socket.on('coin-collected', ({ x, y }) => {
  popups.push({ x: x + 8, y: y + 4, alpha: 1 });
});

socket.on('room-closed', () => {
  alert('Room closed.');
  location.reload();
});

socket.on('disconnect', () => {
  console.warn('Disconnected from server.');
});

// ---------------------------------------------------------------------------
// UI handlers
// ---------------------------------------------------------------------------
startBtn.addEventListener('click', () => socket.emit('start-game'));
backToLobbyBtn.addEventListener('click', () => socket.emit('reset-game'));

function hideAll() {
  lobby.classList.add('hidden');
  gameScreen.classList.add('hidden');
  gameOverScreen.classList.add('hidden');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => (
    { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]
  ));
}

function renderPlayersList() {
  playerCountEl.textContent = `(${players.length}/4)`;
  if (players.length === 0) {
    playersListEl.innerHTML = '<div class="empty">Waiting for players to scan the QR code…</div>';
    return;
  }
  playersListEl.innerHTML = players.map(p => `
    <div class="player-row ${p.connected ? '' : 'disconnected'}" style="border-left-color:${p.color}">
      <div class="player-color" style="background:${p.color};color:${p.color}"></div>
      <div class="player-name">${escapeHtml(p.name)}</div>
      <div class="player-status">${p.connected ? '● Ready' : 'Disconnected'}</div>
    </div>
  `).join('');
}

function showGameOver(state) {
  // Wait a short moment for the winning coin pickup to register visually
  setTimeout(() => {
    hideAll();
    gameOverScreen.classList.remove('hidden');

    const winner = state.winner;
    winnerTextEl.innerHTML = `<span style="color:${winner.color}">${escapeHtml(winner.name)}</span> wins!`;

    const sorted = [...state.players].sort((a, b) => b.score - a.score);
    finalScoresEl.innerHTML = sorted.map(p => `
      <div class="player-row" style="border-left-color:${p.color}">
        <div class="player-color" style="background:${p.color};color:${p.color}"></div>
        <div class="player-name">${escapeHtml(p.name)}</div>
        <div class="player-status" style="color:#fbbf24">${p.score} coins</div>
      </div>
    `).join('');
  }, 700);
}

// ---------------------------------------------------------------------------
// Render loop (60 fps independent of network)
// ---------------------------------------------------------------------------
let lastGameOverHandled = false;

function drawBackground() {
  // Sky gradient
  const grd = ctx.createLinearGradient(0, 0, 0, canvas.height);
  grd.addColorStop(0, '#1a2238');
  grd.addColorStop(1, '#293352');
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Pseudo-random stars (deterministic so they don't flicker)
  ctx.fillStyle = 'rgba(255,255,255,0.18)';
  for (let i = 0; i < 80; i++) {
    const x = (i * 137) % canvas.width;
    const y = (i * 71) % (canvas.height - 80);
    const s = (i % 3) + 1;
    ctx.fillRect(x, y, s, s);
  }

  // Distant mountains
  ctx.fillStyle = 'rgba(20,30,60,0.6)';
  ctx.beginPath();
  ctx.moveTo(0, canvas.height);
  for (let x = 0; x <= canvas.width; x += 80) {
    ctx.lineTo(x, canvas.height - 100 - Math.sin(x * 0.01) * 40 - (x % 240) * 0.2);
  }
  ctx.lineTo(canvas.width, canvas.height);
  ctx.closePath();
  ctx.fill();
}

function drawPlatforms(platforms) {
  for (const p of platforms) {
    // Drop shadow
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.fillRect(p.x + 4, p.y + 6, p.w, p.h);
    // Body
    ctx.fillStyle = '#3a4a7a';
    ctx.fillRect(p.x, p.y, p.w, p.h);
    // Top highlight
    ctx.fillStyle = '#5577bb';
    ctx.fillRect(p.x, p.y, p.w, 4);
  }
}

function drawCoins(coins) {
  const t = Date.now() / 220;
  for (const c of coins) {
    const wob = Math.sin(t + c.x * 0.05) * 3;
    const cx = c.x + 8;
    const cy = c.y + 8 + wob;

    // Glow
    const glow = ctx.createRadialGradient(cx, cy, 2, cx, cy, 18);
    glow.addColorStop(0, 'rgba(255, 213, 79, 0.55)');
    glow.addColorStop(1, 'rgba(255, 213, 79, 0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, 18, 0, Math.PI * 2);
    ctx.fill();

    // Coin
    ctx.fillStyle = '#ffd54f';
    ctx.beginPath();
    ctx.arc(cx, cy, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#b8860b';
    ctx.lineWidth = 2;
    ctx.stroke();
    // Shine
    ctx.fillStyle = '#fff8c4';
    ctx.beginPath();
    ctx.arc(cx - 2, cy - 2, 2.5, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawPlayers(playersArr) {
  for (const p of playersArr) {
    if (!p.connected) continue;
    const x = p.x, y = p.y, w = 36, h = 36;

    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    ctx.beginPath();
    ctx.ellipse(x + w / 2, y + h + 6, w / 2 - 4, 4, 0, 0, Math.PI * 2);
    ctx.fill();

    // Body
    ctx.fillStyle = p.color;
    roundRect(ctx, x, y, w, h, 8);
    ctx.fill();
    // Subtle inner outline
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(255,255,255,0.3)';
    ctx.stroke();

    // Eyes
    const eyeOffset = (p.facing || 1) > 0 ? 2 : -2;
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(x + 11 + eyeOffset, y + 14, 4, 0, Math.PI * 2);
    ctx.arc(x + 25 + eyeOffset, y + 14, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.arc(x + 12 + eyeOffset, y + 15, 2, 0, Math.PI * 2);
    ctx.arc(x + 26 + eyeOffset, y + 15, 2, 0, Math.PI * 2);
    ctx.fill();

    // Name tag
    ctx.font = 'bold 14px system-ui, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(0,0,0,0.55)';
    const nameW = ctx.measureText(p.name).width + 12;
    roundRect(ctx, x + w / 2 - nameW / 2, y - 24, nameW, 18, 6);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.fillText(p.name, x + w / 2, y - 10);
  }
}

function drawPopups() {
  ctx.font = 'bold 24px system-ui, sans-serif';
  ctx.textAlign = 'center';
  for (let i = popups.length - 1; i >= 0; i--) {
    const pop = popups[i];
    pop.y -= 1.2;
    pop.alpha -= 0.018;
    if (pop.alpha <= 0) { popups.splice(i, 1); continue; }
    ctx.fillStyle = `rgba(255,213,79,${pop.alpha})`;
    ctx.strokeStyle = `rgba(184,134,11,${pop.alpha})`;
    ctx.lineWidth = 3;
    ctx.strokeText('+1', pop.x, pop.y);
    ctx.fillText('+1', pop.x, pop.y);
  }
}

function renderHUD() {
  if (!gameState) return;
  hud.innerHTML = '';
  for (const p of gameState.players) {
    const item = document.createElement('div');
    item.className = 'hud-item';
    item.style.borderColor = p.color;
    if (!p.connected) item.style.opacity = '0.4';
    item.innerHTML = `
      <span class="hud-color" style="background:${p.color}"></span>
      <span class="hud-name">${escapeHtml(p.name)}</span>
      <span class="hud-score">${p.score}</span>
    `;
    hud.appendChild(item);
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y,     x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x,     y + h, r);
  ctx.arcTo(x,     y + h, x,     y,     r);
  ctx.arcTo(x,     y,     x + w, y,     r);
  ctx.closePath();
}

function render() {
  drawBackground();

  if (gameState) {
    drawPlatforms(gameState.platforms);
    drawCoins(gameState.coins);
    drawPlayers(gameState.players);
    drawPopups();
    renderHUD();

    // Trigger game-over screen once
    if (gameState.gameOver && gameState.winner && !lastGameOverHandled) {
      lastGameOverHandled = true;
      showGameOver(gameState);
    }
    if (!gameState.gameOver) lastGameOverHandled = false;
  }

  requestAnimationFrame(render);
}

requestAnimationFrame(render);