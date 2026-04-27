#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║  MATH BOMBERMAN — Bomb your way to mathematical mastery!         ║
║                                                                   ║
║  Controls:                                                        ║
║    Arrow keys / WASD   Move on grid                              ║
║    SPACE               Place bomb                                 ║
║    R                   Restart current level                      ║
║    ESC                 Quit                                       ║
║                                                                   ║
║  Destroy ? Question Blocks to start a math challenge.             ║
║  Bomb the answer-target with the CORRECT answer to win a power-up.║
║  Wrong answer spawns extra enemies. Clear all blocks to advance!  ║
╚═══════════════════════════════════════════════════════════════════╝
"""

import pygame
import math
import random
import json
import os
import subprocess
import sys
from collections import deque
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════
#  INITIALIZATION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════
pygame.init()

WIDTH, HEIGHT = 960, 640
HUD_H = 64
TILE = 48
GRID_W = WIDTH // TILE        # 20
GRID_H = (HEIGHT - HUD_H) // TILE  # 12
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Math Bomberman")
clock = pygame.time.Clock()


def load_player_sprite() -> Optional[pygame.Surface]:
    """Load the player sprite, trying common filename variants."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "griffin.png"),
        os.path.join(base_dir, "Griffin.png"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                size = int(TILE * 0.8)
                return pygame.transform.smoothscale(img, (size, size))
            except pygame.error:
                return None
    return None


PLAYER_SPRITE = load_player_sprite()

# ═══════════════════════════════════════════════════════════════════
#  COLOR PALETTE
# ═══════════════════════════════════════════════════════════════════
BLACK        = (10, 10, 16)
WHITE        = (240, 240, 245)
BG_COLOR     = (35, 60, 45)        # grass-y background
BG_ALT       = (28, 50, 38)
HUD_BG       = (15, 12, 28)
HARD_WALL    = (90, 90, 110)
HARD_WALL_HI = (130, 130, 155)
HARD_WALL_LO = (55, 55, 75)
SOFT_BLOCK   = (180, 110, 60)
SOFT_BLOCK_HI = (220, 150, 90)
SOFT_BLOCK_LO = (130, 70, 35)
QUESTION_BLK = (80, 130, 220)
QUESTION_HI  = (130, 170, 255)
ANSWER_BG    = (60, 50, 100)
ANSWER_BORDER = (180, 160, 255)
ANSWER_CORRECT = (50, 220, 100)
ANSWER_WRONG  = (230, 70, 70)
PLAYER_COL   = (255, 220, 80)
PLAYER_DARK  = (200, 160, 30)
ENEMY_COL    = (220, 60, 90)
ENEMY_DARK   = (140, 30, 55)
ENEMY_FAST   = (160, 80, 220)
BOMB_COL     = (30, 30, 30)
BOMB_HIGHLIGHT = (90, 90, 90)
FUSE_COL     = (255, 180, 50)
EXPLOSION_C  = (255, 200, 60)
EXPLOSION_H  = (255, 240, 180)
EXPLOSION_O  = (255, 100, 30)
GOLD         = (255, 210, 50)
RED          = (230, 55, 65)
GREEN        = (50, 210, 90)
BLUE         = (60, 140, 255)
CYAN         = (80, 220, 230)
PURPLE       = (160, 80, 220)
ORANGE       = (255, 150, 40)
PINK         = (255, 100, 150)
GREY         = (100, 100, 120)
GREY_DIM     = (60, 60, 75)
GREY_DARK    = (35, 35, 50)
PANEL_BG     = (18, 16, 35)
PANEL_BORDER = (70, 60, 110)
INPUT_BG     = (25, 22, 45)
CURSOR_COL   = (255, 220, 100)
PU_BOMB      = (100, 200, 255)    # extra bomb power-up
PU_RANGE     = (255, 100, 100)    # bigger blast power-up
PU_SPEED     = (100, 255, 150)    # speed power-up

# ═══════════════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════════════
FONT_XL     = pygame.font.SysFont("consolas", 52, bold=True)
FONT_LG     = pygame.font.SysFont("consolas", 36, bold=True)
FONT_MD     = pygame.font.SysFont("consolas", 22, bold=True)
FONT_SM     = pygame.font.SysFont("consolas", 18)
FONT_XS     = pygame.font.SysFont("consolas", 14)
FONT_HUD    = pygame.font.SysFont("consolas", 17, bold=True)
FONT_TILE   = pygame.font.SysFont("consolas", 24, bold=True)
FONT_INPUT  = pygame.font.SysFont("consolas", 30, bold=True)
FONT_LB     = pygame.font.SysFont("consolas", 17, bold=True)
FONT_LB_HDR = pygame.font.SysFont("consolas", 20, bold=True)

# ═══════════════════════════════════════════════════════════════════
#  TILE TYPES
# ═══════════════════════════════════════════════════════════════════
T_EMPTY    = 0
T_HARD     = 1   # indestructible wall
T_SOFT     = 2   # destructible block
T_QUESTION = 3   # destructible question block — triggers math
T_ANSWER   = 4   # answer target (created during math challenge)

# ═══════════════════════════════════════════════════════════════════
#  GAMEPLAY CONSTANTS
# ═══════════════════════════════════════════════════════════════════
BOMB_TIMER       = 100     # frames until detonation (~3.0s)
EXPLOSION_FRAMES = 16      # how long explosion is visible/dangerous
PLAYER_BASE_SPEED = 3.0    # pixels per frame (grid-snapping handled separately)
ENEMY_SPEED      = 1.5
INVULN_FRAMES    = 90      # i-frames after taking damage
# Set this based on how the source sprite is drawn at rest.
# False means the image naturally faces left; True means it naturally faces right.
PLAYER_SPRITE_POINTS_RIGHT = False

# ═══════════════════════════════════════════════════════════════════
#  LEADERBOARD (JSON persistence)
# ═══════════════════════════════════════════════════════════════════
LB_FILE = "leaderboardBM.json"
MAX_LB  = 10


def load_leaderboard() -> list:
    if os.path.exists(LB_FILE):
        try:
            with open(LB_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                # Time-trial board: lower completion time is better.
                return sorted(
                    data,
                    key=lambda e: (e.get("dnf", False), e.get("time", float("inf"))),
                )[:MAX_LB]
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_leaderboard(board: list):
    try:
        with open(LB_FILE, "w") as f:
            json.dump(board[:MAX_LB], f, indent=2)
    except IOError:
        pass


def add_to_leaderboard(name: str, time_sec: float, dnf: bool = False) -> Tuple[list, bool]:
    board = load_leaderboard()
    entry = {"name": name, "time": round(float(time_sec), 2), "dnf": bool(dnf)}
    board.append(entry)
    board.sort(key=lambda e: (e.get("dnf", False), e.get("time", float("inf"))))
    board = board[:MAX_LB]
    save_leaderboard(board)
    return board, entry in board


# ═══════════════════════════════════════════════════════════════════
#  SOUND (procedural beeps)
# ═══════════════════════════════════════════════════════════════════
SND_ON = False
try:
    pygame.mixer.init(22050, -16, 1, 256)
    SND_ON = True
except Exception:
    pass


def _synth(freq, ms, vol=0.12):
    if not SND_ON:
        return None
    try:
        sr = 22050
        n = int(sr * ms / 1000)
        buf = bytearray(n * 2)
        amp = int(32767 * vol)
        for i in range(n):
            decay = max(0.0, 1.0 - i / n * 0.6)
            v = int(amp * decay * math.sin(2 * math.pi * freq * i / sr))
            v = max(-32768, min(32767, v))
            buf[2 * i] = v & 0xFF
            buf[2 * i + 1] = (v >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))
    except Exception:
        return None


SFX_BOMB    = _synth(150, 250, 0.15)
SFX_PLACE   = _synth(400, 60, 0.08)
SFX_OK      = _synth(880, 160, 0.14)
SFX_BAD     = _synth(180, 220, 0.12)
SFX_HURT    = _synth(220, 180, 0.13)
SFX_LVL     = _synth(1047, 280, 0.13)
SFX_PU      = _synth(660, 120, 0.11)
SFX_TYPE    = _synth(900, 25, 0.06)


def sfx(s):
    if s:
        try:
            s.play()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
#  UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════════
def txt_c(surf, text, font, color, y, x=None):
    r = font.render(text, True, color)
    cx = (x if x is not None else WIDTH // 2) - r.get_width() // 2
    surf.blit(r, (cx, y - r.get_height() // 2))
    return r


def txt_sh(surf, text, font, color, y, x=None):
    sc = tuple(max(0, c // 5) for c in color)
    txt_c(surf, text, font, sc, y + 2, x)
    txt_c(surf, text, font, color, y, x)


def grid_to_px(gx, gy):
    """Convert grid coords to pixel center, accounting for HUD."""
    return (gx * TILE + TILE // 2, gy * TILE + TILE // 2 + HUD_H)


def px_to_grid(px, py):
    return (px // TILE, (py - HUD_H) // TILE)


def format_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    mins = int(seconds // 60)
    secs = seconds - mins * 60
    return f"{mins:02d}:{secs:05.2f}"


# ═══════════════════════════════════════════════════════════════════
#  PARTICLE SYSTEM
# ═══════════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'life', 'max_life', 'size',
                 'is_text', 'text', 'gravity')

    def __init__(self, x, y, vx, vy, color, life=30, size=3, text=None, gravity=0.05):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.is_text = text is not None
        self.text = text
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not self.is_text:
            self.vy += self.gravity
        else:
            self.vy *= 0.94
        self.life -= 1

    def draw(self, surf):
        a = max(0.0, self.life / self.max_life)
        if self.is_text:
            c = tuple(max(0, int(ch * a)) for ch in self.color)
            ts = FONT_SM.render(self.text, True, c)
            surf.blit(ts, (int(self.x) - ts.get_width() // 2, int(self.y)))
        else:
            r = max(1, int(self.size * a))
            c = tuple(max(0, int(ch * a)) for ch in self.color)
            pygame.draw.circle(surf, c, (int(self.x), int(self.y)), r)


g_parts: List[Particle] = []


def emit(x, y, color, n=14, speed=4.5, life=28, size=3, gravity=0.05):
    for _ in range(n):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(0.8, speed)
        g_parts.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd - 1.2,
            color, random.randint(life // 2, life),
            random.uniform(size * 0.5, size), gravity=gravity))


def emit_text(x, y, text, color, life=70):
    g_parts.append(Particle(x, y - 10, 0, -1.0, color, life, text=text, gravity=0))


# ═══════════════════════════════════════════════════════════════════
#  BOMB CLASS
# ═══════════════════════════════════════════════════════════════════
class Bomb:
    def __init__(self, gx, gy, range_, owner='player'):
        self.gx, self.gy = gx, gy
        self.timer = BOMB_TIMER
        self.range = range_
        self.owner = owner
        self.exploded = False

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.exploded = True

    def draw(self, surf):
        cx, cy = grid_to_px(self.gx, self.gy)
        # Pulse based on time left
        pulse = 1.0 + 0.15 * math.sin(self.timer * 0.4)
        r = int(TILE * 0.35 * pulse)
        # Body
        pygame.draw.circle(surf, BOMB_COL, (cx, cy + 2), r + 2)
        pygame.draw.circle(surf, (50, 50, 50), (cx, cy), r)
        # Highlight
        pygame.draw.circle(surf, BOMB_HIGHLIGHT, (cx - r // 3, cy - r // 3), r // 4)
        # Fuse
        fuse_x = cx + int(math.sin(self.timer * 0.2) * 3)
        pygame.draw.line(surf, (160, 100, 50), (cx, cy - r), (fuse_x, cy - r - 8), 2)
        # Spark
        if self.timer % 8 < 4:
            pygame.draw.circle(surf, FUSE_COL, (fuse_x, cy - r - 10), 3)
            pygame.draw.circle(surf, (255, 255, 200), (fuse_x, cy - r - 10), 1)


# ═══════════════════════════════════════════════════════════════════
#  EXPLOSION CLASS
# ═══════════════════════════════════════════════════════════════════
class Explosion:
    """A cross-shaped explosion. Holds a list of grid cells affected."""

    def __init__(self, cells: List[Tuple[int, int]]):
        self.cells = cells  # list of (gx, gy)
        self.timer = EXPLOSION_FRAMES
        self.alive = True

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surf):
        # Stronger alpha early, fades out
        frac = self.timer / EXPLOSION_FRAMES
        for (gx, gy) in self.cells:
            cx, cy = grid_to_px(gx, gy)
            # Outer glow
            r_outer = int(TILE * 0.55 * (0.6 + 0.4 * frac))
            r_mid   = int(TILE * 0.40 * (0.6 + 0.4 * frac))
            r_inner = int(TILE * 0.22 * (0.5 + 0.5 * frac))

            glow = pygame.Surface((TILE * 2, TILE * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*EXPLOSION_O, int(120 * frac)), (TILE, TILE), r_outer)
            pygame.draw.circle(glow, (*EXPLOSION_C, int(180 * frac)), (TILE, TILE), r_mid)
            pygame.draw.circle(glow, (*EXPLOSION_H, int(240 * frac)), (TILE, TILE), r_inner)
            surf.blit(glow, (cx - TILE, cy - TILE))


# ═══════════════════════════════════════════════════════════════════
#  POWER-UP CLASS
# ═══════════════════════════════════════════════════════════════════
class PowerUp:
    KIND_BOMB  = 'bomb'    # extra bomb capacity
    KIND_RANGE = 'range'   # bigger blast
    KIND_SPEED = 'speed'   # faster movement

    def __init__(self, gx, gy, kind):
        self.gx, self.gy = gx, gy
        self.kind = kind
        self.alive = True
        self.bob_t = 0.0

    def update(self):
        self.bob_t += 0.1

    def color(self):
        return {self.KIND_BOMB: PU_BOMB, self.KIND_RANGE: PU_RANGE,
                self.KIND_SPEED: PU_SPEED}[self.kind]

    def label(self):
        return {self.KIND_BOMB: "B+", self.KIND_RANGE: "R+",
                self.KIND_SPEED: "S+"}[self.kind]

    def draw(self, surf):
        if not self.alive:
            return
        cx, cy = grid_to_px(self.gx, self.gy)
        bob = int(math.sin(self.bob_t) * 3)
        col = self.color()
        # Glow
        glow = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*col, 60), (TILE // 2, TILE // 2), TILE // 2 - 2)
        surf.blit(glow, (cx - TILE // 2, cy - TILE // 2 + bob))
        # Body
        pygame.draw.rect(surf, col, (cx - 16, cy - 16 + bob, 32, 32), border_radius=6)
        pygame.draw.rect(surf, WHITE, (cx - 16, cy - 16 + bob, 32, 32), 2, border_radius=6)
        # Label
        lbl = FONT_TILE.render(self.label(), True, BLACK)
        surf.blit(lbl, (cx - lbl.get_width() // 2, cy - lbl.get_height() // 2 + bob))


# ═══════════════════════════════════════════════════════════════════
#  ENEMY CLASS
# ═══════════════════════════════════════════════════════════════════
class Enemy:
    def __init__(self, gx, gy, smart=False):
        self.x, self.y = grid_to_px(gx, gy)
        self.x = float(self.x)
        self.y = float(self.y)
        self.dir = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.smart = smart  # smart enemies chase the player
        self.speed = ENEMY_SPEED * (1.45 if smart else 1.0)
        self.alive = True
        self.think_timer = 0
        self.anim_t = 0.0

    @property
    def gx(self):
        return int(self.x // TILE)

    @property
    def gy(self):
        return int((self.y - HUD_H) // TILE)

    def grid_center(self):
        gx, gy = self.gx, self.gy
        cx, cy = grid_to_px(gx, gy)
        return cx, cy, gx, gy

    def _next_step_toward(self, level, start_gx, start_gy, target_gx, target_gy,
                          avoid_cells=None):
        """Return the first (dx, dy) step on a shortest path to target, or None."""
        if (start_gx, start_gy) == (target_gx, target_gy):
            return (0, 0)

        avoid_cells = avoid_cells or set()

        q = deque([(start_gx, start_gy)])
        parent = {(start_gx, start_gy): None}

        while q:
            x, y = q.popleft()
            if (x, y) == (target_gx, target_gy):
                break
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in parent:
                    continue
                if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                    continue
                if (nx, ny) != (target_gx, target_gy) and (nx, ny) in avoid_cells:
                    continue
                # Allow stepping into the player's tile even if occupancy checks differ.
                if (nx, ny) != (target_gx, target_gy) and not level.passable_for_enemy(nx, ny):
                    continue
                parent[(nx, ny)] = (x, y)
                q.append((nx, ny))

        if (target_gx, target_gy) not in parent:
            return None

        node = (target_gx, target_gy)
        while parent[node] is not None and parent[node] != (start_gx, start_gy):
            node = parent[node]
        if parent[node] is None:
            return None
        return (node[0] - start_gx, node[1] - start_gy)

    def _next_step_to_safe(self, level, start_gx, start_gy, danger_cells):
        """Find first step toward nearest non-danger tile."""
        if (start_gx, start_gy) not in danger_cells:
            return (0, 0)

        q = deque([(start_gx, start_gy)])
        parent = {(start_gx, start_gy): None}
        goal = None

        while q:
            x, y = q.popleft()
            if (x, y) != (start_gx, start_gy) and (x, y) not in danger_cells:
                goal = (x, y)
                break
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) in parent:
                    continue
                if not (0 <= nx < GRID_W and 0 <= ny < GRID_H):
                    continue
                if not level.passable_for_enemy(nx, ny):
                    continue
                parent[(nx, ny)] = (x, y)
                q.append((nx, ny))

        if goal is None:
            return None

        node = goal
        while parent[node] is not None and parent[node] != (start_gx, start_gy):
            node = parent[node]
        if parent[node] is None:
            return None
        return (node[0] - start_gx, node[1] - start_gy)

    def update(self, level, player, danger_cells=None):
        if not self.alive:
            return
        self.anim_t += 0.15
        danger_cells = danger_cells or set()

        cx, cy, gx, gy = self.grid_center()
        # Check if at center of tile
        at_center = abs(self.x - cx) < self.speed and abs(self.y - cy) < self.speed

        if at_center:
            self.x, self.y = float(cx), float(cy)
            # Pick a new direction
            self.think_timer -= 1
            choices = []
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                    if level.passable_for_enemy(nx, ny):
                        choices.append((dx, dy))

            safe_choices = [
                (dx, dy) for (dx, dy) in choices
                if (gx + dx, gy + dy) not in danger_cells
            ]

            if choices:
                # Escape first if current tile is about to explode.
                if (gx, gy) in danger_cells:
                    step = self._next_step_to_safe(level, gx, gy, danger_cells)
                    if step in choices:
                        self.dir = step
                    elif safe_choices:
                        self.dir = random.choice(safe_choices)
                    else:
                        self.dir = random.choice(choices)
                elif self.smart:
                    # Smart bots should aggressively chase, only escaping when currently unsafe.
                    step = self._next_step_toward(level, gx, gy, player.gx, player.gy)
                    if step in choices:
                        self.dir = step
                    elif safe_choices:
                        best = min(
                            safe_choices,
                            key=lambda d: abs((gx + d[0]) - player.gx) + abs((gy + d[1]) - player.gy)
                        )
                        self.dir = best
                    else:
                        self.dir = random.choice(choices)
                else:
                    # Basic bots still roam, but now avoid obvious danger.
                    roam_choices = safe_choices if safe_choices else choices
                    if self.dir in roam_choices and random.random() < 0.75:
                        pass
                    else:
                        self.dir = random.choice(roam_choices)
            else:
                self.dir = (0, 0)

        # Move
        dx, dy = self.dir
        self.x += dx * self.speed
        self.y += dy * self.speed

    def hits_player(self, player):
        return abs(self.x - player.x) < TILE * 0.6 and abs(self.y - player.y) < TILE * 0.6

    def draw(self, surf):
        if not self.alive:
            return
        ix, iy = int(self.x), int(self.y)
        col = ENEMY_FAST if self.smart else ENEMY_COL
        col_d = ENEMY_DARK
        # Bouncing offset
        bounce = int(abs(math.sin(self.anim_t)) * 3)
        # Body
        pygame.draw.circle(surf, col_d, (ix, iy + 4 - bounce), 16)
        pygame.draw.circle(surf, col, (ix, iy - bounce), 16)
        # Eyes
        pygame.draw.circle(surf, WHITE, (ix - 5, iy - 3 - bounce), 4)
        pygame.draw.circle(surf, WHITE, (ix + 5, iy - 3 - bounce), 4)
        # Pupils (look in dir of motion)
        eye_off_x = self.dir[0] * 2
        eye_off_y = self.dir[1] * 2
        pygame.draw.circle(surf, BLACK, (ix - 5 + eye_off_x, iy - 3 - bounce + eye_off_y), 2)
        pygame.draw.circle(surf, BLACK, (ix + 5 + eye_off_x, iy - 3 - bounce + eye_off_y), 2)
        # Mouth (jagged)
        mouth_pts = [(ix - 8, iy + 6 - bounce), (ix - 4, iy + 9 - bounce),
                     (ix, iy + 6 - bounce), (ix + 4, iy + 9 - bounce),
                     (ix + 8, iy + 6 - bounce)]
        pygame.draw.lines(surf, BLACK, False, mouth_pts, 2)


# ═══════════════════════════════════════════════════════════════════
#  PLAYER CLASS
# ═══════════════════════════════════════════════════════════════════
class Player:
    def __init__(self, gx, gy):
        cx, cy = grid_to_px(gx, gy)
        self.x = float(cx)
        self.y = float(cy)
        self.bombs_max = 1       # max bombs out at once
        self.range = 2           # explosion range (cells in each dir)
        self.speed = PLAYER_BASE_SPEED
        self.invuln = 0
        self.move_dir = (0, 0)
        self.facing = (0, 1)
        self.anim_t = 0.0

    @property
    def gx(self):
        # Use rounding for cleaner snap-feel
        return int(round((self.x - TILE / 2) / TILE))

    @property
    def gy(self):
        return int(round((self.y - HUD_H - TILE / 2) / TILE))

    def update(self, keys, level):
        if self.invuln > 0:
            self.invuln -= 1

        # Determine intended direction (one axis at a time)
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1

        # Prefer horizontal if both pressed
        if dx and dy:
            dy = 0

        if dx or dy:
            self.facing = (dx, dy)
            self.anim_t += 0.2
        else:
            self.anim_t = 0

        # Try to move along the chosen axis with grid snapping on the other
        if dx != 0:
            new_x = self.x + dx * self.speed
            test_gy = int(round((self.y - HUD_H - TILE / 2) / TILE))
            test_gx = int((new_x + dx * (TILE / 2 - 4)) // TILE)
            # Smoothly align Y to grid
            target_y = test_gy * TILE + TILE / 2 + HUD_H
            if abs(self.y - target_y) > 1:
                self.y += (1 if target_y > self.y else -1) * min(self.speed, abs(target_y - self.y))
            else:
                self.y = target_y
            if 0 <= test_gx < GRID_W and level.passable_for_player(test_gx, test_gy, self):
                self.x = new_x
            else:
                # snap to current cell
                self.x = self.gx * TILE + TILE / 2
        elif dy != 0:
            new_y = self.y + dy * self.speed
            test_gx = int(round((self.x - TILE / 2) / TILE))
            test_gy = int((new_y - HUD_H + dy * (TILE / 2 - 4)) // TILE)
            target_x = test_gx * TILE + TILE / 2
            if abs(self.x - target_x) > 1:
                self.x += (1 if target_x > self.x else -1) * min(self.speed, abs(target_x - self.x))
            else:
                self.x = target_x
            if 0 <= test_gy < GRID_H and level.passable_for_player(test_gx, test_gy, self):
                self.y = new_y
            else:
                self.y = self.gy * TILE + TILE / 2 + HUD_H

        # Clamp
        self.x = max(TILE / 2, min(WIDTH - TILE / 2, self.x))
        self.y = max(HUD_H + TILE / 2, min(HEIGHT - TILE / 2, self.y))

    def draw(self, surf):
        # Flicker if invulnerable
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            return
        ix, iy = int(self.x), int(self.y)
        bounce = int(abs(math.sin(self.anim_t)) * 2)

        if PLAYER_SPRITE is not None:
            # Keep a subtle shadow for depth even with sprite rendering.
            pygame.draw.ellipse(surf, (0, 0, 0, 80), (ix - 16, iy + 14, 32, 6))
            sprite = PLAYER_SPRITE
            if self.facing[0] != 0:
                moving_right = self.facing[0] > 0
                should_flip = (moving_right != PLAYER_SPRITE_POINTS_RIGHT)
                if should_flip:
                    sprite = pygame.transform.flip(PLAYER_SPRITE, True, False)
            surf.blit(sprite, (ix - sprite.get_width() // 2, iy - sprite.get_height() // 2 - bounce))
            return

        # Body shadow
        pygame.draw.ellipse(surf, (0, 0, 0, 80), (ix - 16, iy + 14, 32, 6))
        # Body
        pygame.draw.circle(surf, PLAYER_DARK, (ix, iy + 2 - bounce), 17)
        pygame.draw.circle(surf, PLAYER_COL, (ix, iy - bounce), 16)
        # Helmet stripe
        pygame.draw.arc(surf, PLAYER_DARK, (ix - 14, iy - 18 - bounce, 28, 22), 0, math.pi, 4)
        # Visor / face area
        pygame.draw.rect(surf, BLACK, (ix - 8, iy - 5 - bounce, 16, 6), border_radius=2)
        # Eyes (white dots in visor)
        eye_off = self.facing[0] * 2
        pygame.draw.circle(surf, CYAN, (ix - 4 + eye_off, iy - 2 - bounce), 1)
        pygame.draw.circle(surf, CYAN, (ix + 4 + eye_off, iy - 2 - bounce), 1)


# ═══════════════════════════════════════════════════════════════════
#  LEVEL CLASS — holds the tile grid + math state
# ═══════════════════════════════════════════════════════════════════
class Level:
    def __init__(self, idx: int):
        """idx is 0-based level index."""
        self.idx = idx
        self.difficulty = idx + 1
        self.grid: List[List[int]] = []
        # Tracks "answer" tiles: dict (gx,gy) -> (value, is_correct)
        self.answer_tiles = {}
        self.bombs: List[Bomb] = []
        self.explosions: List[Explosion] = []
        self.powerups: List[PowerUp] = []
        self.enemies: List[Enemy] = []
        self.player_spawn = (1, 1)
        # Math problem state
        self.active_question = ""
        self.active_answer = 0
        self.has_active_problem = False
        self.problems_solved = 0
        self.target_solves = 2 + idx       # need to solve more in later levels
        self.build()

    # ── Build the level layout ──
    def build(self):
        # Create empty grid, surround with hard walls, add inner pillars
        self.grid = [[T_EMPTY for _ in range(GRID_W)] for _ in range(GRID_H)]
        for y in range(GRID_H):
            for x in range(GRID_W):
                if x == 0 or y == 0 or x == GRID_W - 1 or y == GRID_H - 1:
                    self.grid[y][x] = T_HARD
                # Classic Bomberman pattern: hard pillars on every other tile
                elif x % 2 == 0 and y % 2 == 0:
                    self.grid[y][x] = T_HARD

        # Player spawn: top-left corner area, kept clear (3 tiles)
        self.player_spawn = (1, 1)
        spawn_safe = {(1, 1), (2, 1), (1, 2)}

        # Soft block density scales with level
        soft_density = 0.55 + self.idx * 0.05
        for y in range(1, GRID_H - 1):
            for x in range(1, GRID_W - 1):
                if self.grid[y][x] == T_EMPTY and (x, y) not in spawn_safe:
                    if random.random() < soft_density:
                        self.grid[y][x] = T_SOFT

        # Single-level mode with fixed amount of question blocks.
        n_questions = 15
        soft_positions = [(x, y) for y in range(GRID_H) for x in range(GRID_W)
                          if self.grid[y][x] == T_SOFT]
        random.shuffle(soft_positions)
        for x, y in soft_positions[:n_questions]:
            self.grid[y][x] = T_QUESTION

        # Spawn more enemies and make them aggressive path-followers.
        n_enemies = 5 + self.idx * 2
        n_smart = n_enemies
        empty_positions = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.grid[y][x] != T_EMPTY:
                    continue
                if (x, y) in spawn_safe:
                    continue
                if abs(x - 1) + abs(y - 1) <= 6:
                    continue
                # Avoid trapped enemy spawns: require at least one open neighboring tile.
                open_neighbors = 0
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_W and 0 <= ny < GRID_H and self.grid[ny][nx] == T_EMPTY:
                        open_neighbors += 1
                if open_neighbors >= 1:
                    empty_positions.append((x, y))
        random.shuffle(empty_positions)
        for i in range(min(n_enemies, len(empty_positions))):
            pos = empty_positions[i]
            self.enemies.append(Enemy(*pos, smart=(i < n_smart)))

    def in_bounds(self, gx, gy):
        return 0 <= gx < GRID_W and 0 <= gy < GRID_H

    def tile_at(self, gx, gy):
        if not self.in_bounds(gx, gy):
            return T_HARD
        return self.grid[gy][gx]

    def has_bomb_at(self, gx, gy):
        return any(b.gx == gx and b.gy == gy for b in self.bombs)

    def projected_blast_cells(self, gx, gy, range_):
        """Compute blast cells without mutating the level state."""
        cells = [(gx, gy)]
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            for r in range(1, range_ + 1):
                nx, ny = gx + dx * r, gy + dy * r
                if not self.in_bounds(nx, ny):
                    break
                t = self.tile_at(nx, ny)
                if t == T_HARD:
                    break
                cells.append((nx, ny))
                if t in (T_SOFT, T_QUESTION, T_ANSWER):
                    break
        return cells

    def passable_for_player(self, gx, gy, player):
        t = self.tile_at(gx, gy)
        if t in (T_HARD, T_SOFT, T_QUESTION):
            return False
        if self.has_bomb_at(gx, gy):
            # Allow standing on the bomb you just placed
            cur_gx, cur_gy = player.gx, player.gy
            if (gx, gy) == (cur_gx, cur_gy):
                return True
            return False
        return True

    def passable_for_enemy(self, gx, gy):
        t = self.tile_at(gx, gy)
        if t in (T_HARD, T_SOFT, T_QUESTION, T_ANSWER):
            return False
        if self.has_bomb_at(gx, gy):
            return False
        return True

    # ── Place a bomb ──
    def place_bomb(self, gx, gy, range_):
        if self.tile_at(gx, gy) not in (T_EMPTY, T_ANSWER):
            return False
        if self.has_bomb_at(gx, gy):
            return False
        self.bombs.append(Bomb(gx, gy, range_))
        sfx(SFX_PLACE)
        return True

    # ── Detonate a bomb: returns (cells_affected, destroyed_question) ──
    def detonate(self, bomb: Bomb):
        cells = [(bomb.gx, bomb.gy)]
        destroyed_q = []     # list of (gx, gy) of question blocks destroyed
        chain = []           # other bombs to chain-detonate

        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            for r in range(1, bomb.range + 1):
                nx, ny = bomb.gx + dx * r, bomb.gy + dy * r
                if not self.in_bounds(nx, ny):
                    break
                t = self.tile_at(nx, ny)
                if t == T_HARD:
                    break
                cells.append((nx, ny))
                # Chain bombs
                for b in self.bombs:
                    if b is not bomb and b.gx == nx and b.gy == ny and not b.exploded:
                        chain.append(b)
                if t == T_SOFT:
                    self.grid[ny][nx] = T_EMPTY
                    emit(*grid_to_px(nx, ny), SOFT_BLOCK_HI, n=15, speed=4, life=24, size=4, gravity=0.2)
                    # Chance for power-up to drop
                    if random.random() < 0.18:
                        kind = random.choice([PowerUp.KIND_BOMB, PowerUp.KIND_RANGE,
                                              PowerUp.KIND_SPEED])
                        self.powerups.append(PowerUp(nx, ny, kind))
                    break
                elif t == T_QUESTION:
                    self.grid[ny][nx] = T_EMPTY
                    destroyed_q.append((nx, ny))
                    emit(*grid_to_px(nx, ny), QUESTION_HI, n=20, speed=5, life=30, size=4, gravity=0.2)
                    break
                elif t == T_ANSWER:
                    # Stop blast propagation through answer tiles.
                    break

        # Also chain other bombs
        for b in chain:
            if not b.exploded:
                b.timer = 1  # detonate next frame

        return cells, destroyed_q

    # ── Drawing ──
    def draw(self, surf):
        # Background grass pattern
        for y in range(GRID_H):
            for x in range(GRID_W):
                px = x * TILE
                py = y * TILE + HUD_H
                col = BG_COLOR if (x + y) % 2 == 0 else BG_ALT
                pygame.draw.rect(surf, col, (px, py, TILE, TILE))

        # Tiles
        for y in range(GRID_H):
            for x in range(GRID_W):
                t = self.grid[y][x]
                if t == T_EMPTY:
                    continue
                px = x * TILE
                py = y * TILE + HUD_H
                if t == T_HARD:
                    self._draw_hard(surf, px, py)
                elif t == T_SOFT:
                    self._draw_soft(surf, px, py)
                elif t == T_QUESTION:
                    self._draw_question(surf, px, py)
                elif t == T_ANSWER:
                    val, is_correct = self.answer_tiles.get((x, y), (0, False))
                    self._draw_answer(surf, px, py, val)

    def _draw_hard(self, surf, px, py):
        pygame.draw.rect(surf, HARD_WALL_LO, (px, py, TILE, TILE))
        pygame.draw.rect(surf, HARD_WALL, (px + 2, py + 2, TILE - 4, TILE - 4))
        pygame.draw.rect(surf, HARD_WALL_HI, (px + 4, py + 4, TILE - 12, 4))
        pygame.draw.rect(surf, HARD_WALL_HI, (px + 4, py + 4, 4, TILE - 12))

    def _draw_soft(self, surf, px, py):
        pygame.draw.rect(surf, SOFT_BLOCK_LO, (px + 2, py + 2, TILE - 4, TILE - 4))
        pygame.draw.rect(surf, SOFT_BLOCK, (px + 4, py + 4, TILE - 8, TILE - 8))
        pygame.draw.rect(surf, SOFT_BLOCK_HI, (px + 4, py + 4, TILE - 8, 4))
        # Brick lines
        pygame.draw.line(surf, SOFT_BLOCK_LO, (px + 4, py + TILE // 2),
                         (px + TILE - 4, py + TILE // 2), 1)
        pygame.draw.line(surf, SOFT_BLOCK_LO, (px + TILE // 2, py + 4),
                         (px + TILE // 2, py + TILE // 2), 1)
        pygame.draw.line(surf, SOFT_BLOCK_LO, (px + TILE // 3, py + TILE // 2),
                         (px + TILE // 3, py + TILE - 4), 1)

    def _draw_question(self, surf, px, py):
        pygame.draw.rect(surf, GREY_DARK, (px + 2, py + 2, TILE - 4, TILE - 4))
        pygame.draw.rect(surf, QUESTION_BLK, (px + 4, py + 4, TILE - 8, TILE - 8))
        pygame.draw.rect(surf, QUESTION_HI, (px + 4, py + 4, TILE - 8, 4))
        # ? mark
        q = FONT_TILE.render("?", True, WHITE)
        surf.blit(q, (px + TILE // 2 - q.get_width() // 2,
                      py + TILE // 2 - q.get_height() // 2))

    def _draw_answer(self, surf, px, py, val):
        pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.005)
        # Glow halo around the tile
        glow = pygame.Surface((TILE + 16, TILE + 16), pygame.SRCALPHA)
        pygame.draw.rect(glow, (180, 160, 255, int(80 * pulse)),
                         (0, 0, TILE + 16, TILE + 16), border_radius=12)
        surf.blit(glow, (px - 8, py - 8))
        pygame.draw.rect(surf, ANSWER_BG, (px + 2, py + 2, TILE - 4, TILE - 4), border_radius=6)
        pygame.draw.rect(surf, ANSWER_BORDER, (px + 2, py + 2, TILE - 4, TILE - 4), 3, border_radius=6)
        # Number
        nt = FONT_TILE.render(str(val), True, WHITE)
        surf.blit(nt, (px + TILE // 2 - nt.get_width() // 2,
                       py + TILE // 2 - nt.get_height() // 2))


# ═══════════════════════════════════════════════════════════════════
#  MATH PROBLEM GENERATOR
# ═══════════════════════════════════════════════════════════════════
def gen_problem(difficulty: int):
    types = {
        1: ['add', 'sub', 'mul', 'fib'],
        2: ['add', 'sub', 'mul', 'div', 'fib'],
        3: ['mul', 'div', 'algebra', 'add', 'fib'],
        4: ['algebra', 'mul', 'div', 'percent', 'fib'],
        5: ['algebra', 'percent', 'mul', 'algebra', 'fib'],
    }
    kind = random.choice(types.get(difficulty, types[5]))
    if kind == 'add':
        a = random.randint(8 * difficulty, 30 * difficulty)
        b = random.randint(8 * difficulty, 30 * difficulty)
        return f"{a} + {b}", a + b
    elif kind == 'sub':
        a = random.randint(15 * difficulty, 50 * difficulty)
        b = random.randint(3, a - 1)
        return f"{a} - {b}", a - b
    elif kind == 'mul':
        a = random.randint(2, 4 + difficulty * 2)
        b = random.randint(2, 4 + difficulty * 2)
        return f"{a} x {b}", a * b
    elif kind == 'div':
        divisor = random.randint(2, 3 + difficulty)
        answer = random.randint(2, 5 + difficulty * 2)
        return f"{divisor * answer} / {divisor}", answer
    elif kind == 'algebra':
        coeff = random.randint(2, 2 + difficulty)
        x_val = random.randint(1, 4 + difficulty)
        const = random.randint(1, 8 + difficulty * 2)
        return f"Solve: {coeff}x + {const} = {coeff * x_val + const}", x_val
    elif kind == 'percent':
        pct = random.choice([10, 20, 25, 50, 75])
        base = random.choice([40, 60, 80, 100, 200])
        return f"{pct}% of {base}", int(base * pct / 100)
    elif kind == 'fib':
        seq_len = random.randint(4 + difficulty, 6 + difficulty)
        seq = [1, 1]
        while len(seq) < seq_len:
            seq.append(seq[-1] + seq[-2])
        shown = ", ".join(str(v) for v in seq[-4:])
        return f"Next in Fibonacci: {shown}, ?", seq[-1] + seq[-2]
    a, b = random.randint(5, 20), random.randint(5, 20)
    return f"{a} + {b}", a + b


def gen_wrong(correct, n=3, spread=8):
    wrong = set()
    att = 0
    while len(wrong) < n and att < 200:
        att += 1
        off = random.randint(1, spread)
        if random.random() < 0.5:
            off = -off
        v = correct + off
        if v != correct and v >= 0 and v not in wrong:
            wrong.add(v)
    while len(wrong) < n:
        wrong.add(correct + len(wrong) + 1)
    return list(wrong)[:n]


# ═══════════════════════════════════════════════════════════════════
#  LEADERBOARD PANEL DRAWER
# ═══════════════════════════════════════════════════════════════════
def draw_lb_panel(surf, board, cx, top_y, title="TOP 10 SCORES",
                  hl_name=None, hl_score=None, pw=380, rh=22):
    n = len(board)
    hdr_h = 36
    col_hdr_h = 18
    body_h = max(rh * max(n, 1) + col_hdr_h + 12, 50)
    total_h = hdr_h + body_h
    px = cx - pw // 2
    py = top_y
    pygame.draw.rect(surf, PANEL_BG, (px, py, pw, total_h), border_radius=8)
    pygame.draw.rect(surf, PANEL_BORDER, (px, py, pw, total_h), 2, border_radius=8)
    pygame.draw.rect(surf, GREY_DARK, (px + 2, py + 2, pw - 4, hdr_h - 2), border_radius=6)
    ht = FONT_LB_HDR.render(title, True, GOLD)
    surf.blit(ht, (cx - ht.get_width() // 2, py + hdr_h // 2 - ht.get_height() // 2))
    ry = py + hdr_h + 4
    if n == 0:
        et = FONT_LB.render("No times yet!", True, GREY)
        surf.blit(et, (cx - et.get_width() // 2, ry + 10))
        return
    for text, xoff in [("#", 14), ("NAME", 50), ("TIME", pw - 110)]:
        ct = FONT_XS.render(text, True, GREY)
        surf.blit(ct, (px + xoff, ry))
    ry += col_hdr_h
    rank_colors = [GOLD, (200, 200, 210), ORANGE]
    for i, entry in enumerate(board):
        name = entry.get("name", "???")
        score = float(entry.get("time", 0.0))
        is_dnf = bool(entry.get("dnf", False))
        is_hl = (hl_name and hl_score is not None
                 and name == hl_name and score == hl_score)
        if is_hl:
            pygame.draw.rect(surf, (50, 40, 80),
                             (px + 4, ry - 1, pw - 8, rh), border_radius=3)
        rc = rank_colors[i] if i < 3 else GREY
        nc = WHITE if is_hl else (200, 200, 210)
        sc_c = GOLD if is_hl else (180, 180, 190)
        for text, col, xoff in [(f"{i+1}.", rc, 14), (name[:12], nc, 50)]:
            rt = FONT_LB.render(text, True, col)
            surf.blit(rt, (px + xoff, ry))
        score_text = "DNF" if is_dnf else format_time(score)
        st = FONT_LB.render(score_text, True, sc_c)
        surf.blit(st, (px + pw - 16 - st.get_width(), ry))
        ry += rh


# ═══════════════════════════════════════════════════════════════════
#  GAME CLASS — full state machine
# ═══════════════════════════════════════════════════════════════════
class Game:
    TITLE      = 0
    INTRO      = 1
    PLAYING    = 2
    LEVEL_DONE = 3
    OVER       = 4
    WIN        = 5
    NAME_ENTRY = 6
    LB_SCREEN  = 7
    TUTORIAL   = 8

    NUM_LEVELS = 1

    def __init__(self):
        self.state = self.TITLE
        self.score = 0
        self.lives = 3
        self.lvl_idx = 0
        self.level: Optional[Level] = None
        self.player: Optional[Player] = None
        self.frame = 0
        self.intro_t = 0
        self.done_t = 0
        self.show_timer = 0
        # Math problem state
        self.problem_active = False
        self.problem_text = ""
        self.problem_answer = 0
        self.hidden_questions: List[Tuple[int, int]] = []
        # Flash messages
        self.flash_txt = ""
        self.flash_col = WHITE
        self.flash_t = 0
        # Name entry / leaderboard
        self.name_input = ""
        self.name_max = 12
        self.final_score = 0
        self.level_start_ticks = 0
        self.elapsed_ms = 0
        self.time_penalty_ms = 0
        self.final_time = 0.0
        self.final_dnf = False
        self.came_from_win = False
        self.lb_board: list = []
        self.lb_is_high = False
        self.title_lb = load_leaderboard()
        g_parts.clear()

    def full_reset(self):
        self.__init__()

    def start_level(self):
        self.level = Level(self.lvl_idx)
        self.player = Player(*self.level.player_spawn)
        self.problem_active = False
        self.hidden_questions = []
        self.level_start_ticks = pygame.time.get_ticks()
        self.elapsed_ms = 0
        self.time_penalty_ms = 0
        self.final_dnf = False
        self.state = self.INTRO
        self.intro_t = 140
        g_parts.clear()

    def flash(self, txt, col, dur=80):
        self.flash_txt = txt
        self.flash_col = col
        self.flash_t = dur

    # ── Spawn the math answer-tiles around the player after destroying ?-block ──
    def _spawn_answer_tiles(self, source_gx, source_gy):
        """Find 4 empty cells near source_gx/gy and turn them into answer tiles."""
        q, a = gen_problem(self.level.difficulty)
        self.problem_text = q + " = ?"
        self.problem_answer = a
        wrongs = gen_wrong(a, 3, 4 + self.level.difficulty * 2)
        # Build pool of nearby empty tiles in increasing radius
        candidates = []
        for radius in range(2, 9):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if abs(dx) + abs(dy) > radius:
                        continue
                    nx, ny = source_gx + dx, source_gy + dy
                    if not self.level.in_bounds(nx, ny):
                        continue
                    if self.level.tile_at(nx, ny) != T_EMPTY:
                        continue
                    # Don't replace the player's current tile
                    if (nx, ny) == (self.player.gx, self.player.gy):
                        continue
                    if self.level.has_bomb_at(nx, ny):
                        continue
                    if (nx, ny) not in candidates:
                        candidates.append((nx, ny))
            if len(candidates) >= 8:
                break
        if len(candidates) < 4:
            # Not enough room — bail out
            self.flash("Not enough space!", ORANGE, 60)
            return False
        random.shuffle(candidates)
        chosen = candidates[:4]
        # Randomly pick which slot is the correct one
        ci = random.randint(0, 3)
        values = []
        for i in range(4):
            if i == ci:
                values.append((a, True))
            else:
                values.append((wrongs.pop(0), False))
        # Set tiles
        self.level.answer_tiles.clear()
        for (gx, gy), (val, is_corr) in zip(chosen, values):
            self.level.grid[gy][gx] = T_ANSWER
            self.level.answer_tiles[(gx, gy)] = (val, is_corr)
            # Sparkle
            cx, cy = grid_to_px(gx, gy)
            emit(cx, cy, ANSWER_BORDER, n=12, speed=3, life=25, size=3, gravity=0)

        # Temporarily hide all other question boxes so only one question can be active.
        self.hidden_questions = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.level.grid[y][x] == T_QUESTION:
                    self.hidden_questions.append((x, y))
                    self.level.grid[y][x] = T_EMPTY

        self.problem_active = True
        return True

    # ── Resolve a math problem when an answer tile is hit ──
    def _resolve_answer(self, gx, gy):
        if (gx, gy) not in self.level.answer_tiles:
            return
        val, is_correct = self.level.answer_tiles[(gx, gy)]
        cx, cy = grid_to_px(gx, gy)
        if is_correct:
            self.score += 200
            self.level.problems_solved += 1
            self.flash(f"+200  CORRECT!", GREEN, 70)
            emit_text(cx, cy - 30, "CORRECT!", GREEN)
            sfx(SFX_OK)
            # Spawn power-up at the answer location
            kind = random.choice([PowerUp.KIND_BOMB, PowerUp.KIND_RANGE, PowerUp.KIND_SPEED])
            self.level.powerups.append(PowerUp(gx, gy, kind))
            emit(cx, cy, GOLD, n=24, speed=5, life=30, size=4, gravity=0.05)
        else:
            self.score = max(0, self.score - 30)
            self.flash(f"-30  WRONG!", RED, 70)
            emit_text(cx, cy - 30, "WRONG", RED)
            sfx(SFX_BAD)
            emit(cx, cy, RED, n=15, speed=4, life=22, gravity=0.05)
            # Penalty: spawn a new enemy at a random empty tile
            self._spawn_penalty_enemy()
        # Clear ALL answer tiles (problem ends)
        for (ax, ay) in list(self.level.answer_tiles.keys()):
            if self.level.tile_at(ax, ay) == T_ANSWER:
                self.level.grid[ay][ax] = T_EMPTY
        self.level.answer_tiles.clear()

        # Bring back hidden question boxes after the current question is resolved.
        for qx, qy in self.hidden_questions:
            if self.level.tile_at(qx, qy) == T_EMPTY and not self.level.has_bomb_at(qx, qy):
                self.level.grid[qy][qx] = T_QUESTION
        self.hidden_questions = []

        self.problem_active = False

    def _spawn_penalty_enemy(self):
        empty = []
        for y in range(GRID_H):
            for x in range(GRID_W):
                if self.level.tile_at(x, y) != T_EMPTY:
                    continue
                if abs(x - self.player.gx) + abs(y - self.player.gy) <= 4:
                    continue
                # Spawn only where enemy can move immediately.
                open_neighbors = 0
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if self.level.in_bounds(nx, ny) and self.level.tile_at(nx, ny) == T_EMPTY:
                        open_neighbors += 1
                if open_neighbors >= 1:
                    empty.append((x, y))
        if not empty:
            return
        gx, gy = random.choice(empty)
        self.level.enemies.append(Enemy(gx, gy, smart=False))
        cx, cy = grid_to_px(gx, gy)
        emit(cx, cy, RED, n=10, speed=3, life=20, gravity=0.05)

    # ── Apply power-up effect ──
    def _apply_powerup(self, pu: PowerUp):
        if pu.kind == PowerUp.KIND_BOMB:
            self.player.bombs_max += 1
            self.flash("BOMB CAPACITY +1", PU_BOMB, 70)
        elif pu.kind == PowerUp.KIND_RANGE:
            self.player.range += 1
            self.flash("BLAST RANGE +1", PU_RANGE, 70)
        elif pu.kind == PowerUp.KIND_SPEED:
            self.player.speed = min(self.player.speed + 0.5, 5.5)
            self.flash("SPEED +0.5", PU_SPEED, 70)
        sfx(SFX_PU)
        self.score += 50

    # ── Damage the player ──
    def _hurt_player(self):
        if self.player.invuln > 0:
            return
        self.lives -= 1
        self.time_penalty_ms += 5000
        self.player.invuln = INVULN_FRAMES
        sfx(SFX_HURT)
        emit(self.player.x, self.player.y, RED, n=18, speed=4, life=22, gravity=0.1)
        self.flash("OUCH!", RED, 50)
        if self.lives <= 0:
            self.state = self.OVER
            self.show_timer = 180

    def _go_name_entry(self, from_win):
        self.state = self.NAME_ENTRY
        self.final_score = self.score
        self.final_time = self.elapsed_ms / 1000.0
        self.final_dnf = not from_win
        self.came_from_win = from_win
        self.name_input = ""

    def _submit_name(self):
        name = self.name_input.strip() or "ANON"
        self.lb_board, self.lb_is_high = add_to_leaderboard(name, self.final_time, self.final_dnf)
        self.state = self.LB_SCREEN

    # ─── UPDATE ──────────────────────────────────────────────
    def update(self):
        self.frame += 1

        if self.state == self.INTRO:
            self.intro_t -= 1
            if self.intro_t <= 0:
                self.state = self.PLAYING
            return

        if self.state == self.LEVEL_DONE:
            self.done_t -= 1
            if self.frame % 4 == 0:
                emit(random.randint(200, WIDTH - 200), random.randint(150, 350),
                     random.choice([GOLD, GREEN, CYAN, PINK]),
                     n=4, speed=3, life=30, size=4, gravity=0.05)
            self._tick_p()
            if self.done_t <= 0:
                self.lvl_idx += 1
                if self.lvl_idx >= self.NUM_LEVELS:
                    self.state = self.WIN
                    self.show_timer = 200
                else:
                    self.start_level()
            return

        if self.state == self.OVER:
            self.show_timer -= 1
            self._tick_p()
            if self.show_timer <= 0:
                self._go_name_entry(False)
            return

        if self.state == self.WIN:
            self.show_timer -= 1
            if self.frame % 3 == 0:
                emit(random.randint(150, WIDTH - 150), random.randint(100, 350),
                     random.choice([GOLD, GREEN, CYAN, PINK, ORANGE]),
                     n=3, speed=3, life=35, size=4, gravity=0.05)
            self._tick_p()
            if self.show_timer <= 0:
                self._go_name_entry(True)
            return

        if self.state in (self.TITLE, self.TUTORIAL, self.NAME_ENTRY, self.LB_SCREEN):
            self._tick_p()
            return

        if self.state != self.PLAYING:
            return

        # ── PLAYING ──
        self.elapsed_ms = pygame.time.get_ticks() - self.level_start_ticks + self.time_penalty_ms
        keys = pygame.key.get_pressed()
        self.player.update(keys, self.level)

        # Update bombs
        for b in self.level.bombs:
            b.update()

        # Detonate any expired bombs
        new_explosions = []
        bombs_to_remove = []
        for b in self.level.bombs:
            if b.exploded:
                cells, _destroyed_q = self.level.detonate(b)
                new_explosions.append(Explosion(cells))
                bombs_to_remove.append(b)
                sfx(SFX_BOMB)
                # Big visual particles
                cx, cy = grid_to_px(b.gx, b.gy)
                emit(cx, cy, EXPLOSION_O, n=22, speed=6, life=22, size=4, gravity=0.05)
                # Direct-hit answers only: place bomb on the target answer tile.
                if (b.gx, b.gy) in self.level.answer_tiles:
                    self._resolve_answer(b.gx, b.gy)
                # Re-check destroyed question blocks: since detonate already removed them,
                # we use the destroyed_q list it returned
                for (qx, qy) in _destroyed_q:
                    self.score += 30
                    if not self.problem_active:
                        # Spawn the math problem
                        if self._spawn_answer_tiles(qx, qy):
                            sfx(SFX_PU)
                # Score for soft block destruction (count empty cells that were soft)
                # We approximated: detonate already cleared them and emitted particles
        for b in bombs_to_remove:
            if b in self.level.bombs:
                self.level.bombs.remove(b)
        self.level.explosions.extend(new_explosions)

        # Update explosions
        for e in self.level.explosions:
            e.update()
        self.level.explosions = [e for e in self.level.explosions if e.alive]

        # Check explosion damage on player & enemies
        all_explosion_cells = set()
        for e in self.level.explosions:
            for c in e.cells:
                all_explosion_cells.add(c)

        # Danger map for AI: active flames + near-future bomb blast zones.
        danger_cells = set(all_explosion_cells)
        for b in self.level.bombs:
            if b.timer <= 40:
                danger_cells.update(self.level.projected_blast_cells(b.gx, b.gy, b.range))

        if (self.player.gx, self.player.gy) in all_explosion_cells:
            self._hurt_player()
            if self.state == self.OVER:
                return
        for en in self.level.enemies:
            if en.alive and (en.gx, en.gy) in all_explosion_cells:
                en.alive = False
                self.score += 100
                emit(en.x, en.y, ENEMY_DARK, n=18, speed=5, life=25, gravity=0.1)
                emit_text(en.x, en.y - 20, "+100", GOLD)
                sfx(SFX_OK)
        self.level.enemies = [e for e in self.level.enemies if e.alive]

        # Update enemies
        for en in self.level.enemies:
            en.update(self.level, self.player, danger_cells)
            if en.hits_player(self.player):
                self._hurt_player()
                if self.state == self.OVER:
                    return

        # Update power-ups
        for pu in self.level.powerups:
            pu.update()
            if pu.alive and pu.gx == self.player.gx and pu.gy == self.player.gy:
                pu.alive = False
                self._apply_powerup(pu)
        self.level.powerups = [p for p in self.level.powerups if p.alive]

        # Check level completion: all question blocks destroyed AND no enemies
        no_questions = not any(self.level.tile_at(x, y) == T_QUESTION
                                for y in range(GRID_H) for x in range(GRID_W))
        no_enemies = len(self.level.enemies) == 0
        if no_questions and no_enemies and not self.problem_active:
            self.state = self.LEVEL_DONE
            self.done_t = 150
            bonus = 200 * (self.lvl_idx + 1)
            self.score += bonus
            self.flash(f"Level Bonus +{bonus}", GOLD, 100)
            sfx(SFX_LVL)

        self._tick_p()
        if self.flash_t > 0:
            self.flash_t -= 1

    def _tick_p(self):
        for p in g_parts:
            p.update()
        g_parts[:] = [p for p in g_parts if p.life > 0]

    # ─── EVENTS ──────────────────────────────────────────────
    def handle(self, ev) -> bool:
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.state in (self.LB_SCREEN, self.NAME_ENTRY):
                self.full_reset()
                return True
            return False

        if self.state == self.TITLE:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.state = self.TUTORIAL
            return True

        if self.state == self.TUTORIAL:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.score = 0
                self.lives = 3
                self.lvl_idx = 0
                self.start_level()
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_BACKSPACE:
                self.state = self.TITLE
            return True

        if self.state == self.NAME_ENTRY:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    self._submit_name()
                    sfx(SFX_LVL)
                elif ev.key == pygame.K_BACKSPACE:
                    self.name_input = self.name_input[:-1]
                    sfx(SFX_TYPE)
                else:
                    ch = ev.unicode
                    if ch and ch.isprintable() and len(self.name_input) < self.name_max:
                        self.name_input += ch
                        sfx(SFX_TYPE)
            return True

        if self.state == self.LB_SCREEN:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.full_reset()
            return True

        if self.state in (self.OVER, self.WIN):
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.show_timer = 0
            return True

        if self.state == self.PLAYING:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_SPACE:
                    self._try_place_bomb()
                elif ev.key == pygame.K_r:
                    self.start_level()
        return True

    def _try_place_bomb(self):
        active_bombs = len(self.level.bombs)
        if active_bombs >= self.player.bombs_max:
            return
        gx, gy = self.player.gx, self.player.gy
        self.level.place_bomb(gx, gy, self.player.range)

    # ─── DRAW ────────────────────────────────────────────────
    def draw(self):
        screen.fill(HUD_BG)
        if self.state == self.TITLE:
            self._d_title()
        elif self.state == self.TUTORIAL:
            self._d_tutorial()
        elif self.state == self.INTRO:
            self._d_intro()
        elif self.state == self.PLAYING:
            self._d_game()
        elif self.state == self.LEVEL_DONE:
            self._d_lvl_done()
        elif self.state == self.OVER:
            self._d_over()
        elif self.state == self.WIN:
            self._d_win()
        elif self.state == self.NAME_ENTRY:
            self._d_name()
        elif self.state == self.LB_SCREEN:
            self._d_lb()
        pygame.display.flip()

    # ── TITLE ──
    def _d_title(self):
        # Bg color stripes for some retro feel
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            r = int(15 + t * 25)
            g = int(12 + t * 15)
            b = int(28 + t * 35)
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))
        txt_sh(screen, "MATH BOMBERMAN", FONT_XL, GOLD, 60)

        # Decorative bomb
        cx, cy = WIDTH // 2, 130
        pygame.draw.circle(screen, (40, 40, 40), (cx, cy + 2), 28)
        pygame.draw.circle(screen, (60, 60, 60), (cx, cy), 24)
        pygame.draw.circle(screen, BOMB_HIGHLIGHT, (cx - 8, cy - 8), 6)
        pygame.draw.line(screen, BROWN := (160, 100, 50), (cx, cy - 24), (cx + 8, cy - 36), 3)
        pygame.draw.circle(screen, FUSE_COL, (cx + 8, cy - 38), 4)
        pygame.draw.circle(screen, (255, 255, 200), (cx + 8, cy - 38), 2)

        pulse = int(200 + 55 * math.sin(self.frame * 0.06))
        txt_c(screen, "Press SPACE to Start", FONT_SM,
              (pulse, pulse, min(255, pulse + 20)), 185)
        txt_c(screen, "Arrows/WASD: Move | SPACE: Bomb", FONT_XS, GREY, 210)

        draw_lb_panel(screen, self.title_lb, WIDTH // 2, 240,
                      title="TOP 10 BEST TIMES", pw=420, rh=22)

    # ── TUTORIAL ──
    def _d_tutorial(self):
        for y in range(0, HEIGHT, 4):
            t = y / HEIGHT
            r = int(13 + t * 20)
            g = int(12 + t * 13)
            b = int(24 + t * 28)
            pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

        txt_sh(screen, "HOW TO PLAY", FONT_LG, GOLD, 40)

        panel = pygame.Rect(100, 90, WIDTH - 200, HEIGHT - 170)
        pygame.draw.rect(screen, PANEL_BG, panel, border_radius=10)
        pygame.draw.rect(screen, PANEL_BORDER, panel, 2, border_radius=10)

        y = 120
        txt_sh(screen, "Core Goal", FONT_MD, CYAN, y)
        y += 34
        txt_c(screen, "Destroy ? blocks, solve math answers, and clear enemies.", FONT_SM, WHITE, y)

        y += 40
        txt_sh(screen, "Enemy AI", FONT_MD, ORANGE, y)
        y += 34
        txt_c(screen, "Smart bots actively chase you and path around walls.", FONT_SM, WHITE, y)
        y += 26
        txt_c(screen, "They only run away when a bomb blast is about to hit.", FONT_SM, WHITE, y)

        y += 42
        txt_sh(screen, "Power-Ups", FONT_MD, GREEN, y)
        y += 34
        txt_c(screen, "B+  = Extra bomb capacity (more bombs placed at once)", FONT_SM, WHITE, y)
        y += 26
        txt_c(screen, "R+  = Bigger blast range", FONT_SM, WHITE, y)
        y += 26
        txt_c(screen, "S+  = Faster movement speed", FONT_SM, WHITE, y)

        y += 42
        txt_sh(screen, "Controls", FONT_MD, GOLD, y)
        y += 34
        txt_c(screen, "Move: Arrow Keys / WASD   |   Bomb: SPACE", FONT_SM, WHITE, y)
        y += 26
        txt_c(screen, "Restart level: R   |   Return launcher: 0   |   Quit: ESC", FONT_SM, WHITE, y)

        pulse = int(185 + 60 * math.sin(self.frame * 0.06))
        txt_c(screen, "Press SPACE to begin", FONT_MD, (pulse, pulse, min(255, pulse + 25)), HEIGHT - 46)

    # ── LEVEL INTRO ──
    def _d_intro(self):
        txt_sh(screen, f"LEVEL {self.lvl_idx + 1}", FONT_LG, GOLD, 220)
        names = ["Time Trial Arena"]
        nm = names[min(self.lvl_idx, len(names) - 1)]
        txt_sh(screen, nm, FONT_MD, WHITE, 270)
        d = self.lvl_idx + 1
        stars = "* " * d + ". " * (self.NUM_LEVELS - d)
        txt_c(screen, f"Difficulty: {stars.strip()}", FONT_SM, ORANGE, 315)
        txt_c(screen, "Destroy all 15 ? blocks and clear enemies as fast as you can!", FONT_SM, GREY, 345)
        frac = 1.0 - self.intro_t / 140
        bw = 220
        bx = WIDTH // 2 - bw // 2
        pygame.draw.rect(screen, GREY_DIM, (bx, 400, bw, 8), border_radius=4)
        pygame.draw.rect(screen, GOLD, (bx, 400, int(bw * frac), 8), border_radius=4)

    # ── GAMEPLAY ──
    def _d_game(self):
        self._d_hud()
        self.level.draw(screen)

        # Show hidden question boxes as translucent hints while one question is active.
        if self.problem_active and self.hidden_questions:
            ghost = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
            pygame.draw.rect(ghost, (80, 130, 220, 95), (4, 4, TILE - 8, TILE - 8), border_radius=6)
            pygame.draw.rect(ghost, (130, 170, 255, 130), (4, 4, TILE - 8, TILE - 8), 2, border_radius=6)
            q = FONT_TILE.render("?", True, (255, 255, 255))
            q.set_alpha(165)
            for gx, gy in self.hidden_questions:
                px = gx * TILE
                py = gy * TILE + HUD_H
                screen.blit(ghost, (px, py))
                screen.blit(q, (px + TILE // 2 - q.get_width() // 2,
                                py + TILE // 2 - q.get_height() // 2))

        # Power-ups drawn under bombs/explosions
        for pu in self.level.powerups:
            pu.draw(screen)
        # Bombs
        for b in self.level.bombs:
            b.draw(screen)
        # Player
        self.player.draw(screen)
        # Enemies
        for en in self.level.enemies:
            en.draw(screen)
        # Explosions on top
        for e in self.level.explosions:
            e.draw(screen)
        # Particles
        for p in g_parts:
            p.draw(screen)
        # Flash
        if self.flash_t > 0:
            af = min(1.0, self.flash_t / 25)
            c = tuple(int(ch * af) for ch in self.flash_col)
            txt_sh(screen, self.flash_txt, FONT_MD, c, HUD_H + 35)

    def _d_hud(self):
        # HUD background bar
        pygame.draw.rect(screen, HUD_BG, (0, 0, WIDTH, HUD_H))
        pygame.draw.line(screen, PANEL_BORDER, (0, HUD_H), (WIDTH, HUD_H), 2)

        # Left: score + level + timer
        st = FONT_HUD.render(f"Score: {self.score}", True, WHITE)
        screen.blit(st, (12, 8))
        lt = FONT_XS.render(f"Lvl {self.lvl_idx + 1}/{self.NUM_LEVELS}", True, GREY)
        screen.blit(lt, (12, 30))
        tt = FONT_XS.render(f"Time: {format_time(self.elapsed_ms / 1000.0)}", True, GOLD)
        screen.blit(tt, (12, 46))

        # Center: math problem (when active) or "Find ? blocks"
        if self.problem_active:
            mt = FONT_MD.render(self.problem_text, True, GOLD)
            screen.blit(mt, (WIDTH // 2 - mt.get_width() // 2, 8))
            ht = FONT_XS.render("Place bomb directly on the correct answer!", True, CYAN)
            screen.blit(ht, (WIDTH // 2 - ht.get_width() // 2, 36))
        else:
            mt = FONT_SM.render("Bomb ? blocks to trigger problems", True, GREY)
            screen.blit(mt, (WIDTH // 2 - mt.get_width() // 2, 8))
            # Stats: bombs / range / speed
            stats = (f"Bombs: {self.player.bombs_max}   "
                     f"Range: {self.player.range}   "
                     f"Speed: {self.player.speed:.1f}")
            ss = FONT_XS.render(stats, True, (180, 180, 200))
            screen.blit(ss, (WIDTH // 2 - ss.get_width() // 2, 36))

        # Right: hearts
        for i in range(3):
            hx = WIDTH - 130 + i * 24
            hy = 18
            c = RED if i < self.lives else GREY_DIM
            pygame.draw.circle(screen, c, (hx - 4, hy), 6)
            pygame.draw.circle(screen, c, (hx + 4, hy), 6)
            pygame.draw.polygon(screen, c, [(hx - 10, hy + 2), (hx, hy + 14), (hx + 10, hy + 2)])
        # Bomb counter
        avail = self.player.bombs_max - len(self.level.bombs)
        bt = FONT_HUD.render(f"BOMBS {avail}/{self.player.bombs_max}", True, WHITE)
        screen.blit(bt, (WIDTH - 130, 38))

    # ── LEVEL DONE ──
    def _d_lvl_done(self):
        txt_sh(screen, "LEVEL CLEARED!", FONT_LG, GREEN, 220)
        bonus = 200 * (self.lvl_idx + 1)
        txt_sh(screen, f"Bonus: +{bonus}", FONT_MD, GOLD, 280)
        txt_sh(screen, f"Time: {format_time(self.elapsed_ms / 1000.0)}", FONT_MD, WHITE, 320)
        for i in range(self.lives):
            self._draw_heart_big(WIDTH // 2 - self.lives * 18 + i * 36 + 18, 380, 12)
        for p in g_parts:
            p.draw(screen)

    def _draw_heart_big(self, hx, hy, r):
        pygame.draw.circle(screen, RED, (hx - r // 2, hy), r // 2 + 1)
        pygame.draw.circle(screen, RED, (hx + r // 2, hy), r // 2 + 1)
        pygame.draw.polygon(screen, RED, [(hx - r, hy + 2), (hx, hy + r + 4), (hx + r, hy + 2)])

    # ── GAME OVER ──
    def _d_over(self):
        txt_sh(screen, "GAME OVER", FONT_LG, RED, 220)
        txt_sh(screen, f"Survival Time: {format_time(self.elapsed_ms / 1000.0)}", FONT_MD, WHITE, 290)
        txt_c(screen, "Try again for a faster clear!", FONT_SM, GREY, 335)
        secs = max(1, self.show_timer // 60 + 1)
        txt_c(screen, f"Name entry in {secs}s... (or press SPACE)", FONT_XS, GREY_DIM, 380)

    # ── WIN ──
    def _d_win(self):
        txt_sh(screen, "VICTORY!", FONT_XL, GOLD, 180)
        txt_sh(screen, f"Clear Time: {format_time(self.elapsed_ms / 1000.0)}", FONT_LG, WHITE, 270)
        txt_sh(screen, "Math Bomberman Time Trial Complete!", FONT_MD, GREEN, 340)
        secs = max(1, self.show_timer // 60 + 1)
        txt_c(screen, f"Name entry in {secs}s... (or press SPACE)", FONT_XS, GREY_DIM, 410)
        for p in g_parts:
            p.draw(screen)

    # ── NAME ENTRY ──
    def _d_name(self):
        if self.came_from_win:
            txt_sh(screen, "CONGRATULATIONS!", FONT_LG, GOLD, 110)
        else:
            txt_sh(screen, "GAME OVER", FONT_LG, RED, 110)
        if self.final_dnf:
            txt_sh(screen, "Result: DNF", FONT_MD, RED, 165)
        else:
            txt_sh(screen, f"Time: {format_time(self.final_time)}", FONT_MD, WHITE, 165)
        txt_sh(screen, "Enter Your Name:", FONT_MD, CYAN, 230)
        bw, bh = 340, 50
        bx = WIDTH // 2 - bw // 2
        by = 260
        pygame.draw.rect(screen, INPUT_BG, (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(screen, PANEL_BORDER, (bx, by, bw, bh), 2, border_radius=8)
        nt = FONT_INPUT.render(self.name_input, True, WHITE)
        tx = bx + 16
        ty = by + bh // 2 - nt.get_height() // 2
        screen.blit(nt, (tx, ty))
        if (self.frame // 30) % 2 == 0:
            cur_x = tx + nt.get_width() + 2
            pygame.draw.rect(screen, CURSOR_COL, (cur_x, ty + 2, 3, nt.get_height() - 4))
        cc = FONT_XS.render(f"{len(self.name_input)}/{self.name_max}", True, GREY)
        screen.blit(cc, (bx + bw - cc.get_width() - 8, by + bh + 5))
        txt_c(screen, "Press ENTER to submit", FONT_SM, GOLD, 360)
        txt_c(screen, "(Leave blank for 'ANON')", FONT_XS, GREY_DIM, 385)

    # ── LEADERBOARD SCREEN ──
    def _d_lb(self):
        if self.came_from_win:
            txt_sh(screen, "VICTORY!", FONT_LG, GOLD, 50)
        else:
            txt_sh(screen, "FINAL RESULTS", FONT_LG, CYAN, 50)
        if self.final_dnf:
            txt_sh(screen, "Time: DNF", FONT_MD, RED, 95)
        else:
            txt_sh(screen, f"Time: {format_time(self.final_time)}", FONT_MD, WHITE, 95)
        if self.lb_is_high:
            t = self.frame * 0.08
            r = int(200 + 55 * math.sin(t))
            g = int(200 + 55 * math.sin(t + 2))
            b = int(200 + 55 * math.sin(t + 4))
            txt_sh(screen, "NEW LEADERBOARD ENTRY!", FONT_MD, (r, g, b), 130)
        hl_name = self.name_input.strip() or "ANON"
        draw_lb_panel(screen, self.lb_board, WIDTH // 2, 160,
                      title="LEADERBOARD", hl_name=hl_name,
                      hl_score=round(self.final_time, 2), pw=430, rh=24)
        pulse = int(180 + 60 * math.sin(self.frame * 0.05))
        txt_c(screen, "Press SPACE or ENTER for menu", FONT_SM,
              (pulse, pulse, min(255, pulse)), 600)


# ═══════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════
def return_to_launcher():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    launcher = os.path.join(base_dir, "start_page.py")
    if os.path.exists(launcher):
        subprocess.Popen([sys.executable, launcher], cwd=base_dir)
    pygame.quit()
    sys.exit()


def draw_menu_button(surface, rect):
    hovered = rect.collidepoint(pygame.mouse.get_pos())
    fill = (32, 75, 155) if not hovered else (57, 112, 205)
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, (210, 235, 255), rect, width=2, border_radius=8)
    font = pygame.font.SysFont("consolas", 18, bold=True)
    txt = font.render("Menu", True, (245, 245, 245))
    surface.blit(txt, txt.get_rect(center=rect.center))


def main():
    game = Game()
    menu_btn = pygame.Rect(WIDTH - 122, 10, 110, 34)
    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and menu_btn.collidepoint(ev.pos):
                return_to_launcher()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_0:
                return_to_launcher()
            if not game.handle(ev):
                running = False
        game.update()
        game.draw()
        draw_menu_button(screen, menu_btn)
        clock.tick(FPS)
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()