"""
=================================================================
  CSITE LOGIC DUEL  --  HOST GAME (Pygame + Flask + SocketIO)
=================================================================
Run on the booth laptop. Generates a QR code that Player 2 scans
with their phone to join over the local hotspot.

REQUIREMENTS
------------
    pip install pygame flask flask-socketio "qrcode[pil]" pillow

USAGE
-----
    1. Turn on a phone hotspot (or any local WiFi).
    2. Connect the booth laptop to that hotspot.
    3. Place host_game.py and client.html in the SAME folder.
    4. Run:   python host_game.py
    5. Click "START 1v1 DUEL" on the laptop.
    6. Player 2 points their phone camera at the QR code on screen.
       Their phone opens the client page automatically.
    7. Once Player 2 connects, the duel begins!

NOTES
-----
* No internet required after the libraries are installed.
* Both devices must be on the SAME network (the hotspot).
* If your firewall blocks port 5000, allow it once when prompted.
=================================================================
"""

import os
import sys
import time
import socket
import random
import threading

import pygame
import qrcode
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit

# =================================================================
# CONFIGURATION
# =================================================================

WIDTH, HEIGHT = 1280, 720
FPS = 60
PORT = 5000

# Round timings (seconds)
ROUND_DURATION = 30           # Time to answer each puzzle
RESULT_DURATION = 3.5         # Time the round-result screen is shown
COUNTDOWN_DURATION = 3.0      # Pre-game countdown after both players join

# --- Cyber/neon palette (booth aesthetic) -----------------------
BG_DEEP        = (8, 12, 28)
BG_MID         = (16, 22, 50)
GRID_LINE      = (40, 55, 95)
NEON_CYAN      = (60, 220, 250)
NEON_PINK      = (255, 90, 200)
NEON_PURPLE    = (160, 100, 255)
NEON_YELLOW    = (255, 215, 80)
NEON_GREEN     = (90, 245, 160)
NEON_RED       = (255, 90, 110)
WHITE          = (245, 248, 255)
GRAY           = (165, 175, 205)
DARK_PANEL     = (20, 26, 55)
DARKER_PANEL   = (14, 18, 40)

P1_COLOR       = NEON_CYAN
P2_COLOR       = NEON_PINK


# =================================================================
# QUESTION BANK
# 6 puzzle categories: Fibonacci, Pattern, Logic, Binary/Gates,
# Algorithm, CS Riddle. Each option list has 4 entries; "answer"
# is the index (0-3) of the correct option.
# =================================================================

QUESTION_BANK = [
    # ---------- FIBONACCI ----------
    {"type": "FIBONACCI", "q": "What's the next Fibonacci number?\n1, 1, 2, 3, 5, 8, ?",
     "options": ["11", "12", "13", "14"], "answer": 2},
    {"type": "FIBONACCI", "q": "Fill in the missing number:\n0, 1, 1, 2, 3, 5, ?",
     "options": ["6", "7", "8", "9"], "answer": 2},
    {"type": "FIBONACCI", "q": "What comes next?\n5, 8, 13, 21, ?",
     "options": ["29", "33", "34", "42"], "answer": 2},
    {"type": "FIBONACCI", "q": "Find the missing number:\n1, 1, 2, ?, 5, 8",
     "options": ["2", "3", "4", "6"], "answer": 1},
    {"type": "FIBONACCI", "q": "Fibonacci leap!\n13, 21, 34, ?",
     "options": ["47", "53", "55", "67"], "answer": 2},

    # ---------- PATTERN ----------
    {"type": "PATTERN", "q": "Doubling pattern:\n2, 4, 8, 16, ?",
     "options": ["24", "30", "32", "64"], "answer": 2},
    {"type": "PATTERN", "q": "Squares!\n1, 4, 9, 16, ?",
     "options": ["20", "24", "25", "36"], "answer": 2},
    {"type": "PATTERN", "q": "Cubes only:\n1, 8, 27, 64, ?",
     "options": ["100", "125", "128", "216"], "answer": 1},
    {"type": "PATTERN", "q": "Primes only:\n2, 3, 5, 7, 11, ?",
     "options": ["12", "13", "14", "15"], "answer": 1},
    {"type": "PATTERN", "q": "Triple it!\n1, 3, 9, 27, ?",
     "options": ["54", "63", "81", "108"], "answer": 2},
    {"type": "PATTERN", "q": "Triangular numbers:\n1, 3, 6, 10, ?",
     "options": ["12", "13", "15", "16"], "answer": 2},

    # ---------- LOGIC ----------
    {"type": "LOGIC", "q": "All CSITE students code.\nAlex is a CSITE student.\nTherefore, Alex...",
     "options": ["might code", "does NOT code", "codes", "is a teacher"], "answer": 2},
    {"type": "LOGIC", "q": "If A > B and B > C,\nwhich must be TRUE?",
     "options": ["A < C", "A = C", "A > C", "Cannot tell"], "answer": 2},
    {"type": "LOGIC", "q": "If it rains, ground is wet.\nGround is NOT wet.\nSo...",
     "options": ["It rained", "It did NOT rain", "Maybe it rained", "Cannot tell"], "answer": 1},
    {"type": "LOGIC", "q": "Mia > Sam (height).\nSam > Lee (height).\nWho is shortest?",
     "options": ["Mia", "Sam", "Lee", "Cannot tell"], "answer": 2},
    {"type": "LOGIC", "q": "All bugs are errors.\nNo error is wanted.\nSo bugs are...",
     "options": ["wanted", "not wanted", "fixed", "ignored"], "answer": 1},

    # ---------- BINARY / LOGIC GATES ----------
    {"type": "BINARY", "q": "Convert binary 1011\nto decimal:",
     "options": ["9", "10", "11", "12"], "answer": 2},
    {"type": "BINARY", "q": "Convert binary 1100\nto decimal:",
     "options": ["10", "11", "12", "14"], "answer": 2},
    {"type": "BINARY", "q": "Convert binary 11111\nto decimal:",
     "options": ["29", "30", "31", "32"], "answer": 2},
    {"type": "BINARY", "q": "Decimal 8 in binary?",
     "options": ["111", "1000", "1010", "1100"], "answer": 1},
    {"type": "GATE",   "q": "1 AND 0 = ?",
     "options": ["0", "1", "Both", "Error"], "answer": 0},
    {"type": "GATE",   "q": "1 OR 0 = ?",
     "options": ["0", "1", "Both", "Error"], "answer": 1},
    {"type": "GATE",   "q": "1 XOR 1 = ?",
     "options": ["0", "1", "2", "Error"], "answer": 0},
    {"type": "GATE",   "q": "NOT (1) = ?",
     "options": ["0", "1", "-1", "Null"], "answer": 0},

    # ---------- ALGORITHM ----------
    {"type": "ALGORITHM", "q": "Average time complexity\nof Merge Sort?",
     "options": ["O(n)", "O(n log n)", "O(n^2)", "O(log n)"], "answer": 1},
    {"type": "ALGORITHM", "q": "A Stack uses which order?",
     "options": ["FIFO", "LIFO", "Random", "Priority"], "answer": 1},
    {"type": "ALGORITHM", "q": "A Queue uses which order?",
     "options": ["FIFO", "LIFO", "Random", "Priority"], "answer": 0},
    {"type": "ALGORITHM", "q": "Binary search needs the\narray to be...",
     "options": ["empty", "random", "sorted", "small"], "answer": 2},
    {"type": "ALGORITHM", "q": "Smallest growth rate?",
     "options": ["O(n)", "O(log n)", "O(n^2)", "O(n!)"], "answer": 1},
    {"type": "ALGORITHM", "q": "Recursion always needs\na...",
     "options": ["loop", "base case", "class", "library"], "answer": 1},

    # ---------- CS RIDDLES ----------
    {"type": "CS RIDDLE", "q": "Smallest unit of digital\ninformation?",
     "options": ["Byte", "Bit", "Pixel", "Atom"], "answer": 1},
    {"type": "CS RIDDLE", "q": "How many bits in\none byte?",
     "options": ["4", "8", "16", "32"], "answer": 1},
    {"type": "CS RIDDLE", "q": "What does HTML\nstand for?",
     "options": ["Hyper Text Mark Lang", "Home Text Mark Lang",
                 "HyperText Markup Language", "High Text Make Lang"], "answer": 2},
    {"type": "CS RIDDLE", "q": "Most popular language\nfor AI / Machine Learning?",
     "options": ["Java", "Python", "C++", "PHP"], "answer": 1},
    {"type": "CS RIDDLE", "q": "The acronym 'CPU'\nstands for?",
     "options": ["Computer Power Unit", "Central Process Util",
                 "Central Processing Unit", "Core Programming Unit"], "answer": 2},
    {"type": "CS RIDDLE", "q": "1 KB equals how\nmany bytes?",
     "options": ["100", "256", "512", "1024"], "answer": 3},
]


# =================================================================
# UTILITIES
# =================================================================

def get_local_ip() -> str:
    """Return the machine's LAN IP (works without internet)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # We don't actually send anything; this just picks the right interface
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except OSError:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def make_qr_surface(url: str, size: int = 380) -> pygame.Surface:
    """Generate a Pygame Surface containing a QR code for the given URL."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    pil_img = pil_img.resize((size, size))
    return pygame.image.fromstring(pil_img.tobytes(), pil_img.size, pil_img.mode)


def wrap_lines(text: str, font: pygame.font.Font, max_width: int):
    """Word-wrap a (possibly multi-line) string into a list of strings."""
    out = []
    for paragraph in text.split("\n"):
        if not paragraph:
            out.append("")
            continue
        words = paragraph.split(" ")
        line = ""
        for w in words:
            test = (line + " " + w).strip()
            if font.size(test)[0] <= max_width:
                line = test
            else:
                if line:
                    out.append(line)
                line = w
        if line:
            out.append(line)
    return out


# =================================================================
# GAME STATE  (shared between Pygame thread and SocketIO thread)
# =================================================================

class GameState:
    """Thread-safe game state machine."""

    PHASES = ("MENU", "WAITING", "COUNTDOWN", "QUESTION",
              "ROUND_RESULT", "GAME_OVER")

    def __init__(self):
        self.lock = threading.RLock()

        # Connection
        self.p2_connected = False
        self.p2_sid = None

        # Persistent settings
        self.bo_target = 3            # 3 -> Best of 5  |  4 -> Best of 7

        # Round/game state
        self.phase = "MENU"
        self.phase_start = time.time()
        self.p1_score = 0
        self.p2_score = 0
        self.current_round = 0
        self.current_player = 1       # whose turn it is
        self.question = None
        self.last_result = None       # dict describing what just happened
        self.winner = None
        self.used_indices = set()

    # ---- public API used by Pygame side ---------------------------

    def go_to_menu(self):
        with self.lock:
            self.phase = "MENU"
            self.phase_start = time.time()
            self._broadcast_locked()

    def begin_waiting(self):
        with self.lock:
            self.phase = "WAITING"
            self.phase_start = time.time()
            self._broadcast_locked()

    def set_bo(self, target: int):
        with self.lock:
            if self.phase in ("MENU", "WAITING"):
                self.bo_target = target
                self._broadcast_locked()

    def start_match(self) -> bool:
        """Called when both players are ready; transitions to COUNTDOWN."""
        with self.lock:
            if not self.p2_connected:
                return False
            self._reset_match_locked()
            self.phase = "COUNTDOWN"
            self.phase_start = time.time()
            self._broadcast_locked()
            return True

    def submit_p1_answer(self, idx: int):
        with self.lock:
            if self.phase == "QUESTION" and self.current_player == 1:
                self._evaluate_locked(idx, player=1)

    def submit_p2_answer(self, idx: int):
        with self.lock:
            if self.phase == "QUESTION" and self.current_player == 2:
                self._evaluate_locked(idx, player=2)

    def tick(self):
        """Called every frame on the Pygame thread to advance timers."""
        with self.lock:
            now = time.time()
            elapsed = now - self.phase_start

            if self.phase == "COUNTDOWN":
                if elapsed >= COUNTDOWN_DURATION:
                    self._next_question_locked()
                else:
                    # Push periodic state so client sees the countdown ticking
                    self._broadcast_throttled_locked(now)

            elif self.phase == "QUESTION":
                if elapsed >= ROUND_DURATION:
                    self._evaluate_locked(-1, player=self.current_player,
                                          timeout=True)
                else:
                    self._broadcast_throttled_locked(now)

            elif self.phase == "ROUND_RESULT":
                if elapsed >= RESULT_DURATION:
                    if self.winner is not None:
                        self.phase = "GAME_OVER"
                        self.phase_start = now
                        self._broadcast_locked()
                    else:
                        self.current_player = 2 if self.current_player == 1 else 1
                        self._next_question_locked()

    # ---- helpers (assume lock held) ------------------------------

    _last_broadcast = 0.0

    def _broadcast_throttled_locked(self, now: float):
        """Avoid spamming the socket; refresh ~3x per second."""
        if now - self._last_broadcast > 0.33:
            self._last_broadcast = now
            self._broadcast_locked()

    def _reset_match_locked(self):
        self.p1_score = 0
        self.p2_score = 0
        self.current_round = 0
        self.current_player = random.choice([1, 2])
        self.question = None
        self.last_result = None
        self.winner = None
        self.used_indices = set()

    def _next_question_locked(self):
        available = [i for i in range(len(QUESTION_BANK))
                     if i not in self.used_indices]
        if not available:
            self.used_indices.clear()
            available = list(range(len(QUESTION_BANK)))
        idx = random.choice(available)
        self.used_indices.add(idx)
        self.question = QUESTION_BANK[idx]
        self.current_round += 1
        self.last_result = None
        self.phase = "QUESTION"
        self.phase_start = time.time()
        self._broadcast_locked()

    def _evaluate_locked(self, selected_idx: int, player: int,
                         timeout: bool = False):
        if self.phase != "QUESTION":
            return
        correct = (not timeout) and (selected_idx == self.question["answer"])

        # Award point: correct -> active player; wrong/timeout -> opponent
        if correct:
            if player == 1:
                self.p1_score += 1
            else:
                self.p2_score += 1
        else:
            if player == 1:
                self.p2_score += 1
            else:
                self.p1_score += 1

        self.last_result = {
            "player": player,
            "correct": correct,
            "timeout": timeout,
            "selected": selected_idx,
            "answer": self.question["answer"],
            "options": self.question["options"],
            "type": self.question["type"],
        }

        # Win check
        if self.p1_score >= self.bo_target:
            self.winner = 1
        elif self.p2_score >= self.bo_target:
            self.winner = 2

        self.phase = "ROUND_RESULT"
        self.phase_start = time.time()
        self._broadcast_locked()

    def _broadcast_locked(self):
        """Send a state snapshot to the web client."""
        snap = {
            "phase": self.phase,
            "p1_score": self.p1_score,
            "p2_score": self.p2_score,
            "round": self.current_round,
            "current_player": self.current_player,
            "p2_connected": self.p2_connected,
            "bo_target": self.bo_target,
            "question": self.question,
            "time_left": max(0, int(ROUND_DURATION
                                    - (time.time() - self.phase_start)))
                          if self.phase == "QUESTION" else 0,
            "countdown": max(0, int(COUNTDOWN_DURATION
                                    - (time.time() - self.phase_start)) + 1)
                          if self.phase == "COUNTDOWN" else 0,
            "last_result": self.last_result,
            "winner": self.winner,
        }
        # emit() outside the lock would be ideal, but Flask-SocketIO's emit is
        # thread-safe and non-blocking enough for our scale (1 client).
        try:
            socketio.emit("state", snap)
        except Exception:
            pass


state = GameState()


# =================================================================
# FLASK + SOCKETIO SERVER  (runs in a background thread)
# =================================================================

app = Flask(__name__)
app.config["SECRET_KEY"] = "csite-logic-duel-secret"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


SOCKETIO_JS_NAME = "socket.io.min.js"
SOCKETIO_JS_CDN  = "https://cdn.socket.io/4.7.5/socket.io.min.js"


def ensure_socketio_client():
    """Cache socket.io.min.js next to this script so phones can load it
    without needing internet. Only attempted on first run."""
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, SOCKETIO_JS_NAME)
    if os.path.exists(target) and os.path.getsize(target) > 1000:
        return
    try:
        import urllib.request
        print(f"[CSITE] First-run: downloading {SOCKETIO_JS_NAME} (~60KB)...")
        req = urllib.request.Request(
            SOCKETIO_JS_CDN,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
        with open(target, "wb") as f:
            f.write(data)
        print("[CSITE] Cached for offline use.")
    except Exception as e:
        print(f"[CSITE] Could not download socket.io.js ({e}).")
        print(f"[CSITE] If your phone has data, the client will fall back to CDN.")


@app.route("/")
def serve_client():
    """Serve client.html sitting next to this script."""
    here = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(here, "client.html")


@app.route("/socket.io.min.js")
def serve_socketio_js():
    """Serve a locally-cached copy of the Socket.IO client (for offline)."""
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(here, SOCKETIO_JS_NAME)):
        return send_from_directory(here, SOCKETIO_JS_NAME,
                                    mimetype="application/javascript")
    return ("// socket.io.min.js not cached; client will use CDN fallback\n",
            404, {"Content-Type": "application/javascript"})


@socketio.on("connect")
def on_connect():
    # Send current state immediately so the client can render the right view.
    with state.lock:
        snap_phase = state.phase
    emit("hello", {"msg": "connected", "phase": snap_phase})


@socketio.on("p2_join")
def on_p2_join():
    """Player 2 (phone) registers as the joining player."""
    with state.lock:
        state.p2_connected = True
        state.p2_sid = request.sid
        state._broadcast_locked()


@socketio.on("p2_answer")
def on_p2_answer(data):
    try:
        idx = int(data.get("idx", -1))
    except (TypeError, ValueError):
        idx = -1
    state.submit_p2_answer(idx)


@socketio.on("disconnect")
def on_disconnect():
    with state.lock:
        if request.sid == state.p2_sid:
            state.p2_connected = False
            state.p2_sid = None
            state._broadcast_locked()


def run_server():
    # allow_unsafe_werkzeug=True is needed in newer Flask-SocketIO versions
    # because we're using the dev server in production-ish mode (fine for booth).
    try:
        socketio.run(app, host="0.0.0.0", port=PORT, debug=False,
                     allow_unsafe_werkzeug=True)
    except TypeError:
        socketio.run(app, host="0.0.0.0", port=PORT, debug=False)


# =================================================================
# PYGAME UI
# =================================================================

class Button:
    def __init__(self, rect, text, fill, glow, action=None, font_key="big",
                 disabled=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.fill = fill
        self.glow = glow
        self.action = action
        self.font_key = font_key
        self.disabled = disabled

    def draw(self, screen, fonts):
        mouse = pygame.mouse.get_pos()
        hover = self.rect.collidepoint(mouse) and not self.disabled

        # outer glow
        glow_color = self.glow if not self.disabled else (60, 60, 80)
        for i in range(6, 0, -1):
            grow = pygame.Rect(self.rect.left - i, self.rect.top - i,
                               self.rect.width + 2 * i, self.rect.height + 2 * i)
            alpha = 25 + (10 if hover else 0)
            s = pygame.Surface((grow.width, grow.height), pygame.SRCALPHA)
            pygame.draw.rect(s, (*glow_color, alpha),
                             s.get_rect(), border_radius=14)
            screen.blit(s, grow.topleft)

        # body
        body_color = self.fill
        if hover:
            body_color = tuple(min(255, c + 25) for c in self.fill)
        if self.disabled:
            body_color = (45, 50, 80)
        pygame.draw.rect(screen, body_color, self.rect, border_radius=12)
        pygame.draw.rect(screen, glow_color, self.rect, width=2,
                         border_radius=12)

        # label
        f = fonts[self.font_key]
        label = f.render(self.text, True, WHITE if not self.disabled else GRAY)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def click(self, pos):
        if self.disabled:
            return False
        if self.rect.collidepoint(pos) and self.action:
            self.action()
            return True
        return False


def draw_grid_bg(screen, t):
    """Subtle animated cyber grid background."""
    screen.fill(BG_DEEP)
    # vertical gradient
    for y in range(0, HEIGHT, 4):
        ratio = y / HEIGHT
        c = (
            int(BG_DEEP[0] * (1 - ratio) + BG_MID[0] * ratio),
            int(BG_DEEP[1] * (1 - ratio) + BG_MID[1] * ratio),
            int(BG_DEEP[2] * (1 - ratio) + BG_MID[2] * ratio),
        )
        pygame.draw.rect(screen, c, (0, y, WIDTH, 4))
    # animated grid
    offset = int(t * 25) % 40
    for x in range(-offset, WIDTH, 40):
        pygame.draw.line(screen, GRID_LINE, (x, 0), (x, HEIGHT), 1)
    for y in range(-offset, HEIGHT, 40):
        pygame.draw.line(screen, GRID_LINE, (0, y), (WIDTH, y), 1)
    # corner accents
    pygame.draw.line(screen, NEON_CYAN, (0, 0), (60, 0), 3)
    pygame.draw.line(screen, NEON_CYAN, (0, 0), (0, 60), 3)
    pygame.draw.line(screen, NEON_PINK, (WIDTH, 0), (WIDTH - 60, 0), 3)
    pygame.draw.line(screen, NEON_PINK, (WIDTH, 0), (WIDTH, 60), 3)
    pygame.draw.line(screen, NEON_PINK, (0, HEIGHT), (60, HEIGHT), 3)
    pygame.draw.line(screen, NEON_PINK, (0, HEIGHT), (0, HEIGHT - 60), 3)
    pygame.draw.line(screen, NEON_CYAN, (WIDTH, HEIGHT), (WIDTH - 60, HEIGHT), 3)
    pygame.draw.line(screen, NEON_CYAN, (WIDTH, HEIGHT), (WIDTH, HEIGHT - 60), 3)


def draw_neon_text(screen, font, text, center, color, glow_color=None):
    """Render text with a soft neon glow."""
    if glow_color is None:
        glow_color = color
    glow_surf = font.render(text, True, glow_color)
    rect = glow_surf.get_rect(center=center)
    for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        screen.blit(glow_surf, rect.move(ox, oy))
    main = font.render(text, True, color)
    screen.blit(main, rect)


# ---------------- Scene drawers ----------------

def draw_menu(screen, fonts, buttons, t):
    draw_grid_bg(screen, t)

    # Title
    pulse = 1.0 + 0.04 * (1 + pygame.math.Vector2(0, 1).rotate(t * 80).y)
    title_font = fonts["title"]
    draw_neon_text(screen, title_font, "CSITE",
                   (WIDTH // 2, 130), NEON_CYAN, NEON_CYAN)
    draw_neon_text(screen, title_font, "LOGIC DUEL",
                   (WIDTH // 2, 230), NEON_PINK, NEON_PINK)

    # Subtitle
    sub = fonts["medium"].render(
        "1v1 Brain-Teaser Battle  ::  Booth Edition",
        True, NEON_YELLOW)
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 305)))

    # BO selector header
    bo_label = fonts["small"].render("FORMAT", True, GRAY)
    screen.blit(bo_label, bo_label.get_rect(center=(WIDTH // 2, 370)))

    # Render the BO buttons (already in `buttons`)
    # along with the START button.
    for b in buttons:
        b.draw(screen, fonts)

    # Highlight active BO
    with state.lock:
        active = state.bo_target
    if active == 3:
        pygame.draw.rect(screen, NEON_GREEN,
                         buttons[0].rect.inflate(8, 8), 3, border_radius=14)
    else:
        pygame.draw.rect(screen, NEON_GREEN,
                         buttons[1].rect.inflate(8, 8), 3, border_radius=14)

    # Footer
    foot = fonts["small"].render(
        "Player 1 plays here  +  Player 2 plays on phone via QR",
        True, GRAY)
    screen.blit(foot, foot.get_rect(center=(WIDTH // 2, HEIGHT - 30)))


def draw_waiting(screen, fonts, qr_surface, url, t):
    draw_grid_bg(screen, t)

    # Header
    draw_neon_text(screen, fonts["big"], "PLAYER 2: SCAN TO JOIN",
                   (WIDTH // 2, 70), NEON_PINK, NEON_PINK)

    # QR panel
    qr_size = qr_surface.get_width()
    panel = pygame.Rect(WIDTH // 2 - qr_size // 2 - 25,
                        140,
                        qr_size + 50,
                        qr_size + 50)
    pygame.draw.rect(screen, WHITE, panel, border_radius=18)
    pygame.draw.rect(screen, NEON_PINK, panel, width=4, border_radius=18)
    screen.blit(qr_surface, (panel.x + 25, panel.y + 25))

    # URL text
    url_text = fonts["medium"].render(url, True, NEON_CYAN)
    screen.blit(url_text, url_text.get_rect(center=(WIDTH // 2, panel.bottom + 40)))

    # Status
    with state.lock:
        connected = state.p2_connected

    if connected:
        msg = "PLAYER 2 CONNECTED!  Click START to begin."
        col = NEON_GREEN
    else:
        dots = "." * (int(t * 2) % 4)
        msg = f"Waiting for Player 2{dots}"
        col = NEON_YELLOW
    status = fonts["medium"].render(msg, True, col)
    screen.blit(status, status.get_rect(center=(WIDTH // 2, panel.bottom + 90)))

    # Side instructions panel
    inst_lines = [
        "HOW TO JOIN:",
        "1. Open phone camera",
        "2. Point at QR code",
        "3. Tap the link",
        "4. Wait for game to start",
    ]
    side_x = 60
    side_y = 200
    pygame.draw.rect(screen, DARK_PANEL,
                     (side_x - 20, side_y - 20, 280, 220),
                     border_radius=14)
    pygame.draw.rect(screen, NEON_CYAN,
                     (side_x - 20, side_y - 20, 280, 220),
                     width=2, border_radius=14)
    for i, line in enumerate(inst_lines):
        f = fonts["medium"] if i == 0 else fonts["small"]
        col = NEON_CYAN if i == 0 else WHITE
        surf = f.render(line, True, col)
        screen.blit(surf, (side_x, side_y + i * 38))

    # Right-side BO indicator
    with state.lock:
        bo = state.bo_target
    bo_txt = f"BEST OF {5 if bo == 3 else 7}"
    rect = pygame.Rect(WIDTH - 280, 220, 220, 80)
    pygame.draw.rect(screen, DARK_PANEL, rect, border_radius=14)
    pygame.draw.rect(screen, NEON_YELLOW, rect, width=2, border_radius=14)
    txt = fonts["medium"].render(bo_txt, True, NEON_YELLOW)
    screen.blit(txt, txt.get_rect(center=rect.center))


def draw_score_bar(screen, fonts):
    with state.lock:
        p1 = state.p1_score
        p2 = state.p2_score
        rd = state.current_round
        cp = state.current_player
        bo = state.bo_target

    bar = pygame.Rect(0, 0, WIDTH, 90)
    pygame.draw.rect(screen, DARKER_PANEL, bar)
    pygame.draw.line(screen, NEON_PURPLE, (0, 90), (WIDTH, 90), 2)

    # P1 panel (left)
    p1_active = (cp == 1)
    p1_box = pygame.Rect(20, 12, 320, 66)
    if p1_active:
        pygame.draw.rect(screen, P1_COLOR, p1_box.inflate(10, 10), 3,
                         border_radius=12)
    pygame.draw.rect(screen, DARK_PANEL, p1_box, border_radius=10)
    p1_label = fonts["small"].render("PLAYER 1 (LAPTOP)", True, P1_COLOR)
    screen.blit(p1_label, (p1_box.x + 16, p1_box.y + 8))
    score_txt = fonts["score"].render(str(p1), True, WHITE)
    screen.blit(score_txt, score_txt.get_rect(midright=(p1_box.right - 16,
                                                        p1_box.centery + 4)))

    # P2 panel (right)
    p2_active = (cp == 2)
    p2_box = pygame.Rect(WIDTH - 340, 12, 320, 66)
    if p2_active:
        pygame.draw.rect(screen, P2_COLOR, p2_box.inflate(10, 10), 3,
                         border_radius=12)
    pygame.draw.rect(screen, DARK_PANEL, p2_box, border_radius=10)
    p2_label = fonts["small"].render("PLAYER 2 (PHONE)", True, P2_COLOR)
    screen.blit(p2_label, (p2_box.x + 16, p2_box.y + 8))
    score_txt2 = fonts["score"].render(str(p2), True, WHITE)
    screen.blit(score_txt2, score_txt2.get_rect(midright=(p2_box.right - 16,
                                                          p2_box.centery + 4)))

    # Center: round + format
    fmt = f"BEST OF {5 if bo == 3 else 7}  -  ROUND {rd}"
    center = fonts["small"].render(fmt, True, NEON_YELLOW)
    screen.blit(center, center.get_rect(center=(WIDTH // 2, 30)))
    target = fonts["small"].render(
        f"First to {bo} wins", True, GRAY)
    screen.blit(target, target.get_rect(center=(WIDTH // 2, 60)))


def draw_countdown(screen, fonts, t):
    draw_grid_bg(screen, t)
    draw_score_bar(screen, fonts)

    with state.lock:
        elapsed = time.time() - state.phase_start
        cp = state.current_player
    remaining = max(0, COUNTDOWN_DURATION - elapsed)
    n = int(remaining) + 1 if remaining > 0 else "GO!"

    # Active turn banner
    color = P1_COLOR if cp == 1 else P2_COLOR
    who = "PLAYER 1" if cp == 1 else "PLAYER 2"
    banner = fonts["big"].render(f"{who} STARTS!", True, color)
    screen.blit(banner, banner.get_rect(center=(WIDTH // 2, 220)))

    # Countdown number
    big = fonts["mega"].render(str(n), True, NEON_YELLOW)
    rect = big.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
    # pulse circle
    radius = 130 + int(20 * abs((remaining % 1) - 0.5))
    pygame.draw.circle(screen, NEON_PURPLE, rect.center, radius, 3)
    screen.blit(big, rect)

    sub = fonts["medium"].render("Get ready!", True, WHITE)
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT - 90)))


def draw_question(screen, fonts, answer_buttons, t):
    draw_grid_bg(screen, t)
    draw_score_bar(screen, fonts)

    with state.lock:
        q = state.question
        cp = state.current_player
        elapsed = time.time() - state.phase_start
    if q is None:
        return

    is_p1_turn = (cp == 1)
    color = P1_COLOR if is_p1_turn else P2_COLOR

    # Turn banner
    who = "PLAYER 1's TURN" if is_p1_turn else "PLAYER 2's TURN"
    sub_msg = "Click an answer below" if is_p1_turn else "Player 2 is answering on phone..."
    draw_neon_text(screen, fonts["big"], who,
                   (WIDTH // 2, 130), color, color)

    sub = fonts["small"].render(sub_msg, True, GRAY)
    screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 175)))

    # Category tag
    tag_text = q["type"]
    tag = fonts["small"].render(tag_text, True, NEON_YELLOW)
    tag_rect = tag.get_rect(center=(WIDTH // 2, 210))
    pad = pygame.Rect(0, 0, tag_rect.width + 24, tag_rect.height + 10)
    pad.center = tag_rect.center
    pygame.draw.rect(screen, DARK_PANEL, pad, border_radius=10)
    pygame.draw.rect(screen, NEON_YELLOW, pad, width=2, border_radius=10)
    screen.blit(tag, tag_rect)

    # Question card
    q_rect = pygame.Rect(WIDTH // 2 - 480, 240, 960, 160)
    pygame.draw.rect(screen, DARKER_PANEL, q_rect, border_radius=18)
    pygame.draw.rect(screen, NEON_PURPLE, q_rect, width=3, border_radius=18)

    lines = wrap_lines(q["q"], fonts["medium"], q_rect.width - 40)
    line_h = fonts["medium"].get_linesize()
    total_h = line_h * len(lines)
    y = q_rect.centery - total_h // 2
    for line in lines:
        surf = fonts["medium"].render(line, True, WHITE)
        screen.blit(surf, surf.get_rect(centerx=q_rect.centerx, top=y))
        y += line_h

    # Answer buttons (only enabled for P1)
    for i, b in enumerate(answer_buttons):
        b.text = f"{chr(ord('A') + i)}.  {q['options'][i]}"
        b.disabled = not is_p1_turn
        b.draw(screen, fonts)

    # Timer bar at bottom
    pct = max(0.0, 1.0 - (elapsed / ROUND_DURATION))
    bar_x = 80
    bar_y = HEIGHT - 40
    bar_w = WIDTH - 160
    bar_h = 18
    pygame.draw.rect(screen, DARKER_PANEL,
                     (bar_x, bar_y, bar_w, bar_h),
                     border_radius=9)
    fill_w = int(bar_w * pct)
    bar_color = NEON_GREEN if pct > 0.5 else (NEON_YELLOW if pct > 0.25 else NEON_RED)
    pygame.draw.rect(screen, bar_color,
                     (bar_x, bar_y, fill_w, bar_h),
                     border_radius=9)
    secs_left = max(0, int(ROUND_DURATION - elapsed))
    timer_txt = fonts["small"].render(f"{secs_left}s", True, WHITE)
    screen.blit(timer_txt, timer_txt.get_rect(midleft=(bar_x + bar_w + 10,
                                                       bar_y + bar_h // 2)))


def draw_round_result(screen, fonts, t):
    draw_grid_bg(screen, t)
    draw_score_bar(screen, fonts)

    with state.lock:
        res = state.last_result
        elapsed = time.time() - state.phase_start
        winner = state.winner
    if res is None:
        return

    if res["correct"]:
        big = "CORRECT!"
        color = NEON_GREEN
    elif res["timeout"]:
        big = "TIME'S UP!"
        color = NEON_RED
    else:
        big = "WRONG!"
        color = NEON_RED

    draw_neon_text(screen, fonts["mega"], big,
                   (WIDTH // 2, 230), color, color)

    who = f"Player {res['player']}"
    detail = (f"{who} answered correctly. +1 point"
              if res["correct"]
              else f"{who} missed. Point goes to opponent.")
    surf = fonts["medium"].render(detail, True, WHITE)
    screen.blit(surf, surf.get_rect(center=(WIDTH // 2, 320)))

    # Show correct answer
    correct_letter = chr(ord('A') + res["answer"])
    correct_text = res["options"][res["answer"]]
    ans_surf = fonts["medium"].render(
        f"Answer: {correct_letter}.  {correct_text}", True, NEON_YELLOW)
    screen.blit(ans_surf, ans_surf.get_rect(center=(WIDTH // 2, 380)))

    # Next round / final indicator
    if winner is not None:
        next_msg = "Calculating final result..."
    else:
        wait = max(0, RESULT_DURATION - elapsed)
        next_msg = f"Next round in {wait:.1f}s"
    n_surf = fonts["small"].render(next_msg, True, GRAY)
    screen.blit(n_surf, n_surf.get_rect(center=(WIDTH // 2, HEIGHT - 80)))


def draw_game_over(screen, fonts, buttons, t):
    draw_grid_bg(screen, t)

    with state.lock:
        winner = state.winner
        p1 = state.p1_score
        p2 = state.p2_score

    win_color = P1_COLOR if winner == 1 else P2_COLOR
    win_label = "PLAYER 1 WINS!" if winner == 1 else "PLAYER 2 WINS!"
    draw_neon_text(screen, fonts["mega"], win_label,
                   (WIDTH // 2, 130), win_color, win_color)

    # Final score
    score_msg = f"Final Score   {p1}  :  {p2}"
    s_surf = fonts["big"].render(score_msg, True, WHITE)
    screen.blit(s_surf, s_surf.get_rect(center=(WIDTH // 2, 220)))

    # Big CSITE callout panel
    panel = pygame.Rect(WIDTH // 2 - 480, 290, 960, 240)
    pygame.draw.rect(screen, DARKER_PANEL, panel, border_radius=20)
    pygame.draw.rect(screen, NEON_YELLOW, panel, width=4, border_radius=20)

    headline = fonts["big"].render("LOVED THE CHALLENGE?", True, NEON_YELLOW)
    screen.blit(headline, headline.get_rect(center=(WIDTH // 2, panel.y + 50)))

    cta_lines = [
        ("LEARN HOW TO CODE", NEON_CYAN),
        ("MASTER LOGIC -- JOIN CSITE", NEON_GREEN),
        ("ENROLL IN CSITE NOW!", NEON_PINK),
    ]
    for i, (line, c) in enumerate(cta_lines):
        s = fonts["medium"].render(line, True, c)
        screen.blit(s, s.get_rect(center=(WIDTH // 2,
                                          panel.y + 110 + i * 42)))

    # Buttons
    for b in buttons:
        b.draw(screen, fonts)


# =================================================================
# MAIN
# =================================================================

def main():
    pygame.init()
    pygame.display.set_caption("CSITE Logic Duel - Host")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Fonts
    def f(size, bold=False):
        return pygame.font.SysFont("arial,helvetica,sans-serif", size, bold=bold)
    fonts = {
        "title":  f(96, True),
        "mega":   f(110, True),
        "big":    f(56, True),
        "medium": f(32),
        "small":  f(22),
        "score":  f(48, True),
    }

    # Network info / QR
    ensure_socketio_client()
    local_ip = get_local_ip()
    url = f"http://{local_ip}:{PORT}/"
    qr_surface = make_qr_surface(url, size=380)

    # Start the SocketIO server in a background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print(f"\n[CSITE] Web client URL:  {url}")
    print(f"[CSITE] Place client.html in the same folder as host_game.py")
    print(f"[CSITE] Waiting for Player 2 to connect...\n")

    # ---------- Build buttons for each scene ----------
    # Menu buttons
    bo5_btn = Button((WIDTH // 2 - 240, 400, 220, 70), "BEST OF 5",
                     DARK_PANEL, NEON_CYAN,
                     action=lambda: state.set_bo(3),
                     font_key="medium")
    bo7_btn = Button((WIDTH // 2 + 20,  400, 220, 70), "BEST OF 7",
                     DARK_PANEL, NEON_CYAN,
                     action=lambda: state.set_bo(4),
                     font_key="medium")
    start_btn = Button((WIDTH // 2 - 240, 510, 480, 90), "START 1v1 DUEL",
                       (35, 45, 100), NEON_PINK,
                       action=state.begin_waiting,
                       font_key="big")
    menu_buttons = [bo5_btn, bo7_btn, start_btn]

    # Waiting buttons
    waiting_back = Button((40, HEIGHT - 80, 160, 50),
                          "< BACK",
                          DARK_PANEL, NEON_CYAN,
                          action=state.go_to_menu,
                          font_key="small")
    waiting_start = Button((WIDTH - 280, HEIGHT - 100, 240, 70),
                           "START DUEL",
                           (35, 80, 45), NEON_GREEN,
                           action=state.start_match,
                           font_key="medium")
    waiting_buttons = [waiting_back, waiting_start]

    # Question answer buttons (4 large clickable tiles)
    ans_w, ans_h = 440, 95
    gap_x = 40
    gap_y = 25
    base_x = WIDTH // 2 - ans_w - gap_x // 2
    base_y = 440
    answer_buttons = []
    for i in range(4):
        col = i % 2
        row = i // 2
        rect = (base_x + col * (ans_w + gap_x),
                base_y + row * (ans_h + gap_y),
                ans_w, ans_h)
        # The action submits Player 1's answer with this index.
        answer_buttons.append(Button(
            rect,
            "",
            DARK_PANEL,
            NEON_CYAN,
            action=(lambda idx=i: state.submit_p1_answer(idx)),
            font_key="medium",
        ))

    # Game over buttons
    play_again = Button((WIDTH // 2 - 270, HEIGHT - 110, 240, 75),
                        "PLAY AGAIN",
                        (35, 80, 45), NEON_GREEN,
                        action=state.start_match,
                        font_key="medium")
    main_menu = Button((WIDTH // 2 + 30, HEIGHT - 110, 240, 75),
                       "MAIN MENU",
                       DARK_PANEL, NEON_CYAN,
                       action=state.go_to_menu,
                       font_key="medium")
    over_buttons = [play_again, main_menu]

    # ---------- Main loop ----------
    running = True
    while running:
        clock.tick(FPS)
        t = pygame.time.get_ticks() / 1000.0

        # Tick state machine (advances timers / phases)
        state.tick()

        # Read current phase under lock
        with state.lock:
            phase = state.phase
            connected = state.p2_connected

        # Adjust waiting_start enabled state based on connection
        waiting_start.disabled = not connected

        # Events
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if phase == "MENU":
                        running = False
                    else:
                        state.go_to_menu()
                # Keyboard shortcuts for P1 during a question (1-4 / A-D)
                elif phase == "QUESTION":
                    with state.lock:
                        is_p1 = (state.current_player == 1)
                    if is_p1:
                        key_map = {
                            pygame.K_1: 0, pygame.K_KP1: 0, pygame.K_a: 0,
                            pygame.K_2: 1, pygame.K_KP2: 1, pygame.K_b: 1,
                            pygame.K_3: 2, pygame.K_KP3: 2, pygame.K_c: 2,
                            pygame.K_4: 3, pygame.K_KP4: 3, pygame.K_d: 3,
                        }
                        if ev.key in key_map:
                            state.submit_p1_answer(key_map[ev.key])
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = ev.pos
                if phase == "MENU":
                    for b in menu_buttons:
                        b.click(pos)
                elif phase == "WAITING":
                    for b in waiting_buttons:
                        b.click(pos)
                elif phase == "QUESTION":
                    with state.lock:
                        is_p1 = (state.current_player == 1)
                    if is_p1:
                        for b in answer_buttons:
                            b.click(pos)
                elif phase == "GAME_OVER":
                    for b in over_buttons:
                        b.click(pos)

        # Draw current scene
        if phase == "MENU":
            draw_menu(screen, fonts, menu_buttons, t)
        elif phase == "WAITING":
            draw_waiting(screen, fonts, qr_surface, url, t)
            for b in waiting_buttons:
                b.draw(screen, fonts)
        elif phase == "COUNTDOWN":
            draw_countdown(screen, fonts, t)
        elif phase == "QUESTION":
            draw_question(screen, fonts, answer_buttons, t)
        elif phase == "ROUND_RESULT":
            draw_round_result(screen, fonts, t)
        elif phase == "GAME_OVER":
            draw_game_over(screen, fonts, over_buttons, t)

        pygame.display.flip()

    pygame.quit()
    # Server thread is daemon, will die with the process
    sys.exit(0)


if __name__ == "__main__":
    main()