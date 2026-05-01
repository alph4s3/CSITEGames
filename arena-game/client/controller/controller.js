/**
 * CONTROLLER CLIENT
 * Runs on each player's phone. Responsibilities:
 *   1. Read room code (from ?room= URL param or input)
 *   2. Join the room over Socket.IO
 *   3. Send touch input (left/right/jump) to the server at ~20 Hz
 *   4. Show simple status (score, waiting, game over)
 *
 * NEVER renders the game. The host is the display.
 */

const socket = io();
const params = new URLSearchParams(location.search);
const initialRoomFromUrl = (params.get('room') || '').toUpperCase();

// DOM
const lobby      = document.getElementById('lobby');
const waiting    = document.getElementById('waiting');
const play       = document.getElementById('play');
const gameover   = document.getElementById('gameover');

const roomInput  = document.getElementById('room-input');
const nameInput  = document.getElementById('name-input');
const joinBtn    = document.getElementById('join-btn');
const errorMsg   = document.getElementById('error-msg');

const colorDot1  = document.getElementById('color-dot-1');
const colorDot2  = document.getElementById('color-dot-2');
const nameDisp1  = document.getElementById('name-display-1');
const nameDisp2  = document.getElementById('name-display-2');
const scoreEl    = document.getElementById('score');
const goverText  = document.getElementById('gameover-text');

// State
let myPlayerId = null;
let myRoomId   = null;
let myName     = '';
let myColor    = '#888';

// ---------------------------------------------------------------------------
// Pre-fill from URL + restore name from localStorage
// ---------------------------------------------------------------------------
if (initialRoomFromUrl) roomInput.value = initialRoomFromUrl;
const savedName = localStorage.getItem('arena-name');
if (savedName) nameInput.value = savedName;

// Auto-rejoin if we have a saved session for this room
const savedSession = JSON.parse(localStorage.getItem('arena-session') || 'null');
if (savedSession && savedSession.roomId === initialRoomFromUrl && savedSession.playerId) {
  attemptJoin(savedSession.roomId, savedSession.name || savedName || 'Player', savedSession.playerId);
}

// ---------------------------------------------------------------------------
// Lobby
// ---------------------------------------------------------------------------
joinBtn.addEventListener('click', () => {
  const room = (roomInput.value || '').trim().toUpperCase();
  const name = (nameInput.value || '').trim() || 'Player';
  if (!/^[A-Z0-9]{3,6}$/.test(room)) {
    showError('Enter a valid room code');
    return;
  }
  localStorage.setItem('arena-name', name);
  attemptJoin(room, name);
});

// Allow pressing Enter to join (helpful on mobile keyboards)
[roomInput, nameInput].forEach(el => {
  el.addEventListener('keydown', e => {
    if (e.key === 'Enter') joinBtn.click();
  });
});

function attemptJoin(room, name, playerId) {
  errorMsg.textContent = '';
  joinBtn.disabled = true;
  joinBtn.textContent = 'Joining…';
  socket.emit('join-room', { roomId: room, name, playerId });
}

function showError(msg) {
  errorMsg.textContent = msg;
  joinBtn.disabled = false;
  joinBtn.textContent = 'Join';
}

// ---------------------------------------------------------------------------
// Socket events
// ---------------------------------------------------------------------------
socket.on('room-error', ({ message }) => {
  showError(message);
  // Clear stale session
  localStorage.removeItem('arena-session');
  show(lobby);
});

socket.on('joined-room', ({ roomId, playerId, color, name, gameStarted, gameOver }) => {
  myRoomId   = roomId;
  myPlayerId = playerId;
  myName     = name;
  myColor    = color;

  localStorage.setItem('arena-session', JSON.stringify({ roomId, playerId, name }));

  // Apply color/name to UI
  colorDot1.style.background = color;
  colorDot1.style.color = color;
  colorDot2.style.background = color;
  colorDot2.style.color = color;
  nameDisp1.textContent = name;
  nameDisp2.textContent = name;
  scoreEl.textContent = '0';

  // Restore previous-button reset
  joinBtn.disabled = false;
  joinBtn.textContent = 'Join';

  // Decide which screen to show based on current game state
  if (gameStarted) show(play);
  else if (gameOver) show(gameover);
  else show(waiting);
});

socket.on('game-started', () => {
  scoreEl.textContent = '0';
  goverText.textContent = '';
  show(play);
});

socket.on('game-reset', () => {
  show(waiting);
});

socket.on('player-status', (s) => {
  scoreEl.textContent = s.score;
  if (s.gameOver && s.winner) {
    if (s.winner.id === myPlayerId) {
      goverText.innerHTML = `🎉 <strong>You win!</strong>`;
    } else {
      goverText.innerHTML = `<strong style="color:${s.winner.color}">${escapeHtml(s.winner.name)}</strong> wins!`;
    }
    show(gameover);
  }
});

socket.on('room-closed', () => {
  localStorage.removeItem('arena-session');
  alert('The host closed the room.');
  location.reload();
});

socket.on('disconnect', () => {
  console.warn('Disconnected from server.');
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function show(screen) {
  for (const s of [lobby, waiting, play, gameover]) s.classList.add('hidden');
  screen.classList.remove('hidden');
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => (
    { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]
  ));
}

// ---------------------------------------------------------------------------
// Input handling
// ---------------------------------------------------------------------------
const input = { left: false, right: false, jump: false };
let inputDirty = false;

function setInput(key, value) {
  if (input[key] === value) return;
  input[key] = value;
  inputDirty = true;
}

/**
 * Bind a button to a specific input key. Uses pointer events when available
 * for unified mouse + touch + stylus handling, with touch fallback.
 */
function bindButton(el, key) {
  const press   = (e) => { e.preventDefault(); setInput(key, true);  el.classList.add('active'); };
  const release = (e) => { e.preventDefault(); setInput(key, false); el.classList.remove('active'); };

  if (window.PointerEvent) {
    el.addEventListener('pointerdown', press);
    el.addEventListener('pointerup', release);
    el.addEventListener('pointercancel', release);
    el.addEventListener('pointerleave', release);
  } else {
    el.addEventListener('touchstart', press,  { passive: false });
    el.addEventListener('touchend',   release, { passive: false });
    el.addEventListener('touchcancel', release, { passive: false });
    el.addEventListener('mousedown', press);
    el.addEventListener('mouseup', release);
    el.addEventListener('mouseleave', release);
  }

  // Prevent the iOS double-tap-to-zoom from eating presses
  el.addEventListener('contextmenu', e => e.preventDefault());
}

bindButton(document.getElementById('btn-left'),  'left');
bindButton(document.getElementById('btn-right'), 'right');
bindButton(document.getElementById('btn-jump'),  'jump');

// Keyboard fallback for desktop testing
window.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  if (e.key === 'ArrowLeft'  || e.key === 'a' || e.key === 'A') setInput('left',  true);
  if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') setInput('right', true);
  if (e.key === ' '          || e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') setInput('jump', true);
});
window.addEventListener('keyup', (e) => {
  if (e.key === 'ArrowLeft'  || e.key === 'a' || e.key === 'A') setInput('left',  false);
  if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') setInput('right', false);
  if (e.key === ' '          || e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') setInput('jump', false);
});

/**
 * Send input to the server at fixed 20 Hz.
 * Only emit when state has changed OR while any button is held.
 * Also resend periodically when held to recover from any dropped packet.
 */
let lastSent = 0;
setInterval(() => {
  const now = Date.now();
  const anyPressed = input.left || input.right || input.jump;
  if (inputDirty || (anyPressed && now - lastSent > 100)) {
    socket.emit('player-input', input);
    inputDirty = false;
    lastSent = now;
  }
}, 50);

// Block iOS bounce / pinch / scroll while playing
document.addEventListener('touchmove',  e => e.preventDefault(), { passive: false });
document.addEventListener('gesturestart', e => e.preventDefault());