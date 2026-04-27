#!/usr/bin/env python3
"""
=============================================================================
  ROAD FIGHTER RETRO — A Classic Vertical Scrolling Racer (Pygame)
=============================================================================

  Faithful simplified remake of Konami's "Road Fighter" (1984)

  HOW TO RUN:
    1. Install Python 3.8+ and Pygame:
         pip install pygame
    2. Run:
         python road_fighter.py

  CONTROLS:
    LEFT / RIGHT  — Steer
    UP            — Accelerate
    DOWN          — Brake
    SPACE         — Turbo boost (burns fuel faster!)
    M             — Toggle Audio Aid (mute/unmute)
        0             — Return to start page
    ENTER         — Start game / Restart
    ESC           — Quit

  GAMEPLAY:
    • Dodge traffic, stay on the road, manage your fuel.
    • Hit YELLOW cars to refuel.
    • Avoid OIL SLICKS (dark puddles) — they make you spin out.
    • Crashing into traffic or walls ends the game.
    • Reach each checkpoint (every 5 km) before fuel runs out.
    • Speed and clean overtakes earn bonus points.

  HOW TO ADD YOUR OWN ASSETS:
    • SPRITES: Replace the draw() methods with pygame.image.load():
        player_sprite = pygame.image.load("player_car.png").convert_alpha()
      Recommended sizes: cars 30×52 px, scenery 20-40 px wide.
    • SOUNDS: Search for "# SFX:" comments and load .wav / .ogg files:
        engine_sound = pygame.mixer.Sound("engine.wav")
        crash_sound  = pygame.mixer.Sound("crash.wav")
    • MUSIC: pygame.mixer.music.load("road_fighter_theme.ogg")

  PROJECT STRUCTURE:
    PlayerCar    — player physics, steering, fuel, drawing
    TrafficCar   — AI traffic vehicles (obstacles + fuel pickups)
    OilSlick     — hazard that causes spin-outs
    Road         — scrolling road surface, lane markings, shoulders
    Scenery      — parallax background objects (trees, signs, mountains)
    HUD          — speedometer, fuel gauge, score, distance
    Game         — main loop, state machine, spawning, collision

=============================================================================
"""

import pygame
import sys
import math
import random
import os
import subprocess
import json
from array import array

# ---------------------------------------------------------------------------
#  CONSTANTS
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 800, 600
FPS = 60

# --- Colour Palette (1984 Konami / NES style) ---
BLACK       = (5,   5,   10)
DARK_GRAY   = (30,  30,  38)
MID_GRAY    = (80,  80,  95)
LIGHT_GRAY  = (170, 170, 180)
WHITE       = (240, 240, 245)

# Player car — classic red
P_RED       = (220, 35,  30)
P_RED_DARK  = (160, 20,  15)
P_RED_LIGHT = (255, 80,  60)

# Traffic palette
T_BLUE      = (40,  80,  220)
T_GREEN     = (30,  180, 60)
T_PURPLE    = (150, 40,  200)
T_CYAN      = (30,  200, 210)
T_ORANGE    = (240, 140, 20)
T_WHITE     = (210, 210, 220)

# Special
FUEL_YELLOW = (255, 220, 40)
OIL_BROWN   = (50,  35,  25)
OIL_SHEEN   = (70,  55,  45)

# Road
ASPHALT     = (55,  55,  62)
ASPHALT_ALT = (50,  50,  57)       # alternating strip for pseudo-3D
ROAD_EDGE   = (200, 200, 190)
SHOULDER    = (90,  130, 70)        # grass / gravel
DASH_WHITE  = (220, 220, 210)
RUMBLE_RED  = (200, 40,  30)
RUMBLE_WHITE = (220, 220, 210)

# Scenery
TREE_GREEN   = (25,  120, 40)
TREE_TRUNK   = (100, 65,  30)
MOUNTAIN     = (60,  70,  90)
SKY_TOP      = (10,  10,  35)
SKY_BOTTOM   = (30,  30,  70)
SIGN_BLUE    = (30,  60,  180)

# HUD
HUD_BG       = (15,  15,  22)
FUEL_GREEN   = (40,  220, 70)
FUEL_RED     = (220, 40,  40)
SPEED_CYAN   = (0,   210, 240)
SCORE_YELLOW = (255, 230, 50)

# Compatibility aliases used by HUD/effects code
GREEN        = FUEL_GREEN
ORANGE       = T_ORANGE

# --- Road geometry ---
ROAD_LEFT     = 200            # left edge of road on screen
ROAD_RIGHT    = 600            # right edge of road on screen
ROAD_WIDTH    = ROAD_RIGHT - ROAD_LEFT
ROAD_CENTER   = (ROAD_LEFT + ROAD_RIGHT) // 2
NUM_LANES     = 4
LANE_WIDTH    = ROAD_WIDTH // NUM_LANES

# --- Car dimensions ---
CAR_W, CAR_H  = 30, 52
PLAYER_START_X = ROAD_CENTER
PLAYER_START_Y = SCREEN_H - 100

# --- Physics ---
MAX_SPEED      = 400.0          # km/h display
MIN_SPEED      = 0.0
ACCEL_RATE     = 120.0          # km/h per second when pressing up
BRAKE_RATE     = 200.0          # km/h per second when pressing down
DRAG_RATE      = 30.0           # natural deceleration
BOOST_SPEED    = 380.0          # minimum speed during boost
STEER_SPEED    = 280.0          # pixels per second lateral movement
STEER_TILT     = 12.0           # degrees of visual tilt when steering

# --- Fuel ---
FUEL_MAX       = 100.0
FUEL_DRAIN     = 2.5            # per second at normal speed
FUEL_DRAIN_BOOST = 7.0          # per second when boosting
FUEL_PICKUP    = 25.0           # fuel gained from yellow car

# --- Spawning ---
TRAFFIC_MIN_GAP   = 120         # min vertical px between spawns
TRAFFIC_BASE_RATE = 1.2         # spawns per second at start
TRAFFIC_MAX_RATE  = 4.0         # spawns per second at max difficulty
OIL_BASE_RATE     = 0.15        # oil slick spawns per second
OIL_MAX_RATE      = 0.5
FUEL_CAR_CHANCE   = 0.12        # 12% chance a traffic car is a fuel pickup

# --- Checkpoints ---
CHECKPOINT_DIST   = 5000.0      # metres between checkpoints
STAGES            = 5           # total stages to beat the game

# --- Score ---
OVERTAKE_BONUS    = 50          # points for passing a car cleanly
SPEED_BONUS_RATE  = 0.5         # points per second proportional to speed

# Save file
HIGHSCORE_FILE = "leaderboardPR.json"
MAX_LEADERBOARD = 10


# ---------------------------------------------------------------------------
#  HELPERS
# ---------------------------------------------------------------------------

def load_leaderboard() -> list:
    """Load leaderboard entries sorted by highest score first."""
    if not os.path.exists(HIGHSCORE_FILE):
        return []

    try:
        with open(HIGHSCORE_FILE, "r") as f:
            raw = f.read().strip()
        if not raw:
            return []

        data = json.loads(raw)
        rows = []

        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict) and "score" in row:
                    name = str(row.get("name", "PLAYER"))[:12]
                    rows.append({"name": name, "score": int(row["score"])})
        elif isinstance(data, dict):
            # Backward compatibility with {"highscore": N} format.
            if "highscore" in data:
                rows.append({"name": "PLAYER", "score": int(data["highscore"])})
        else:
            # Backward compatibility with plain numeric files.
            rows.append({"name": "PLAYER", "score": int(data)})

        rows.sort(key=lambda e: e.get("score", 0), reverse=True)
        return rows[:MAX_LEADERBOARD]
    except (ValueError, TypeError, IOError, json.JSONDecodeError):
        # Legacy plain-text fallback.
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                value = int(f.read().strip())
            return [{"name": "PLAYER", "score": value}]
        except (ValueError, IOError):
            return []


def save_leaderboard(board: list):
    clean = []
    for row in board:
        if isinstance(row, dict) and "score" in row:
            clean.append({
                "name": str(row.get("name", "PLAYER"))[:12],
                "score": int(row["score"]),
            })
    clean.sort(key=lambda e: e["score"], reverse=True)
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump(clean[:MAX_LEADERBOARD], f, indent=2)
    except IOError:
        pass


def add_to_leaderboard(name: str, score: int) -> list:
    board = load_leaderboard()
    board.append({"name": (name or "PLAYER")[:12], "score": int(score)})
    board.sort(key=lambda e: e["score"], reverse=True)
    board = board[:MAX_LEADERBOARD]
    save_leaderboard(board)
    return board


def load_highscore() -> int:
    board = load_leaderboard()
    return int(board[0]["score"]) if board else 0


def save_highscore(score: int):
    board = load_leaderboard()
    if board and board[0]["score"] >= int(score):
        return
    # Keep compatibility for existing high-score update call sites.
    add_to_leaderboard("PLAYER", int(score))


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lane_center_x(lane: int) -> float:
    """Return the screen-x centre of a lane (0-based from left)."""
    return ROAD_LEFT + LANE_WIDTH // 2 + lane * LANE_WIDTH


def return_to_start_page() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    launcher = os.path.join(base_dir, "start_page.py")
    if os.path.exists(launcher):
        subprocess.Popen([sys.executable, launcher], cwd=base_dir)
    pygame.quit()
    sys.exit()


class AudioAid:
    """Generates simple built-in tone cues without external sound files."""

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.low_fuel_timer = 0.0
        self.sounds: dict[str, pygame.mixer.Sound] = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.enabled = True
            self._build_sounds()
        except pygame.error:
            # Audio is optional; game remains playable without sound support.
            self.enabled = False

    def _build_sounds(self):
        self.sounds = {
            "menu_move": self._tone(520, 0.05, 0.18),
            "menu_select": self._tone(740, 0.08, 0.22),
            "fuel_pickup": self._tone(980, 0.09, 0.25),
            "boost_on": self._tone(620, 0.08, 0.20),
            "low_fuel": self._tone(880, 0.05, 0.22, wave="square"),
            "checkpoint": self._tone(720, 0.16, 0.25),
            "crash": self._tone(160, 0.22, 0.30, wave="square"),
            "game_over": self._tone(200, 0.18, 0.24),
            "win": self._tone(1040, 0.18, 0.24),
        }

    @staticmethod
    def _tone(freq: float, duration: float, volume: float,
              wave: str = "sine") -> pygame.mixer.Sound:
        sample_rate = 44100
        total = max(1, int(sample_rate * duration))
        attack = max(1, int(sample_rate * 0.005))
        release = max(1, int(sample_rate * 0.02))
        buf = array("h")

        for i in range(total):
            t = i / sample_rate
            if wave == "square":
                base = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            else:
                base = math.sin(2 * math.pi * freq * t)

            if i < attack:
                env = i / attack
            elif i > total - release:
                env = max(0.0, (total - i) / release)
            else:
                env = 1.0

            sample = int(32767 * volume * base * env)
            buf.append(sample)

        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name: str):
        if not self.enabled or self.muted:
            return
        sfx = self.sounds.get(name)
        if sfx is not None:
            sfx.play()

    def update_low_fuel(self, dt: float, fuel_ratio: float, playing: bool):
        if not self.enabled or self.muted:
            self.low_fuel_timer = 0.0
            return

        if playing and fuel_ratio < 0.2:
            self.low_fuel_timer += dt
            interval = 0.35 if fuel_ratio < 0.1 else 0.6
            if self.low_fuel_timer >= interval:
                self.low_fuel_timer = 0.0
                self.play("low_fuel")
        else:
            self.low_fuel_timer = 0.0

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted


# ---------------------------------------------------------------------------
#  PLAYER CAR
# ---------------------------------------------------------------------------

class PlayerCar:
    """
    The player-controlled red sports car.

    Physics model:
      - speed_kmh:  display speed (0-400 km/h), controls scroll rate
      - x, y:       screen position (y is mostly fixed near bottom)
      - fuel:       0-100, drains over time, refilled by fuel pickups
      - spin_timer: >0 when spinning out (from oil slick)
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.x = float(PLAYER_START_X)
        self.y = float(PLAYER_START_Y)
        self.speed_kmh = 0.0
        self.fuel = FUEL_MAX
        self.alive = True
        self.tilt = 0.0              # visual steering angle in degrees
        self.spin_timer = 0.0        # seconds remaining in spin-out
        self.spin_angle = 0.0        # visual spin rotation
        self.boosting = False
        self.distance_m = 0.0        # total distance in metres
        self.invuln_timer = 0.0      # brief invulnerability after respawn flash

        # Visual effects
        self.exhaust_particles: list[dict] = []

    @property
    def scroll_speed(self) -> float:
        """Pixels per second the road scrolls (derived from speed_kmh)."""
        # Scale so max speed gives ~600 px/s of scroll
        return (self.speed_kmh / MAX_SPEED) * 600.0

    def get_rect(self) -> pygame.Rect:
        """Collision rectangle (slightly narrower for fairness)."""
        return pygame.Rect(int(self.x) - CAR_W // 2 + 4,
                           int(self.y) - CAR_H // 2 + 6,
                           CAR_W - 8, CAR_H - 12)

    def update(self, dt: float, keys):
        """Process input and update physics."""
        if not self.alive:
            return

        # --- Spin-out state ---
        if self.spin_timer > 0:
            self.spin_timer -= dt
            self.spin_angle += 720 * dt  # fast spin animation
            self.speed_kmh = max(60, self.speed_kmh - 150 * dt)
            # Can't steer during spin
            if self.spin_timer <= 0:
                self.spin_timer = 0
                self.spin_angle = 0
                self.invuln_timer = 1.0  # brief invulnerability after spin
            self.distance_m += (self.speed_kmh / 3.6) * dt
            self._update_fuel(dt)
            return

        # Invulnerability countdown
        if self.invuln_timer > 0:
            self.invuln_timer -= dt

        # --- Acceleration / braking ---
        self.boosting = keys[pygame.K_SPACE] and self.fuel > 5
        if keys[pygame.K_UP] or self.boosting:
            target = BOOST_SPEED if self.boosting else MAX_SPEED
            accel = ACCEL_RATE * 1.5 if self.boosting else ACCEL_RATE
            self.speed_kmh = min(target, self.speed_kmh + accel * dt)
        elif keys[pygame.K_DOWN]:
            self.speed_kmh = max(MIN_SPEED, self.speed_kmh - BRAKE_RATE * dt)
        else:
            # Natural drag
            self.speed_kmh = max(MIN_SPEED, self.speed_kmh - DRAG_RATE * dt)

        # --- Steering ---
        steer_input = 0
        if keys[pygame.K_LEFT]:
            steer_input = -1
        if keys[pygame.K_RIGHT]:
            steer_input = 1

        if steer_input != 0:
            move = STEER_SPEED * dt * steer_input
            # Slightly faster steering at higher speeds (feels more responsive)
            speed_factor = 0.7 + 0.3 * (self.speed_kmh / MAX_SPEED)
            self.x += move * speed_factor
            self.tilt = STEER_TILT * steer_input
        else:
            # Return tilt to neutral
            self.tilt *= 0.8

        # Clamp to road edges (with crash detection done separately)
        # Allow slightly past the edge — collision system handles crash
        self.x = clamp(self.x, ROAD_LEFT - 10, ROAD_RIGHT + 10)

        # --- Distance ---
        self.distance_m += (self.speed_kmh / 3.6) * dt

        # --- Fuel ---
        self._update_fuel(dt)

        # --- Exhaust particles ---
        self._update_exhaust(dt)

    def _update_fuel(self, dt: float):
        """Drain fuel based on speed and boost status."""
        if self.speed_kmh > 10:
            rate = FUEL_DRAIN_BOOST if self.boosting else FUEL_DRAIN
            # Fuel drain scales slightly with speed
            speed_mult = 0.5 + 0.5 * (self.speed_kmh / MAX_SPEED)
            self.fuel -= rate * speed_mult * dt
            self.fuel = max(0, self.fuel)

    def _update_exhaust(self, dt: float):
        """Spawn and age exhaust / boost flame particles."""
        if self.speed_kmh > 50:
            chance = 0.3 if not self.boosting else 0.8
            if random.random() < chance:
                self.exhaust_particles.append({
                    "x": self.x + random.uniform(-6, 6),
                    "y": self.y + CAR_H // 2 + random.uniform(0, 4),
                    "vy": random.uniform(40, 100),
                    "life": random.uniform(0.1, 0.3),
                    "size": random.randint(2, 5),
                    "color": random.choice(
                        [(255, 100, 30), (255, 200, 50)] if self.boosting
                        else [(120, 120, 130), (90, 90, 100)])
                })

        for p in self.exhaust_particles:
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self.exhaust_particles = [p for p in self.exhaust_particles if p["life"] > 0]

    def add_fuel(self, amount: float):
        """Called when the player hits a fuel car."""
        self.fuel = min(FUEL_MAX, self.fuel + amount)
        # SFX: play fuel pickup sound

    def start_spin(self):
        """Called when the player hits an oil slick."""
        if self.spin_timer <= 0 and self.invuln_timer <= 0:
            self.spin_timer = 1.0   # 1 second spin-out
            self.spin_angle = 0
            # SFX: play skid / spin sound

    def crash(self):
        """Called on collision with traffic or wall."""
        if self.invuln_timer > 0:
            return False  # still invulnerable
        self.alive = False
        # SFX: play crash sound
        return True

    def draw(self, surface: pygame.Surface):
        """
        Draw the player car as a chunky pixel-art rectangle.
        To replace with a sprite:
            sprite = pygame.image.load("player_car.png").convert_alpha()
            rotated = pygame.transform.rotate(sprite, -self.tilt)
            rect = rotated.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(rotated, rect)
        """
        if not self.alive:
            return

        # Blinking during invulnerability
        if self.invuln_timer > 0 and int(self.invuln_timer * 10) % 2 == 0:
            return

        # Build car surface
        car_surf = pygame.Surface((CAR_W, CAR_H), pygame.SRCALPHA)

        # --- Body ---
        # Main body
        pygame.draw.rect(car_surf, P_RED, (4, 6, CAR_W - 8, CAR_H - 12))
        # Hood (front, narrower)
        pygame.draw.rect(car_surf, P_RED_LIGHT, (6, 2, CAR_W - 12, 12))
        # Roof / cabin
        pygame.draw.rect(car_surf, P_RED_DARK, (7, 18, CAR_W - 14, 16))
        # Windshield
        pygame.draw.rect(car_surf, (50, 60, 90), (9, 16, CAR_W - 18, 8))
        # Rear windshield
        pygame.draw.rect(car_surf, (40, 50, 70), (9, 34, CAR_W - 18, 5))

        # Headlights
        pygame.draw.rect(car_surf, FUEL_YELLOW, (6, 1, 5, 4))
        pygame.draw.rect(car_surf, FUEL_YELLOW, (CAR_W - 11, 1, 5, 4))

        # Tail lights
        pygame.draw.rect(car_surf, (255, 30, 30), (5, CAR_H - 7, 6, 4))
        pygame.draw.rect(car_surf, (255, 30, 30), (CAR_W - 11, CAR_H - 7, 6, 4))

        # Boost flame effect (below car)
        if self.boosting:
            flame_h = random.randint(8, 18)
            flame_c = random.choice([(255, 150, 30), (255, 220, 50), (255, 80, 20)])
            pygame.draw.rect(car_surf, flame_c,
                             (CAR_W // 2 - 4, CAR_H - 2, 8, flame_h))

        # Rotate for tilt or spin
        angle = -self.tilt if self.spin_timer <= 0 else -self.spin_angle
        if abs(angle) > 0.5:
            rotated = pygame.transform.rotate(car_surf, angle)
        else:
            rotated = car_surf
        rect = rotated.get_rect(center=(int(self.x), int(self.y)))

        # Exhaust particles (drawn behind car)
        for p in self.exhaust_particles:
            sz = max(1, int(p["size"] * (p["life"] / 0.3)))
            c = tuple(min(255, int(ch * (p["life"] / 0.3))) for ch in p["color"])
            pygame.draw.rect(surface, c,
                             (int(p["x"]) - sz // 2, int(p["y"]), sz, sz))

        surface.blit(rotated, rect)


# ---------------------------------------------------------------------------
#  TRAFFIC CAR
# ---------------------------------------------------------------------------

class TrafficCar:
    """
    An NPC vehicle on the road. Can be:
      - Regular traffic (obstacle) — various colors
      - Fuel car (yellow) — gives fuel on "collision" (pickup)
    """

    COLORS = [T_BLUE, T_GREEN, T_PURPLE, T_CYAN, T_ORANGE, T_WHITE]

    def __init__(self, x: float, y: float, speed_kmh: float,
                 is_fuel: bool = False):
        self.x = x
        self.y = y
        self.speed_kmh = speed_kmh  # the traffic car's own speed
        self.is_fuel = is_fuel
        self.color = FUEL_YELLOW if is_fuel else random.choice(self.COLORS)
        self.active = True
        self.scored = False          # has the player been credited for passing this car?
        self.wobble = random.uniform(-0.3, 0.3)  # slight lane weaving

        # Slight size variation for visual variety
        self.w = CAR_W - 2 + random.randint(-2, 4)
        self.h = CAR_H - 4 + random.randint(-4, 4)

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - self.w // 2 + 3,
                           int(self.y) - self.h // 2 + 4,
                           self.w - 6, self.h - 8)

    def update(self, dt: float, player_scroll: float):
        """
        Move the traffic car. It scrolls down the screen relative to the
        player's speed, plus its own forward speed.
        """
        # Traffic moves down because player moves up; traffic's own speed
        # makes it scroll slightly slower (it's also moving forward).
        relative_speed = player_scroll - (self.speed_kmh / MAX_SPEED) * 600.0
        self.y += relative_speed * dt

        # Gentle lane weaving
        self.x += math.sin(self.y * 0.008) * self.wobble

        # Deactivate when off-screen
        if self.y > SCREEN_H + 100 or self.y < -200:
            self.active = False

    def draw(self, surface: pygame.Surface):
        """
        Draw the traffic car as a simple pixel rectangle.
        Replace with sprite loading for real pixel art.
        """
        if not self.active:
            return

        x = int(self.x) - self.w // 2
        y = int(self.y) - self.h // 2

        # Body
        pygame.draw.rect(surface, self.color, (x + 2, y + 4, self.w - 4, self.h - 8))
        # Darker top (roof)
        darker = tuple(max(0, c - 50) for c in self.color)
        pygame.draw.rect(surface, darker, (x + 4, y + self.h // 3, self.w - 8, self.h // 3))
        # Windshield
        pygame.draw.rect(surface, (40, 50, 70),
                         (x + 5, y + self.h // 3 - 2, self.w - 10, 6))

        # Fuel car special glow effect
        if self.is_fuel:
            # Pulsing outline
            pulse = (math.sin(pygame.time.get_ticks() * 0.008) + 1) / 2
            glow_c = (255, int(200 + 55 * pulse), 0)
            pygame.draw.rect(surface, glow_c,
                             (x, y + 2, self.w, self.h - 4), 2)
            # "F" label
            font = pygame.font.SysFont("consolas", 14, bold=True)
            f_text = font.render("F", True, BLACK)
            surface.blit(f_text, (int(self.x) - 4, int(self.y) - 6))

        # Tail lights
        if not self.is_fuel:
            pygame.draw.rect(surface, (255, 40, 40), (x + 3, y + self.h - 6, 4, 3))
            pygame.draw.rect(surface, (255, 40, 40),
                             (x + self.w - 7, y + self.h - 6, 4, 3))


# ---------------------------------------------------------------------------
#  OIL SLICK
# ---------------------------------------------------------------------------

class OilSlick:
    """A dark puddle on the road that causes spin-outs."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.w = random.randint(36, 56)
        self.h = random.randint(18, 28)
        self.active = True

    def get_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) - self.w // 2,
                           int(self.y) - self.h // 2,
                           self.w, self.h)

    def update(self, dt: float, player_scroll: float):
        self.y += player_scroll * dt
        if self.y > SCREEN_H + 60:
            self.active = False

    def draw(self, surface: pygame.Surface):
        if not self.active:
            return
        # Dark oil puddle with slight sheen
        rect = (int(self.x) - self.w // 2, int(self.y) - self.h // 2,
                self.w, self.h)
        pygame.draw.ellipse(surface, OIL_BROWN, rect)
        # Sheen highlight
        sheen_rect = (rect[0] + 4, rect[1] + 3,
                      self.w // 2, self.h // 2)
        pygame.draw.ellipse(surface, OIL_SHEEN, sheen_rect)


# ---------------------------------------------------------------------------
#  ROAD RENDERER
# ---------------------------------------------------------------------------

class Road:
    """
    Draws the scrolling road surface with lane markings, shoulders,
    and rumble strips. Uses a simple striped pattern that scrolls to
    create the classic top-down racing feel.
    """

    def __init__(self):
        self.scroll_offset = 0.0  # accumulated scroll in pixels

    def update(self, dt: float, scroll_speed: float):
        self.scroll_offset += scroll_speed * dt

    def draw(self, surface: pygame.Surface):
        """Render road, markings, shoulders, and rumble strips."""
        offset = self.scroll_offset

        # --- Grass / shoulder background ---
        surface.fill(SHOULDER)

        # --- Asphalt ---
        pygame.draw.rect(surface, ASPHALT,
                         (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_H))

        # --- Alternating asphalt strips (pseudo-3D depth illusion) ---
        strip_h = 8
        strip_offset = int(offset) % (strip_h * 2)
        for sy in range(strip_offset - (strip_h * 2), SCREEN_H + strip_h, strip_h * 2):
            pygame.draw.rect(surface, ASPHALT_ALT,
                             (ROAD_LEFT, sy, ROAD_WIDTH, strip_h))

        # --- Rumble strips (red/white on road edges) ---
        rumble_w = 8
        rumble_h = 12
        rumble_offset = int(offset) % (rumble_h * 2)
        for ry in range(rumble_offset - (rumble_h * 2), SCREEN_H + rumble_h, rumble_h * 2):
            # Left rumble
            pygame.draw.rect(surface, RUMBLE_RED,
                             (ROAD_LEFT - rumble_w, ry, rumble_w, rumble_h))
            pygame.draw.rect(surface, RUMBLE_WHITE,
                             (ROAD_LEFT - rumble_w, ry + rumble_h,
                              rumble_w, rumble_h))
            # Right rumble
            pygame.draw.rect(surface, RUMBLE_RED,
                             (ROAD_RIGHT, ry, rumble_w, rumble_h))
            pygame.draw.rect(surface, RUMBLE_WHITE,
                             (ROAD_RIGHT, ry + rumble_h, rumble_w, rumble_h))

        # --- Road edge lines ---
        pygame.draw.line(surface, ROAD_EDGE,
                         (ROAD_LEFT, 0), (ROAD_LEFT, SCREEN_H), 3)
        pygame.draw.line(surface, ROAD_EDGE,
                         (ROAD_RIGHT, 0), (ROAD_RIGHT, SCREEN_H), 3)

        # --- Dashed centre line ---
        dash_len = 30
        gap_len = 25
        total = dash_len + gap_len
        dash_offset = int(offset) % total
        for dy in range(dash_offset - total, SCREEN_H + total, total):
            pygame.draw.rect(surface, DASH_WHITE,
                             (ROAD_CENTER - 1, dy, 3, dash_len))

        # --- Lane divider lines (lighter dashes on each side) ---
        for lane_i in [1, 3]:  # between lanes 0-1 and 2-3
            lx = ROAD_LEFT + lane_i * LANE_WIDTH
            small_dash = 16
            small_gap = 30
            small_total = small_dash + small_gap
            sd_offset = int(offset) % small_total
            for dy in range(sd_offset - small_total, SCREEN_H + small_total, small_total):
                pygame.draw.rect(surface, MID_GRAY,
                                 (lx - 1, dy, 2, small_dash))


# ---------------------------------------------------------------------------
#  SCENERY (parallax background objects)
# ---------------------------------------------------------------------------

class Scenery:
    """
    Manages roadside objects (trees, signs, mountains) that scroll at
    a slower rate than the road for parallax depth.
    """

    def __init__(self):
        self.objects: list[dict] = []
        self.spawn_timer = 0.0
        self._init_mountains()

    def _init_mountains(self):
        """Pre-generate distant mountain silhouettes."""
        self.mountain_points = []
        x = 0
        while x < SCREEN_W:
            h = random.randint(30, 80)
            w = random.randint(60, 140)
            self.mountain_points.append((x, h, w))
            x += w - random.randint(10, 30)

    def update(self, dt: float, scroll_speed: float):
        """Spawn and scroll scenery objects."""
        parallax_speed = scroll_speed * 0.35  # slower than road

        for obj in self.objects:
            obj["y"] += parallax_speed * dt

        self.objects = [o for o in self.objects if o["y"] < SCREEN_H + 60]

        # Spawn new objects at the top
        self.spawn_timer += dt
        if self.spawn_timer > 0.3 and scroll_speed > 50:
            self.spawn_timer = 0
            # Left side scenery
            if random.random() < 0.5:
                self.objects.append(self._make_object("left"))
            # Right side scenery
            if random.random() < 0.5:
                self.objects.append(self._make_object("right"))

    def _make_object(self, side: str) -> dict:
        kind = random.choices(
            ["tree", "sign", "bush", "pole"],
            weights=[40, 15, 30, 15]
        )[0]

        if side == "left":
            x = random.randint(20, ROAD_LEFT - 40)
        else:
            x = random.randint(ROAD_RIGHT + 15, SCREEN_W - 30)

        return {
            "kind": kind,
            "x": x,
            "y": -40,
            "side": side,
            "size": random.uniform(0.7, 1.3),
        }

    def draw(self, surface: pygame.Surface, scroll_offset: float):
        """Draw mountains and all scenery objects."""
        # --- Distant mountains (very slow parallax) ---
        mt_offset = int(scroll_offset * 0.05) % 40
        for mx, mh, mw in self.mountain_points:
            pts = [(mx, 240 + mt_offset),
                   (mx + mw // 2, 240 - mh + mt_offset),
                   (mx + mw, 240 + mt_offset)]
            pygame.draw.polygon(surface, MOUNTAIN, pts)

        # --- Individual objects ---
        for obj in self.objects:
            x, y = int(obj["x"]), int(obj["y"])
            s = obj["size"]

            if obj["kind"] == "tree":
                # Trunk
                tw = int(6 * s)
                th = int(20 * s)
                pygame.draw.rect(surface, TREE_TRUNK,
                                 (x - tw // 2, y, tw, th))
                # Canopy (triangle-ish)
                cw = int(22 * s)
                ch = int(24 * s)
                pts = [(x - cw // 2, y),
                       (x, y - ch),
                       (x + cw // 2, y)]
                pygame.draw.polygon(surface, TREE_GREEN, pts)

            elif obj["kind"] == "sign":
                # Post
                pygame.draw.rect(surface, LIGHT_GRAY, (x - 1, y - 20, 3, 25))
                # Sign board
                pygame.draw.rect(surface, SIGN_BLUE,
                                 (x - 10, y - 28, 20, 12))
                pygame.draw.rect(surface, WHITE,
                                 (x - 8, y - 26, 16, 8))

            elif obj["kind"] == "bush":
                bw = int(18 * s)
                bh = int(10 * s)
                pygame.draw.ellipse(surface, TREE_GREEN,
                                    (x - bw // 2, y - bh // 2, bw, bh))
                darker = (20, 90, 30)
                pygame.draw.ellipse(surface, darker,
                                    (x - bw // 3, y - bh // 3, bw // 2, bh // 2))

            elif obj["kind"] == "pole":
                pygame.draw.rect(surface, LIGHT_GRAY, (x, y - 30, 3, 35))
                pygame.draw.rect(surface, FUEL_YELLOW, (x - 3, y - 32, 9, 4))


# ---------------------------------------------------------------------------
#  HUD RENDERER
# ---------------------------------------------------------------------------

class HUD:
    """Draws the speedometer, fuel gauge, score, distance, and gear info."""

    def __init__(self):
        self.font_large = pygame.font.SysFont("consolas", 38, bold=True)
        self.font_med   = pygame.font.SysFont("consolas", 22, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 16)
        self.font_tiny  = pygame.font.SysFont("consolas", 13)

        # CRT scanline overlay
        self.scanlines = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for y in range(0, SCREEN_H, 3):
            pygame.draw.line(self.scanlines, (0, 0, 0, 28),
                             (0, y), (SCREEN_W, y))

    def draw(self, surface: pygame.Surface, player: PlayerCar, score: int,
             highscore: int, stage: int, checkpoint_dist: float):
        """Render all HUD elements."""

        # --- Speed display (top-left) ---
        speed_str = f"{int(player.speed_kmh)} km/h"
        speed_surf = self.font_med.render(speed_str, True, SPEED_CYAN)
        # Dark background panel
        pygame.draw.rect(surface, HUD_BG, (10, 8, 160, 30))
        surface.blit(speed_surf, (16, 10))

        # Boost indicator
        if player.boosting:
            boost_text = self.font_tiny.render("TURBO!", True, FUEL_YELLOW)
            surface.blit(boost_text, (130, 14))

        # --- Fuel gauge (top-left, below speed) ---
        fuel_x, fuel_y = 14, 44
        fuel_w, fuel_h = 140, 14
        label = self.font_tiny.render("FUEL", True, LIGHT_GRAY)
        surface.blit(label, (fuel_x, fuel_y - 2))

        # Background bar
        pygame.draw.rect(surface, DARK_GRAY,
                         (fuel_x + 36, fuel_y, fuel_w, fuel_h))
        # Fill
        fill_ratio = player.fuel / FUEL_MAX
        fill_color = FUEL_GREEN if fill_ratio > 0.3 else FUEL_RED
        pygame.draw.rect(surface, fill_color,
                         (fuel_x + 36, fuel_y, int(fuel_w * fill_ratio), fuel_h))
        # Border
        pygame.draw.rect(surface, LIGHT_GRAY,
                         (fuel_x + 36, fuel_y, fuel_w, fuel_h), 1)

        # Low fuel warning
        if fill_ratio < 0.2 and int(pygame.time.get_ticks() / 300) % 2:
            warn = self.font_small.render("LOW FUEL!", True, FUEL_RED)
            surface.blit(warn, (fuel_x + 36, fuel_y + 16))

        # --- Score (top-right) ---
        score_str = f"SCORE: {score:,}"
        score_surf = self.font_med.render(score_str, True, SCORE_YELLOW)
        pygame.draw.rect(surface, HUD_BG,
                         (SCREEN_W - score_surf.get_width() - 24, 8,
                          score_surf.get_width() + 16, 30))
        surface.blit(score_surf, (SCREEN_W - score_surf.get_width() - 16, 10))

        # High score
        hi_str = f"HI: {highscore:,}"
        hi_surf = self.font_tiny.render(hi_str, True, MID_GRAY)
        surface.blit(hi_surf, (SCREEN_W - hi_surf.get_width() - 16, 40))

        # --- Stage / distance progress (top-centre) ---
        stage_str = f"STAGE {stage}"
        stage_surf = self.font_small.render(stage_str, True, WHITE)
        surface.blit(stage_surf,
                     (SCREEN_W // 2 - stage_surf.get_width() // 2, 8))

        # Distance to next checkpoint
        remaining = max(0, checkpoint_dist - player.distance_m)
        dist_str = f"{remaining / 1000:.1f} km to checkpoint"
        dist_surf = self.font_tiny.render(dist_str, True, LIGHT_GRAY)
        surface.blit(dist_surf,
                     (SCREEN_W // 2 - dist_surf.get_width() // 2, 28))

        # Progress bar
        prog_w = 200
        prog_x = SCREEN_W // 2 - prog_w // 2
        prog_y = 44
        progress = min(1.0, player.distance_m / checkpoint_dist)
        pygame.draw.rect(surface, DARK_GRAY, (prog_x, prog_y, prog_w, 8))
        pygame.draw.rect(surface, GREEN,
                         (prog_x, prog_y, int(prog_w * progress), 8))
        pygame.draw.rect(surface, LIGHT_GRAY, (prog_x, prog_y, prog_w, 8), 1)

        # Distance in km
        km_str = f"{player.distance_m / 1000:.2f} km"
        km_surf = self.font_tiny.render(km_str, True, MID_GRAY)
        surface.blit(km_surf,
                     (SCREEN_W // 2 - km_surf.get_width() // 2, 54))

    def draw_scanlines(self, surface: pygame.Surface):
        surface.blit(self.scanlines, (0, 0))


# ---------------------------------------------------------------------------
#  CRASH / EXPLOSION EFFECT
# ---------------------------------------------------------------------------

class CrashEffect:
    """Simple expanding debris particles shown on crash."""

    def __init__(self, x: float, y: float):
        self.particles: list[dict] = []
        for _ in range(35):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 350)
            self.particles.append({
                "x": x, "y": y,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": random.uniform(0.4, 1.2),
                "max_life": 1.2,
                "size": random.randint(2, 7),
                "color": random.choice([P_RED, FUEL_YELLOW, WHITE, ORANGE, (200, 80, 30)])
            })
        self.alive = True

    def update(self, dt: float):
        for p in self.particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 200 * dt  # gravity
            p["life"] -= dt
        self.particles = [p for p in self.particles if p["life"] > 0]
        if not self.particles:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        for p in self.particles:
            alpha = max(0, p["life"] / p["max_life"])
            sz = max(1, int(p["size"] * alpha))
            c = tuple(int(ch * alpha) for ch in p["color"])
            pygame.draw.rect(surface, c,
                             (int(p["x"]) - sz // 2,
                              int(p["y"]) - sz // 2, sz, sz))


# ---------------------------------------------------------------------------
#  GAME (main controller)
# ---------------------------------------------------------------------------

class Game:
    """
    Master game controller.

    States:
      MENU       — title screen
      PLAYING    — active gameplay
      GAME_OVER  — crash or out of fuel
      STAGE_CLEAR — reached a checkpoint
      WIN        — completed all stages
    """

    MENU        = 0
    PLAYING     = 1
    GAME_OVER   = 2
    STAGE_CLEAR = 3
    WIN         = 4
    LEADERBOARD = 5

    def __init__(self):
        pygame.init()
        # pygame.mixer.init()  # SFX: uncomment for sound support
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("ROAD FIGHTER RETRO")
        self.clock = pygame.time.Clock()

        self.hud = HUD()
        self.road = Road()
        self.scenery = Scenery()
        self.player = PlayerCar()
        self.audio = AudioAid()
        self._was_boosting = False

        self.traffic: list[TrafficCar] = []
        self.oil_slicks: list[OilSlick] = []
        self.crash_effects: list[CrashEffect] = []

        self.score = 0
        self.highscore = load_highscore()
        self.leaderboard = load_leaderboard()
        self.stage = 1
        self.checkpoint_dist = CHECKPOINT_DIST
        self.state = self.MENU
        self.score_submitted = False

        # Spawn accumulators
        self.traffic_spawn_accum = 0.0
        self.oil_spawn_accum = 0.0
        self.last_spawn_y = -999.0

        # Stage clear animation timer
        self.state_timer = 0.0

        # Difficulty ramp (0.0 → 1.0 over the course of stages)
        self.difficulty = 0.0

    def new_game(self):
        """Reset everything for a fresh game."""
        self.player.reset()
        self.traffic.clear()
        self.oil_slicks.clear()
        self.crash_effects.clear()
        self.score = 0
        self.stage = 1
        self.checkpoint_dist = CHECKPOINT_DIST
        self.state = self.PLAYING
        self.score_submitted = False
        self.traffic_spawn_accum = 0.0
        self.oil_spawn_accum = 0.0
        self.last_spawn_y = -999.0
        self.difficulty = 0.0
        self.road.scroll_offset = 0.0
        self.scenery.objects.clear()
        self._was_boosting = False

    def _next_stage(self):
        """Advance to the next stage after checkpoint."""
        self.stage += 1
        if self.stage > STAGES:
            self.state = self.WIN
            self.state_timer = 0.0
            self._update_highscore()
            self.audio.play("win")
            return

        # Keep player state but reset distance for next checkpoint
        self.checkpoint_dist += CHECKPOINT_DIST
        self.traffic.clear()
        self.oil_slicks.clear()
        self.player.fuel = min(FUEL_MAX, self.player.fuel + 30)  # bonus fuel
        self.state = self.PLAYING
        self.difficulty = min(1.0, self.stage / STAGES)
        self.audio.play("checkpoint")

    def _update_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.highscore)

    def _record_score(self):
        """Store the current run in leaderboard once per run."""
        if self.score_submitted or self.score <= 0:
            return
        self.leaderboard = add_to_leaderboard("PLAYER", self.score)
        self.highscore = max(self.highscore, self.score)
        self.score_submitted = True

    # ---- spawning ----

    def _spawn_traffic(self, dt: float):
        """Procedurally spawn traffic cars ahead of the player."""
        scroll = self.player.scroll_speed
        if scroll < 30:
            return

        # Difficulty-scaled spawn rate
        rate = TRAFFIC_BASE_RATE + (TRAFFIC_MAX_RATE - TRAFFIC_BASE_RATE) * self.difficulty
        self.traffic_spawn_accum += rate * dt

        while self.traffic_spawn_accum >= 1.0:
            self.traffic_spawn_accum -= 1.0

            lane = random.randint(0, NUM_LANES - 1)
            x = lane_center_x(lane)

            # Don't spawn too close to another car
            too_close = any(abs(t.y - (-60)) < TRAFFIC_MIN_GAP and
                            abs(t.x - x) < LANE_WIDTH
                            for t in self.traffic)
            if too_close:
                continue

            # Determine if this is a fuel car
            is_fuel = random.random() < FUEL_CAR_CHANCE

            # Traffic speed: slower than player for overtaking feel
            traffic_speed = random.uniform(80, 200) + self.difficulty * 60

            self.traffic.append(
                TrafficCar(x, -60, traffic_speed, is_fuel=is_fuel))

    def _spawn_oil(self, dt: float):
        """Spawn oil slicks on the road."""
        rate = OIL_BASE_RATE + (OIL_MAX_RATE - OIL_BASE_RATE) * self.difficulty
        self.oil_spawn_accum += rate * dt

        while self.oil_spawn_accum >= 1.0:
            self.oil_spawn_accum -= 1.0
            x = random.uniform(ROAD_LEFT + 30, ROAD_RIGHT - 30)
            self.oil_slicks.append(OilSlick(x, -40))

    # ---- collision ----

    def _check_collisions(self):
        """Check player against traffic, oil slicks, and road edges."""
        player = self.player
        if not player.alive or player.invuln_timer > 0:
            return

        p_rect = player.get_rect()

        # --- Wall collision ---
        if player.x - CAR_W // 2 < ROAD_LEFT - 5:
            if player.crash():
                self._trigger_crash()
                return
        if player.x + CAR_W // 2 > ROAD_RIGHT + 5:
            if player.crash():
                self._trigger_crash()
                return

        # --- Traffic collision ---
        for t in self.traffic:
            if not t.active:
                continue
            t_rect = t.get_rect()
            if p_rect.colliderect(t_rect):
                if t.is_fuel:
                    # Fuel pickup — not a crash
                    player.add_fuel(FUEL_PICKUP)
                    t.active = False
                    self.score += 100
                    self.audio.play("fuel_pickup")
                else:
                    if player.crash():
                        self._trigger_crash()
                        return

            # Overtake scoring: player passed this car cleanly
            if (not t.scored and not t.is_fuel and t.active
                    and t.y > player.y + CAR_H):
                t.scored = True
                self.score += OVERTAKE_BONUS

        # --- Oil slick collision ---
        for oil in self.oil_slicks:
            if not oil.active:
                continue
            if p_rect.colliderect(oil.get_rect()):
                player.start_spin()
                oil.active = False

    def _trigger_crash(self):
        """Start crash sequence."""
        self.crash_effects.append(
            CrashEffect(self.player.x, self.player.y))
        self.state = self.GAME_OVER
        self.state_timer = 0.0
        self._record_score()
        self._update_highscore()
        self.audio.play("crash")

    # ---- update ----

    def update(self, dt: float):
        """Main per-frame update."""
        if self.state == self.PLAYING:
            keys = pygame.key.get_pressed()
            self.player.update(dt, keys)

            # Audio cues for assistive feedback
            self.audio.update_low_fuel(dt, self.player.fuel / FUEL_MAX, True)
            if self.player.boosting and not self._was_boosting:
                self.audio.play("boost_on")
            self._was_boosting = self.player.boosting

            scroll = self.player.scroll_speed
            self.road.update(dt, scroll)
            self.scenery.update(dt, scroll)

            # Update traffic
            for t in self.traffic:
                t.update(dt, scroll)
            self.traffic = [t for t in self.traffic if t.active]

            # Update oil slicks
            for oil in self.oil_slicks:
                oil.update(dt, scroll)
            self.oil_slicks = [o for o in self.oil_slicks if o.active]

            # Spawning
            self._spawn_traffic(dt)
            self._spawn_oil(dt)

            # Collisions
            self._check_collisions()

            # Score from speed
            self.score += int(SPEED_BONUS_RATE * (self.player.speed_kmh / MAX_SPEED) * dt * 100)

            # Difficulty ramp
            self.difficulty = min(1.0,
                                  (self.player.distance_m / self.checkpoint_dist)
                                  * 0.6 + (self.stage - 1) / STAGES * 0.4)

            # Fuel death
            if self.player.fuel <= 0 and self.player.speed_kmh < 5:
                self.player.alive = False
                self.state = self.GAME_OVER
                self.state_timer = 0.0
                self._record_score()
                self._update_highscore()
                self.audio.play("game_over")

            # Checkpoint reached
            if self.player.distance_m >= self.checkpoint_dist:
                self.state = self.STAGE_CLEAR
                self.state_timer = 0.0
                self.score += 2000  # stage clear bonus
                self.audio.play("checkpoint")

        elif self.state in (self.GAME_OVER, self.STAGE_CLEAR, self.WIN):
            self.state_timer += dt
            # Keep updating crash effects
            for fx in self.crash_effects:
                fx.update(dt)
            self.crash_effects = [fx for fx in self.crash_effects if fx.alive]

    # ---- drawing ----

    def _draw_playing(self):
        """Render the active game."""
        # Sky gradient
        for y in range(0, 250, 4):
            t = y / 250
            r = int(SKY_TOP[0] + (SKY_BOTTOM[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOTTOM[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOTTOM[2] - SKY_TOP[2]) * t)
            pygame.draw.rect(self.screen, (r, g, b), (0, y, SCREEN_W, 4))

        # Scenery behind road
        self.scenery.draw(self.screen, self.road.scroll_offset)

        # Road
        self.road.draw(self.screen)

        # Oil slicks (on road surface)
        for oil in self.oil_slicks:
            oil.draw(self.screen)

        # Traffic cars
        for t in self.traffic:
            t.draw(self.screen)

        # Crash effects
        for fx in self.crash_effects:
            fx.draw(self.screen)

        # Player
        self.player.draw(self.screen)

        # HUD
        self.hud.draw(self.screen, self.player, self.score, self.highscore,
                      self.stage, self.checkpoint_dist)

        aid_status = "AUDIO AID: OFF" if self.audio.muted else "AUDIO AID: ON"
        aid_color = FUEL_RED if self.audio.muted else FUEL_GREEN
        aid_text = self.hud.font_tiny.render(aid_status, True, aid_color)
        self.screen.blit(aid_text, (14, 66))

    def _draw_menu(self):
        """Title screen."""
        self.screen.fill(BLACK)

        # Decorative road
        pygame.draw.rect(self.screen, ASPHALT, (300, 0, 200, SCREEN_H))
        for dy in range(0, SCREEN_H, 50):
            pygame.draw.rect(self.screen, DASH_WHITE, (398, dy, 4, 28))
        pygame.draw.rect(self.screen, RUMBLE_RED, (296, 0, 6, SCREEN_H))
        pygame.draw.rect(self.screen, RUMBLE_RED, (498, 0, 6, SCREEN_H))

        cx = SCREEN_W // 2

        # Title
        title = self.hud.font_large.render("ROAD FIGHTER", True, P_RED)
        self.screen.blit(title, (cx - title.get_width() // 2, 100))

        sub = self.hud.font_small.render("R E T R O", True, FUEL_YELLOW)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 148))

        # Mini car icon
        pygame.draw.rect(self.screen, P_RED, (cx - 12, 200, 24, 40))
        pygame.draw.rect(self.screen, P_RED_DARK, (cx - 8, 212, 16, 14))
        pygame.draw.rect(self.screen, FUEL_YELLOW, (cx - 8, 198, 5, 4))
        pygame.draw.rect(self.screen, FUEL_YELLOW, (cx + 3, 198, 5, 4))

        # Instructions
        instructions = [
            "Arrows: Steer & Speed",
            "Space: TURBO BOOST",
            "M: Audio Aid On/Off",
            "L: Leaderboard",
            "Dodge traffic, collect fuel (yellow cars)",
            "Reach checkpoints before fuel runs out!",
            "",
            "Press ENTER to start",
        ]
        for i, line in enumerate(instructions):
            c = WHITE if i < 4 else (SPEED_CYAN if line else WHITE)
            t = self.hud.font_small.render(line, True, c)
            self.screen.blit(t, (cx - t.get_width() // 2, 280 + i * 28))

        # High score
        hi = self.hud.font_tiny.render(f"HIGH SCORE: {self.highscore:,}", True, MID_GRAY)
        self.screen.blit(hi, (cx - hi.get_width() // 2, SCREEN_H - 40))

    def _draw_game_over(self):
        """Game over overlay on top of the game scene."""
        self._draw_playing()

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        cx = SCREEN_W // 2

        title = self.hud.font_large.render("GAME OVER", True, P_RED)
        self.screen.blit(title, (cx - title.get_width() // 2, 160))

        # Reason
        if self.player.fuel <= 0:
            reason = "OUT OF FUEL!"
            reason_c = FUEL_YELLOW
        else:
            reason = "CRASHED!"
            reason_c = ORANGE
        reason_surf = self.hud.font_med.render(reason, True, reason_c)
        self.screen.blit(reason_surf, (cx - reason_surf.get_width() // 2, 215))

        # Stats
        stats = [
            f"Distance: {self.player.distance_m / 1000:.2f} km",
            f"Score: {self.score:,}",
            f"High Score: {self.highscore:,}",
            f"Stage: {self.stage} / {STAGES}",
        ]
        for i, line in enumerate(stats):
            t = self.hud.font_small.render(line, True, WHITE)
            self.screen.blit(t, (cx - t.get_width() // 2, 270 + i * 30))

        if self.score >= self.highscore and self.score > 0:
            new_best = self.hud.font_med.render("NEW HIGH SCORE!", True, SCORE_YELLOW)
            self.screen.blit(new_best, (cx - new_best.get_width() // 2, 410))

        if self.state_timer > 1.0:
            hint = self.hud.font_small.render("Press ENTER to continue", True, SPEED_CYAN)
            self.screen.blit(hint, (cx - hint.get_width() // 2, 460))

    def _draw_stage_clear(self):
        """Stage clear celebration overlay."""
        self._draw_playing()

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        cx = SCREEN_W // 2

        title = self.hud.font_large.render("CHECKPOINT!", True, GREEN)
        self.screen.blit(title, (cx - title.get_width() // 2, 180))

        stage_str = f"Stage {self.stage} Complete"
        stage_surf = self.hud.font_med.render(stage_str, True, WHITE)
        self.screen.blit(stage_surf, (cx - stage_surf.get_width() // 2, 240))

        bonus = self.hud.font_med.render("+2000 BONUS!", True, SCORE_YELLOW)
        self.screen.blit(bonus, (cx - bonus.get_width() // 2, 280))

        score_t = self.hud.font_small.render(f"Score: {self.score:,}", True, LIGHT_GRAY)
        self.screen.blit(score_t, (cx - score_t.get_width() // 2, 330))

        if self.state_timer > 1.5:
            hint = self.hud.font_small.render("Press ENTER for next stage", True, SPEED_CYAN)
            self.screen.blit(hint, (cx - hint.get_width() // 2, 400))

    def _draw_win(self):
        """Victory screen after all stages."""
        self.screen.fill(BLACK)
        cx = SCREEN_W // 2

        # Celebratory pixel art
        title = self.hud.font_large.render("YOU WIN!", True, SCORE_YELLOW)
        self.screen.blit(title, (cx - title.get_width() // 2, 100))

        sub = self.hud.font_med.render("All Stages Cleared!", True, GREEN)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 160))

        # Trophy (simple pixel art)
        trophy_x, trophy_y = cx, 230
        pygame.draw.rect(self.screen, SCORE_YELLOW,
                         (trophy_x - 20, trophy_y, 40, 35))
        pygame.draw.rect(self.screen, SCORE_YELLOW,
                         (trophy_x - 30, trophy_y + 5, 60, 10))
        pygame.draw.rect(self.screen, SCORE_YELLOW,
                         (trophy_x - 10, trophy_y + 35, 20, 10))
        pygame.draw.rect(self.screen, SCORE_YELLOW,
                         (trophy_x - 18, trophy_y + 45, 36, 6))
        pygame.draw.rect(self.screen, (200, 170, 30),
                         (trophy_x - 12, trophy_y + 8, 24, 18))

        stats = [
            f"Final Score: {self.score:,}",
            f"Distance: {self.player.distance_m / 1000:.2f} km",
            f"High Score: {self.highscore:,}",
        ]
        for i, line in enumerate(stats):
            t = self.hud.font_med.render(line, True, WHITE)
            self.screen.blit(t, (cx - t.get_width() // 2, 310 + i * 40))

        if self.state_timer > 2.0:
            hint = self.hud.font_small.render("Press ENTER to play again", True, SPEED_CYAN)
            self.screen.blit(hint, (cx - hint.get_width() // 2, 480))

    def _draw_leaderboard(self):
        """Dedicated leaderboard page similar to other games."""
        self.screen.fill(BLACK)
        cx = SCREEN_W // 2

        title = self.hud.font_large.render("LEADERBOARD", True, SCORE_YELLOW)
        self.screen.blit(title, (cx - title.get_width() // 2, 56))

        panel = pygame.Rect(170, 130, 460, 340)
        pygame.draw.rect(self.screen, HUD_BG, panel, border_radius=10)
        pygame.draw.rect(self.screen, MID_GRAY, panel, 2, border_radius=10)

        header_rank = self.hud.font_small.render("#", True, LIGHT_GRAY)
        header_name = self.hud.font_small.render("NAME", True, LIGHT_GRAY)
        header_score = self.hud.font_small.render("SCORE", True, LIGHT_GRAY)
        self.screen.blit(header_rank, (panel.x + 18, panel.y + 16))
        self.screen.blit(header_name, (panel.x + 58, panel.y + 16))
        self.screen.blit(header_score, (panel.right - 108, panel.y + 16))

        rows = self.leaderboard if self.leaderboard else load_leaderboard()
        if not rows:
            empty = self.hud.font_med.render("No scores yet.", True, MID_GRAY)
            self.screen.blit(empty, (cx - empty.get_width() // 2, panel.y + 150))
        else:
            start_y = panel.y + 52
            row_h = 28
            for i, row in enumerate(rows[:MAX_LEADERBOARD]):
                y = start_y + i * row_h
                rank_c = SCORE_YELLOW if i == 0 else LIGHT_GRAY
                name_c = WHITE
                score_c = FUEL_GREEN if i == 0 else SPEED_CYAN

                rank = self.hud.font_small.render(f"{i + 1}.", True, rank_c)
                name = self.hud.font_small.render(str(row.get("name", "PLAYER"))[:12], True, name_c)
                score = self.hud.font_small.render(f"{int(row.get('score', 0)):,}", True, score_c)

                self.screen.blit(rank, (panel.x + 18, y))
                self.screen.blit(name, (panel.x + 58, y))
                self.screen.blit(score, (panel.right - 108, y))

        hint = self.hud.font_small.render("Press ESC or ENTER to return", True, SPEED_CYAN)
        self.screen.blit(hint, (cx - hint.get_width() // 2, 510))

    # ---- main loop ----

    def run(self):
        """Entry point — game loop runs until quit."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # prevent physics explosion on lag

            # ---- events ----
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_0:
                        return_to_start_page()

                    if event.key == pygame.K_m:
                        muted = self.audio.toggle_mute()
                        if not muted:
                            self.audio.play("menu_select")

                    if event.key == pygame.K_l and self.state == self.MENU:
                        self.leaderboard = load_leaderboard()
                        self.state = self.LEADERBOARD
                        self.audio.play("menu_select")
                        continue

                    if event.key == pygame.K_ESCAPE:
                        if self.state == self.PLAYING:
                            self.state = self.MENU
                        elif self.state == self.LEADERBOARD:
                            self.state = self.MENU
                            self.audio.play("menu_select")
                        else:
                            running = False

                    if event.key == pygame.K_RETURN:
                        if self.state == self.MENU:
                            self.audio.play("menu_select")
                            self.new_game()
                        elif self.state == self.GAME_OVER and self.state_timer > 1.0:
                            self.audio.play("menu_select")
                            self.state = self.MENU
                        elif self.state == self.STAGE_CLEAR and self.state_timer > 1.5:
                            self.audio.play("menu_select")
                            self._next_stage()
                        elif self.state == self.WIN and self.state_timer > 2.0:
                            self.audio.play("menu_select")
                            self.state = self.MENU
                        elif self.state == self.LEADERBOARD:
                            self.audio.play("menu_select")
                            self.state = self.MENU

            # ---- update ----
            self.update(dt)

            # ---- draw ----
            if self.state == self.MENU:
                self._draw_menu()
            elif self.state == self.PLAYING:
                self._draw_playing()
            elif self.state == self.GAME_OVER:
                self._draw_game_over()
            elif self.state == self.STAGE_CLEAR:
                self._draw_stage_clear()
            elif self.state == self.WIN:
                self._draw_win()
            elif self.state == self.LEADERBOARD:
                self._draw_leaderboard()

            # Scanline overlay
            self.hud.draw_scanlines(self.screen)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
#  ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    game = Game()
    game.run()