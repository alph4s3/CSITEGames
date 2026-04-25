#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║  MATH JETPACK — An Endless Math-Powered Runner                   ║
║                                                                   ║
║  Controls:                                                        ║
║    SPACE (hold)   Jetpack ON — fly up                             ║
║    Release SPACE  Fall with gravity                               ║
║    Mouse click    Also works as jetpack                           ║
║    R              Restart (on game over)                          ║
║    ESC            Quit                                            ║
║                                                                   ║
║  Fly through the gate with the CORRECT answer for a big bonus!    ║
║  Wrong answer = jetpack stalls for a moment. Watch your altitude! ║
╚═══════════════════════════════════════════════════════════════════╝
"""

import pygame
import math
import random
import json
import os
import subprocess
import sys
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════
#  INITIALIZATION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════
pygame.init()

WIDTH, HEIGHT = 960, 540
FPS = 60
HUD_H = 60
FLOOR_Y = HEIGHT - 40
CEIL_Y  = HUD_H + 10
PLAY_TOP = CEIL_Y
PLAY_BOT = FLOOR_Y

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Math Jetpack")
clock = pygame.time.Clock()

# ═══════════════════════════════════════════════════════════════════
#  COLOR PALETTE (neon retro)
# ═══════════════════════════════════════════════════════════════════
BLACK        = (8, 8, 16)
WHITE        = (240, 240, 245)
BG_DARK      = (12, 14, 28)
BG_MID       = (22, 24, 50)
BG_FAR       = (35, 30, 70)
FLOOR_COL    = (60, 40, 80)
FLOOR_TOP    = (110, 70, 160)
CEIL_COL     = (60, 40, 80)
CEIL_BOT     = (110, 70, 160)
GRID_COL     = (50, 35, 100)
NEON_PINK    = (255, 70, 180)
NEON_CYAN    = (80, 230, 240)
NEON_GREEN   = (60, 240, 130)
NEON_YELLOW  = (255, 230, 60)
NEON_ORANGE  = (255, 140, 50)
NEON_RED     = (255, 60, 80)
NEON_PURPLE  = (180, 80, 255)
GOLD         = (255, 210, 50)
GOLD_HI      = (255, 240, 150)
GREY         = (110, 110, 130)
GREY_DIM     = (60, 60, 80)
GREY_DARK    = (35, 35, 50)
PANEL_BG     = (18, 16, 35)
PANEL_BORDER = (80, 65, 130)
INPUT_BG     = (25, 22, 45)
CURSOR_COL   = (255, 220, 100)
PLAYER_BODY  = (255, 230, 60)
PLAYER_DARK  = (200, 160, 30)
PLAYER_SUIT  = (90, 110, 200)
JET_OUTER    = (255, 80, 30)
JET_MID      = (255, 180, 50)
JET_INNER    = (255, 250, 200)
HUD_BG       = (10, 10, 22)
GATE_FRAME   = (200, 180, 255)
GATE_FILL    = (60, 50, 110)
GATE_CORRECT = (60, 240, 130)
GATE_WRONG   = (255, 70, 90)

# ═══════════════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════════════
FONT_XL     = pygame.font.SysFont("consolas", 52, bold=True)
FONT_LG     = pygame.font.SysFont("consolas", 36, bold=True)
FONT_MD     = pygame.font.SysFont("consolas", 24, bold=True)
FONT_SM     = pygame.font.SysFont("consolas", 19)
FONT_XS     = pygame.font.SysFont("consolas", 14)
FONT_HUD    = pygame.font.SysFont("consolas", 18, bold=True)
FONT_GATE   = pygame.font.SysFont("consolas", 22, bold=True)
FONT_INPUT  = pygame.font.SysFont("consolas", 30, bold=True)
FONT_LB     = pygame.font.SysFont("consolas", 17, bold=True)
FONT_LB_HDR = pygame.font.SysFont("consolas", 20, bold=True)

# ═══════════════════════════════════════════════════════════════════
#  PHYSICS / GAMEPLAY CONSTANTS
# ═══════════════════════════════════════════════════════════════════
GRAVITY        = 0.50
THRUST         = -0.75
MAX_FALL_SPEED = 10
MAX_RISE_SPEED = -10
PLAYER_X       = 180          # fixed X position; world scrolls past
START_SPEED    = 4.5          # initial scroll speed
MAX_SPEED      = 11.5
SPEED_RAMP     = 0.00045      # speed increase per frame
COIN_VAL       = 10
GATE_BONUS     = 250
PENALTY_FRAMES = 60           # jetpack stall duration on wrong answer
INVULN_FRAMES  = 60           # invulnerability after a non-fatal hit
DIST_PER_PIXEL = 0.1          # how distance score scales with scrolled pixels

# Spawn distances (in pixels of world scroll)
OBSTACLE_MIN_GAP = 320
OBSTACLE_MAX_GAP = 520
COIN_MIN_GAP     = 180
COIN_MAX_GAP     = 380
GATE_MIN_GAP     = 1500       # math gates appear less frequently
GATE_MAX_GAP     = 2400

# ═══════════════════════════════════════════════════════════════════
#  LEADERBOARD (JSON persistence)
# ═══════════════════════════════════════════════════════════════════
LB_FILE = "leaderboardJPJR.json"
MAX_LB  = 10


def load_leaderboard() -> list:
    if os.path.exists(LB_FILE):
        try:
            with open(LB_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                clean = [e for e in data if isinstance(e, dict)
                         and isinstance(e.get("score"), (int, float))]
                return sorted(clean, key=lambda e: e["score"], reverse=True)[:MAX_LB]
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_leaderboard(board: list):
    try:
        with open(LB_FILE, "w") as f:
            json.dump(board[:MAX_LB], f, indent=2)
    except IOError:
        pass


def add_to_leaderboard(name: str, score: int) -> Tuple[list, bool]:
    """Add an entry; returns (board, is_top_10)."""
    board = load_leaderboard()
    entry = {"name": name, "score": int(score)}
    board.append(entry)
    board.sort(key=lambda e: e.get("score", 0), reverse=True)
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


def _synth(freq, ms, vol=0.10):
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


SFX_COIN  = _synth(900, 80, 0.10)
SFX_OK    = _synth(1100, 200, 0.13)
SFX_BAD   = _synth(180, 250, 0.13)
SFX_HURT  = _synth(220, 200, 0.13)
SFX_DIE   = _synth(150, 400, 0.15)
SFX_TYPE  = _synth(900, 25, 0.06)


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


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ═══════════════════════════════════════════════════════════════════
#  PARTICLE
# ═══════════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'life', 'max_life',
                 'size', 'is_text', 'text', 'gravity')

    def __init__(self, x, y, vx, vy, color, life=30, size=3, text=None, gravity=0.0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.is_text = text is not None
        self.text = text
        self.gravity = gravity

    def update(self, scroll_speed=0.0):
        # Particles also drift left with the world scroll for cohesion
        self.x += self.vx - scroll_speed * 0.3
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


def emit(x, y, color, n=12, speed=4.0, life=24, size=3, gravity=0.0):
    for _ in range(n):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(0.8, speed)
        g_parts.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd,
            color, random.randint(life // 2, life),
            random.uniform(size * 0.5, size), gravity=gravity))


def emit_text(x, y, text, color, life=60):
    g_parts.append(Particle(x, y - 10, 0, -1.0, color, life, text=text, gravity=0))


def emit_jet_flame(x, y, intensity=1.0):
    """Continuous flame trail behind the player."""
    for _ in range(int(2 * intensity)):
        spread = random.uniform(-3, 3)
        col = random.choice([JET_OUTER, JET_MID, JET_INNER])
        g_parts.append(Particle(
            x + random.uniform(-2, 2), y + spread,
            random.uniform(-3, -1), random.uniform(-0.8, 0.8),
            col, random.randint(8, 16), random.uniform(2, 4), gravity=0.0
        ))


# ═══════════════════════════════════════════════════════════════════
#  BACKGROUND CLASS — parallax scrolling lab
# ═══════════════════════════════════════════════════════════════════
class Background:
    """Parallax scrolling background with grid lines, distant pillars, and floor/ceiling."""

    def __init__(self):
        # Far-back pillars (deep parallax)
        self.far_pillars = []
        for i in range(8):
            self.far_pillars.append({
                'x': i * (WIDTH // 8) + random.randint(-30, 30),
                'w': random.randint(40, 80),
                'h': random.randint(120, 260),
            })
        # Mid-layer panels
        self.mid_panels = []
        for i in range(6):
            self.mid_panels.append({
                'x': i * (WIDTH // 5) + random.randint(-50, 50),
                'w': random.randint(80, 140),
                'h': random.randint(60, 140),
            })
        # Floor/ceiling tile offset
        self.tile_offset = 0.0
        self.grid_offset = 0.0

    def update(self, speed):
        for p in self.far_pillars:
            p['x'] -= speed * 0.2
            if p['x'] + p['w'] < 0:
                p['x'] = WIDTH + random.randint(20, 100)
                p['w'] = random.randint(40, 80)
                p['h'] = random.randint(120, 260)
        for p in self.mid_panels:
            p['x'] -= speed * 0.5
            if p['x'] + p['w'] < 0:
                p['x'] = WIDTH + random.randint(20, 100)
                p['w'] = random.randint(80, 140)
                p['h'] = random.randint(60, 140)
        self.tile_offset = (self.tile_offset + speed) % 40
        self.grid_offset = (self.grid_offset + speed * 0.3) % 80

    def draw(self, surf):
        # Background gradient
        for y in range(PLAY_TOP, PLAY_BOT, 4):
            t = (y - PLAY_TOP) / max(1, PLAY_BOT - PLAY_TOP)
            r = int(BG_DARK[0] * (1 - t) + BG_MID[0] * t)
            g = int(BG_DARK[1] * (1 - t) + BG_MID[1] * t)
            b = int(BG_DARK[2] * (1 - t) + BG_MID[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (WIDTH, y))

        # Distant pillars (deepest layer)
        for p in self.far_pillars:
            x = int(p['x'])
            h = p['h']
            y = PLAY_BOT - h
            pygame.draw.rect(surf, BG_FAR, (x, y, p['w'], h))
            # Window dots
            for wy in range(y + 12, y + h - 8, 18):
                for wx in range(x + 6, x + p['w'] - 4, 12):
                    if (wx + wy) % 30 < 12:
                        pygame.draw.rect(surf, (80, 60, 130), (wx, wy, 4, 6))

        # Grid lines (mid layer) — vertical
        gx_off = int(self.grid_offset)
        for gx in range(-gx_off, WIDTH, 80):
            pygame.draw.line(surf, GRID_COL, (gx, PLAY_TOP), (gx, PLAY_BOT), 1)
        # Horizontal grid
        for gy in range(PLAY_TOP, PLAY_BOT, 80):
            pygame.draw.line(surf, GRID_COL, (0, gy), (WIDTH, gy), 1)

        # Mid panels
        for p in self.mid_panels:
            x = int(p['x'])
            h = p['h']
            y = PLAY_BOT - h - 5
            pygame.draw.rect(surf, (45, 35, 90), (x, y, p['w'], h))
            pygame.draw.rect(surf, (75, 55, 140), (x, y, p['w'], 4))
            # Glowing strip
            pygame.draw.line(surf, NEON_PINK, (x + 6, y + h - 8),
                             (x + p['w'] - 6, y + h - 8), 2)

        # Floor
        pygame.draw.rect(surf, FLOOR_COL, (0, PLAY_BOT, WIDTH, HEIGHT - PLAY_BOT))
        pygame.draw.rect(surf, FLOOR_TOP, (0, PLAY_BOT, WIDTH, 4))
        # Animated floor stripes
        ox = int(self.tile_offset)
        for fx in range(-ox, WIDTH, 40):
            pygame.draw.line(surf, NEON_PURPLE, (fx, PLAY_BOT + 12),
                             (fx + 20, PLAY_BOT + 12), 2)

        # Ceiling
        pygame.draw.rect(surf, CEIL_COL, (0, PLAY_TOP - 10, WIDTH, 10))
        pygame.draw.rect(surf, CEIL_BOT, (0, PLAY_TOP - 4, WIDTH, 4))
        for fx in range(-ox, WIDTH, 40):
            pygame.draw.line(surf, NEON_PURPLE, (fx, PLAY_TOP - 14),
                             (fx + 20, PLAY_TOP - 14), 2)


# ═══════════════════════════════════════════════════════════════════
#  PLAYER CLASS
# ═══════════════════════════════════════════════════════════════════
class Player:
    W, H = 38, 50

    def __init__(self):
        self.x = float(PLAYER_X)
        self.y = float((PLAY_TOP + PLAY_BOT) / 2)
        self.vy = 0.0
        self.thrust_on = False
        self.alive = True
        self.invuln = 0
        self.stall_timer = 0     # disables jetpack briefly (penalty)
        self.anim_t = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.W / 2), int(self.y - self.H / 2),
                           self.W, self.H)

    def update(self):
        self.anim_t += 0.18
        if self.invuln > 0:
            self.invuln -= 1
        if self.stall_timer > 0:
            self.stall_timer -= 1

        # Apply thrust if on AND not stalled
        if self.thrust_on and self.stall_timer == 0:
            self.vy += THRUST
        else:
            self.vy += GRAVITY

        self.vy = clamp(self.vy, MAX_RISE_SPEED, MAX_FALL_SPEED)
        self.y += self.vy

        # Floor / ceiling collisions: don't kill, just clamp
        if self.y + self.H / 2 > PLAY_BOT:
            self.y = PLAY_BOT - self.H / 2
            self.vy = 0
        if self.y - self.H / 2 < PLAY_TOP:
            self.y = PLAY_TOP + self.H / 2
            self.vy = 0

    def emit_flame(self):
        """Emit jetpack flame particles when thrusting."""
        if self.thrust_on and self.stall_timer == 0 and self.alive:
            jx = self.x - self.W / 2 + 4
            jy = self.y + self.H / 2 - 8
            emit_jet_flame(jx, jy, intensity=1.2)

    def hurt(self, fatal=False):
        if fatal:
            self.alive = False
            sfx(SFX_DIE)
            emit(self.x, self.y, NEON_RED, n=30, speed=6, life=40, size=5, gravity=0.15)
            emit(self.x, self.y, NEON_ORANGE, n=20, speed=5, life=30, size=4, gravity=0.1)
            return True
        if self.invuln > 0:
            return False
        self.invuln = INVULN_FRAMES
        sfx(SFX_HURT)
        emit(self.x, self.y, NEON_RED, n=15, speed=4, life=22, gravity=0.05)
        return False

    def draw(self, surf):
        # Flicker if invulnerable
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            return
        ix, iy = int(self.x), int(self.y)
        # Subtle vertical bob
        bob = int(math.sin(self.anim_t) * 1.5)

        # === JETPACK (back) ===
        jp_rect = pygame.Rect(ix - self.W // 2, iy - 12 + bob, 12, 28)
        pygame.draw.rect(surf, (60, 70, 90), jp_rect, border_radius=3)
        pygame.draw.rect(surf, (130, 140, 170), (jp_rect.x + 1, jp_rect.y + 2,
                                                  jp_rect.w - 2, 3), border_radius=2)
        # Stall indicator (smoke puffs)
        if self.stall_timer > 0:
            for _ in range(1):
                emit(jp_rect.x + 6, jp_rect.bottom + 2, GREY, n=1, speed=1, life=15, size=2)

        # === BODY (suit torso) ===
        body_r = pygame.Rect(ix - 10, iy - 8 + bob, 20, 24)
        pygame.draw.rect(surf, PLAYER_SUIT, body_r, border_radius=5)
        # Belt
        pygame.draw.rect(surf, (40, 50, 100), (body_r.x, body_r.bottom - 5, body_r.w, 4))
        pygame.draw.circle(surf, GOLD, (body_r.centerx, body_r.bottom - 3), 2)

        # === LEGS ===
        leg_swing = math.sin(self.anim_t) * 3
        pygame.draw.line(surf, PLAYER_SUIT, (ix - 5, iy + 16 + bob),
                         (ix - 5 + int(leg_swing), iy + 24 + bob), 4)
        pygame.draw.line(surf, PLAYER_SUIT, (ix + 5, iy + 16 + bob),
                         (ix + 5 - int(leg_swing), iy + 24 + bob), 4)
        # Boots
        pygame.draw.rect(surf, (30, 30, 40),
                         (ix - 7 + int(leg_swing), iy + 22 + bob, 6, 4))
        pygame.draw.rect(surf, (30, 30, 40),
                         (ix + 1 - int(leg_swing), iy + 22 + bob, 6, 4))

        # === HEAD (helmet) ===
        head_y = iy - 16 + bob
        pygame.draw.circle(surf, PLAYER_DARK, (ix, head_y + 1), 12)
        pygame.draw.circle(surf, PLAYER_BODY, (ix, head_y), 11)
        # Visor
        pygame.draw.rect(surf, NEON_CYAN, (ix - 7, head_y - 2, 14, 6), border_radius=2)
        pygame.draw.rect(surf, (180, 240, 255), (ix - 6, head_y - 2, 4, 2), border_radius=1)

        # === ARMS ===
        # Forward arm
        pygame.draw.line(surf, PLAYER_SUIT, (ix + 8, iy - 4 + bob),
                         (ix + 14, iy + 2 + bob), 4)
        # Back arm (gripping jetpack)
        pygame.draw.line(surf, PLAYER_SUIT, (ix - 8, iy - 4 + bob),
                         (ix - 12, iy + 2 + bob), 4)


# ═══════════════════════════════════════════════════════════════════
#  COIN CLASS
# ═══════════════════════════════════════════════════════════════════
class Coin:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.alive = True
        self.spin = random.uniform(0, math.tau)
        self.bob = random.uniform(0, math.tau)

    def update(self, speed):
        self.x -= speed
        self.spin += 0.18
        self.bob += 0.07
        if self.x < -30:
            self.alive = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 10, int(self.y) - 10, 20, 20)

    def draw(self, surf):
        if not self.alive:
            return
        ix = int(self.x)
        iy = int(self.y + math.sin(self.bob) * 3)
        # Spinning ellipse for coin effect
        w_spin = abs(math.cos(self.spin))
        ww = max(3, int(12 * w_spin))
        # Glow halo
        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*GOLD, 60), (15, 15), 12)
        surf.blit(glow, (ix - 15, iy - 15))
        # Coin body
        pygame.draw.ellipse(surf, GOLD, (ix - ww, iy - 12, ww * 2, 24))
        pygame.draw.ellipse(surf, GOLD_HI, (ix - ww + 1, iy - 11, ww * 2 - 2, 6))
        if ww >= 6:
            # $ sign
            ds = FONT_XS.render("$", True, (130, 90, 20))
            surf.blit(ds, (ix - ds.get_width() // 2, iy - ds.get_height() // 2))


# ═══════════════════════════════════════════════════════════════════
#  OBSTACLE CLASSES
# ═══════════════════════════════════════════════════════════════════
class Zapper:
    """Vertical electric beam between two emitters."""
    def __init__(self, x, top_y, bot_y):
        self.x = float(x)
        self.top_y = top_y
        self.bot_y = bot_y
        self.alive = True
        self.t = random.uniform(0, math.tau)

    def update(self, speed):
        self.x -= speed
        self.t += 0.25
        if self.x < -40:
            self.alive = False

    def collides(self, rect: pygame.Rect) -> bool:
        beam = pygame.Rect(int(self.x) - 4, self.top_y + 14, 8,
                           self.bot_y - self.top_y - 28)
        return beam.colliderect(rect)

    def draw(self, surf):
        if not self.alive:
            return
        ix = int(self.x)
        # Top emitter
        pygame.draw.rect(surf, (180, 100, 200), (ix - 12, self.top_y, 24, 14),
                         border_radius=3)
        pygame.draw.rect(surf, NEON_PINK, (ix - 10, self.top_y + 2, 20, 4),
                         border_radius=2)
        # Bottom emitter
        pygame.draw.rect(surf, (180, 100, 200),
                         (ix - 12, self.bot_y - 14, 24, 14), border_radius=3)
        pygame.draw.rect(surf, NEON_PINK,
                         (ix - 10, self.bot_y - 6, 20, 4), border_radius=2)
        # Beam — pulsing
        pulse = 0.7 + 0.3 * abs(math.sin(self.t))
        beam_w = int(3 * pulse) + 2
        beam_glow = pygame.Surface((20, self.bot_y - self.top_y), pygame.SRCALPHA)
        pygame.draw.rect(beam_glow, (255, 100, 200, 50),
                         (10 - beam_w - 2, 14, beam_w * 2 + 4,
                          self.bot_y - self.top_y - 28))
        surf.blit(beam_glow, (ix - 10, self.top_y))
        pygame.draw.rect(surf, NEON_PINK,
                         (ix - beam_w // 2, self.top_y + 14, beam_w,
                          self.bot_y - self.top_y - 28))
        pygame.draw.rect(surf, WHITE,
                         (ix - 1, self.top_y + 14, 2,
                          self.bot_y - self.top_y - 28))


class Missile:
    """Homing-ish missile that flies in from the right."""
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vx = -2.0   # in addition to scroll speed
        self.alive = True
        self.t = random.uniform(0, math.tau)

    def update(self, speed):
        # Missiles drift slightly toward player y-wise; we track via game ref later
        self.x -= speed + 1.5
        self.t += 0.3
        if self.x < -50:
            self.alive = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 18, int(self.y) - 7, 36, 14)

    def collides(self, r: pygame.Rect) -> bool:
        return self.rect.colliderect(r)

    def draw(self, surf):
        if not self.alive:
            return
        ix, iy = int(self.x), int(self.y)
        # Body
        pygame.draw.rect(surf, NEON_RED, (ix - 16, iy - 6, 28, 12), border_radius=3)
        pygame.draw.rect(surf, (180, 40, 60), (ix - 16, iy + 2, 28, 4), border_radius=2)
        # Nose cone
        pygame.draw.polygon(surf, NEON_YELLOW, [(ix - 16, iy - 6), (ix - 22, iy),
                                                 (ix - 16, iy + 6)])
        # Fins
        pygame.draw.polygon(surf, (180, 40, 60), [(ix + 12, iy - 6), (ix + 18, iy - 10),
                                                   (ix + 14, iy - 4)])
        pygame.draw.polygon(surf, (180, 40, 60), [(ix + 12, iy + 6), (ix + 18, iy + 10),
                                                   (ix + 14, iy + 4)])
        # Exhaust flame at back
        flame_l = 4 + int(abs(math.sin(self.t)) * 6)
        pygame.draw.polygon(surf, JET_OUTER,
                            [(ix + 12, iy - 4), (ix + 12 + flame_l, iy),
                             (ix + 12, iy + 4)])
        pygame.draw.polygon(surf, JET_MID,
                            [(ix + 12, iy - 2), (ix + 12 + flame_l - 2, iy),
                             (ix + 12, iy + 2)])


class Spike:
    """A row of pointed spikes attached to floor or ceiling."""
    def __init__(self, x, on_floor=True, count=3):
        self.x = float(x)
        self.on_floor = on_floor
        self.count = count
        self.alive = True
        self.w = count * 18

    def update(self, speed):
        self.x -= speed
        if self.x + self.w < -10:
            self.alive = False

    @property
    def rect(self):
        if self.on_floor:
            return pygame.Rect(int(self.x), PLAY_BOT - 18, self.w, 18)
        else:
            return pygame.Rect(int(self.x), PLAY_TOP, self.w, 18)

    def collides(self, r: pygame.Rect) -> bool:
        return self.rect.colliderect(r)

    def draw(self, surf):
        if not self.alive:
            return
        ix = int(self.x)
        for i in range(self.count):
            sx = ix + i * 18
            if self.on_floor:
                base_y = PLAY_BOT
                tip_y = base_y - 16
                pts = [(sx, base_y), (sx + 9, tip_y), (sx + 18, base_y)]
                pygame.draw.polygon(surf, GREY, pts)
                pygame.draw.polygon(surf, (200, 200, 220),
                                    [(sx + 7, base_y - 2), (sx + 9, tip_y + 2),
                                     (sx + 9, base_y - 2)])
            else:
                base_y = PLAY_TOP
                tip_y = base_y + 16
                pts = [(sx, base_y), (sx + 9, tip_y), (sx + 18, base_y)]
                pygame.draw.polygon(surf, GREY, pts)
                pygame.draw.polygon(surf, (200, 200, 220),
                                    [(sx + 7, base_y + 2), (sx + 9, tip_y - 2),
                                     (sx + 9, base_y + 2)])


# ═══════════════════════════════════════════════════════════════════
#  MATH GATE & ANSWER OPTIONS
# ═══════════════════════════════════════════════════════════════════
class AnswerOption:
    """A floating gate with a number. Player flies through to choose."""
    GATE_W  = 70
    GATE_H  = 100

    def __init__(self, x, y, value, is_correct):
        self.x = float(x)
        self.y = float(y)
        self.value = value
        self.is_correct = is_correct
        self.alive = True
        self.triggered = False    # set true once player passes through
        self.flash_timer = 0
        self.t = random.uniform(0, math.tau)

    def update(self, speed):
        self.x -= speed
        self.t += 0.05
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.x < -100:
            self.alive = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - self.GATE_W // 2,
                           int(self.y) - self.GATE_H // 2,
                           self.GATE_W, self.GATE_H)

    def contains_player(self, player_rect: pygame.Rect) -> bool:
        return self.rect.colliderect(player_rect)

    def draw(self, surf):
        if not self.alive:
            return
        ix, iy = int(self.x), int(self.y)
        w, h = self.GATE_W, self.GATE_H
        x = ix - w // 2
        y = iy - h // 2
        pulse = 0.7 + 0.3 * math.sin(self.t * 2)

        # Color depends on triggered state
        if self.flash_timer > 0:
            frame_col = GATE_CORRECT if self.is_correct else GATE_WRONG
        else:
            frame_col = GATE_FRAME

        # Glow halo
        glow = pygame.Surface((w + 30, h + 30), pygame.SRCALPHA)
        ga = int(40 * pulse)
        gc = frame_col if self.flash_timer > 0 else (200, 200, 255)
        pygame.draw.rect(glow, (*gc, ga), (0, 0, w + 30, h + 30), border_radius=12)
        surf.blit(glow, (x - 15, y - 15))

        # Top frame
        pygame.draw.rect(surf, frame_col, (x - 6, y - 4, w + 12, 14), border_radius=4)
        pygame.draw.rect(surf, GATE_FILL, (x - 4, y - 2, w + 8, 10), border_radius=3)
        # Bottom frame
        pygame.draw.rect(surf, frame_col, (x - 6, y + h - 10, w + 12, 14), border_radius=4)
        pygame.draw.rect(surf, GATE_FILL, (x - 4, y + h - 8, w + 8, 10), border_radius=3)
        # Side posts
        pygame.draw.rect(surf, frame_col, (x - 6, y, 4, h), border_radius=2)
        pygame.draw.rect(surf, frame_col, (x + w + 2, y, 4, h), border_radius=2)
        # Translucent fly-through area
        inside = pygame.Surface((w, h - 20), pygame.SRCALPHA)
        inside.fill((*frame_col, 30))
        surf.blit(inside, (x, y + 10))

        # Value display
        nt = FONT_GATE.render(str(self.value), True, WHITE)
        surf.blit(nt, (ix - nt.get_width() // 2, iy - nt.get_height() // 2))


# ═══════════════════════════════════════════════════════════════════
#  MATH PROBLEM GENERATOR (difficulty grows with distance)
# ═══════════════════════════════════════════════════════════════════
def gen_problem(difficulty: int):
    """difficulty: 1..5, returns (question, answer)."""
    types = {
        1: ['add', 'sub', 'mul', 'fib'],
        2: ['add', 'sub', 'mul', 'div', 'fib'],
        3: ['mul', 'div', 'algebra', 'add', 'fib'],
        4: ['algebra', 'mul', 'div', 'add', 'fib'],
        5: ['algebra', 'mul', 'div', 'algebra', 'fib'],
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
    elif kind == 'fib':
        seq_len = random.randint(4 + difficulty, 6 + difficulty)
        seq = [1, 1]
        while len(seq) < seq_len:
            seq.append(seq[-1] + seq[-2])
        shown = ", ".join(str(v) for v in seq[-4:])
        return f"Next in Fibonacci: {shown}, ?", seq[-1] + seq[-2]
    a, b = random.randint(5, 20), random.randint(5, 20)
    return f"{a} + {b}", a + b


def gen_wrong(correct, n=2, spread=8):
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
        et = FONT_LB.render("No scores yet — be the first!", True, GREY)
        surf.blit(et, (cx - et.get_width() // 2, ry + 10))
        return
    for text, xoff in [("#", 14), ("NAME", 50), ("SCORE", pw - 80)]:
        ct = FONT_XS.render(text, True, GREY)
        surf.blit(ct, (px + xoff, ry))
    ry += col_hdr_h
    rank_colors = [GOLD, (200, 200, 210), NEON_ORANGE]
    for i, entry in enumerate(board):
        name = entry.get("name", "???")
        score = entry.get("score", 0)
        is_hl = (hl_name and hl_score is not None
                 and name == hl_name and score == hl_score)
        if is_hl:
            pygame.draw.rect(surf, (50, 40, 80),
                             (px + 4, ry - 1, pw - 8, rh), border_radius=3)
        rc = rank_colors[i] if i < 3 else GREY
        nc = WHITE if is_hl else (210, 210, 220)
        sc_c = GOLD if is_hl else (180, 180, 190)
        rt = FONT_LB.render(f"{i+1}.", True, rc)
        nt = FONT_LB.render(name[:12], True, nc)
        st = FONT_LB.render(str(score), True, sc_c)
        surf.blit(rt, (px + 14, ry))
        surf.blit(nt, (px + 50, ry))
        surf.blit(st, (px + pw - 16 - st.get_width(), ry))
        ry += rh


# ═══════════════════════════════════════════════════════════════════
#  GAME CLASS
# ═══════════════════════════════════════════════════════════════════
class Game:
    TITLE      = 0
    PLAYING    = 1
    DYING      = 2     # brief fade after death
    GAME_OVER  = 3
    NAME_ENTRY = 4
    LB_SCREEN  = 5

    def __init__(self):
        self.state = self.TITLE
        self.frame = 0
        self.bg = Background()
        self.player: Optional[Player] = None
        self.coins: List[Coin] = []
        self.zappers: List[Zapper] = []
        self.missiles: List[Missile] = []
        self.spikes: List[Spike] = []
        self.gates: List[AnswerOption] = []   # currently-on-screen gates from active gate spawn
        # Scrolling / progression
        self.speed = START_SPEED
        self.distance = 0.0           # in "meters" (scaled pixel scroll)
        self.score = 0
        self.coin_count = 0
        # Spawn schedulers
        self.next_obstacle = 600       # initial delay before obstacles (ease-in)
        self.next_coin     = 250
        self.next_gate     = 1200      # first gate appears earlier than steady pace
        # Math gate state
        self.active_question = ""      # the displayed question text
        self.active_answer   = 0
        self.gate_cooldown   = 0       # frames until we can spawn another gate
        # Death / over
        self.dying_timer = 0
        self.show_timer  = 0
        # Flash messages
        self.flash_txt = ""
        self.flash_col = WHITE
        self.flash_t   = 0
        # Name entry / leaderboard
        self.name_input  = ""
        self.name_max    = 12
        self.final_score = 0
        self.lb_board: list = []
        self.lb_is_high  = False
        self.title_lb    = load_leaderboard()
        # Cached high score for title display
        self.high_score  = self.title_lb[0]['score'] if self.title_lb else 0
        g_parts.clear()

    def full_reset(self):
        self.__init__()

    def start_run(self):
        self.player = Player()
        self.coins.clear()
        self.zappers.clear()
        self.missiles.clear()
        self.spikes.clear()
        self.gates.clear()
        self.speed = START_SPEED
        self.distance = 0.0
        self.score = 0
        self.coin_count = 0
        self.next_obstacle = 600
        self.next_coin = 250
        self.next_gate = 1400
        self.active_question = ""
        self.active_answer = 0
        self.gate_cooldown = 0
        self.dying_timer = 0
        self.flash_t = 0
        g_parts.clear()
        self.state = self.PLAYING

    def difficulty(self):
        """Return integer difficulty 1..5 based on distance."""
        d = self.distance
        if d < 400:   return 1
        if d < 1200:  return 2
        if d < 2400:  return 3
        if d < 4000:  return 4
        return 5

    def flash(self, txt, col, dur=70):
        self.flash_txt = txt
        self.flash_col = col
        self.flash_t = dur

    # ── Spawn an obstacle (random kind based on difficulty) ──
    def _spawn_obstacle(self):
        diff = self.difficulty()
        kinds = ['zapper', 'spike']
        if diff >= 2:
            kinds.append('zapper')   # more zappers
        if diff >= 3:
            kinds.append('missile')
        if diff >= 4:
            kinds.extend(['missile', 'spike'])
        kind = random.choice(kinds)
        spawn_x = WIDTH + 60

        if kind == 'zapper':
            # Vertical zapper of varying height
            min_h = 80
            max_h = 220
            beam_h = random.randint(min_h, max_h)
            # Random vertical position
            top = random.randint(PLAY_TOP, PLAY_BOT - beam_h)
            self.zappers.append(Zapper(spawn_x, top, top + beam_h))
        elif kind == 'missile':
            # Spawn at random height in playfield
            y = random.randint(PLAY_TOP + 40, PLAY_BOT - 40)
            self.missiles.append(Missile(spawn_x + 50, y))
        elif kind == 'spike':
            on_floor = random.random() < 0.6
            count = random.randint(2, 4)
            self.spikes.append(Spike(spawn_x, on_floor=on_floor, count=count))

    # ── Spawn a coin pattern (small line/cluster) ──
    def _spawn_coin_cluster(self):
        n = random.randint(3, 6)
        pattern = random.choice(['line', 'arc', 'wave'])
        base_y = random.randint(PLAY_TOP + 60, PLAY_BOT - 60)
        for i in range(n):
            x = WIDTH + 60 + i * 30
            if pattern == 'line':
                y = base_y
            elif pattern == 'arc':
                y = base_y - int(math.sin(i / max(1, n - 1) * math.pi) * 40)
            else:  # wave
                y = base_y + int(math.sin(i * 0.8) * 30)
            y = clamp(y, PLAY_TOP + 20, PLAY_BOT - 20)
            self.coins.append(Coin(x, y))

    # ── Spawn a math gate (3 answer options stacked vertically) ──
    def _spawn_math_gate(self):
        diff = self.difficulty()
        q, a = gen_problem(diff)
        self.active_question = q + " = ?"
        self.active_answer = a
        wrongs = gen_wrong(a, 2, 4 + diff * 2)

        # 3 vertical slots
        n_options = 3
        options_x = WIDTH + 100

        # Gate slot heights: top, middle, bottom
        slot_ys = []
        avail_h = PLAY_BOT - PLAY_TOP - 30
        gate_h = AnswerOption.GATE_H
        spacing = (avail_h - gate_h * n_options) / (n_options + 1)
        for i in range(n_options):
            sy = PLAY_TOP + 15 + spacing * (i + 1) + gate_h * (i + 0.5)
            slot_ys.append(int(sy))

        # Pick which slot is correct
        ci = random.randint(0, n_options - 1)
        values = []
        for i in range(n_options):
            if i == ci:
                values.append((a, True))
            else:
                values.append((wrongs.pop(0), False))

        for (val, is_corr), sy in zip(values, slot_ys):
            self.gates.append(AnswerOption(options_x, sy, val, is_corr))

        # Sparkles on entry
        emit(WIDTH - 20, HEIGHT // 2, NEON_CYAN, n=8, speed=2, life=20, size=3)

    # ── UPDATE ──
    def update(self):
        self.frame += 1

        if self.state == self.TITLE:
            self.bg.update(START_SPEED * 0.6)
            self._tick_p()
            return

        if self.state == self.DYING:
            self.dying_timer -= 1
            self._tick_p()
            if self.dying_timer <= 0:
                self.state = self.GAME_OVER
                self.show_timer = 120
            return

        if self.state == self.GAME_OVER:
            self.show_timer -= 1
            self._tick_p()
            if self.show_timer <= 0:
                self._go_name_entry()
            return

        if self.state in (self.NAME_ENTRY, self.LB_SCREEN):
            self.bg.update(START_SPEED * 0.4)
            self._tick_p()
            return

        if self.state != self.PLAYING:
            return

        # ── PLAYING ──
        # Ramp speed
        self.speed = min(MAX_SPEED, self.speed + SPEED_RAMP)
        self.bg.update(self.speed)
        # Track distance
        self.distance += self.speed * DIST_PER_PIXEL
        # Distance score
        self.score = int(self.distance) + self.coin_count * COIN_VAL

        # Update player
        self.player.update()
        self.player.emit_flame()

        # Spawn obstacles & coins as their counters tick down
        # (counter is in "world pixels" — decrement by speed each frame)
        self.next_obstacle -= self.speed
        if self.next_obstacle <= 0:
            self._spawn_obstacle()
            # Gap reduces slightly with difficulty
            diff = self.difficulty()
            min_g = max(220, OBSTACLE_MIN_GAP - diff * 25)
            max_g = max(min_g + 80, OBSTACLE_MAX_GAP - diff * 40)
            self.next_obstacle = random.randint(int(min_g), int(max_g))

        self.next_coin -= self.speed
        if self.next_coin <= 0:
            self._spawn_coin_cluster()
            self.next_coin = random.randint(COIN_MIN_GAP, COIN_MAX_GAP)

        # Math gates only when no active gate AND cooldown done
        if not self.gates and self.gate_cooldown <= 0:
            self.next_gate -= self.speed
            if self.next_gate <= 0:
                self._spawn_math_gate()
                self.next_gate = random.randint(GATE_MIN_GAP, GATE_MAX_GAP)
        else:
            self.gate_cooldown -= 1

        # Update obstacles
        for z in self.zappers:
            z.update(self.speed)
        for m in self.missiles:
            m.update(self.speed)
        for sp in self.spikes:
            sp.update(self.speed)
        for c in self.coins:
            c.update(self.speed)
        for g in self.gates:
            g.update(self.speed)

        # Cull dead
        self.zappers  = [z for z in self.zappers  if z.alive]
        self.missiles = [m for m in self.missiles if m.alive]
        self.spikes   = [s for s in self.spikes   if s.alive]
        self.coins    = [c for c in self.coins    if c.alive]
        self.gates    = [g for g in self.gates    if g.alive]

        # ── COLLISIONS ──
        pr = self.player.rect

        # Coins
        for c in self.coins:
            if c.alive and c.rect.colliderect(pr):
                c.alive = False
                self.coin_count += 1
                emit(c.x, c.y, GOLD, n=8, speed=3, life=18, size=3)
                emit_text(c.x, c.y - 10, "+10", GOLD, life=30)
                sfx(SFX_COIN)

        # Math gate detection (player flies through)
        # When player center crosses any gate's x band, lock in answer
        for g in self.gates:
            if g.alive and not g.triggered and g.contains_player(pr):
                g.triggered = True
                g.flash_timer = 30
                if g.is_correct:
                    self.score += GATE_BONUS
                    self.flash(f"+{GATE_BONUS}  CORRECT!", NEON_GREEN, 70)
                    emit_text(g.x, g.y - 60, "CORRECT!", NEON_GREEN)
                    emit(g.x, g.y, NEON_GREEN, n=24, speed=5, life=30, size=4)
                    sfx(SFX_OK)
                    # Disable other gates so the player doesn't keep bouncing around
                    for og in self.gates:
                        if og is not g:
                            og.alive = False
                            og.flash_timer = 0
                else:
                    # Wrong answer: stall jetpack briefly
                    self.player.stall_timer = PENALTY_FRAMES
                    self.flash("WRONG! Jetpack stalled!", NEON_RED, 70)
                    emit_text(g.x, g.y - 60, "WRONG", NEON_RED)
                    emit(g.x, g.y, NEON_RED, n=18, speed=4, life=22)
                    sfx(SFX_BAD)
                # Either way, clear the active question after a moment
                self.gate_cooldown = 60
                self.active_question = ""

        # If all gates flew off without being chosen, also clear question
        if self.gates and all(g.x < -50 for g in self.gates):
            self.active_question = ""

        if not self.gates:
            self.active_question = ""

        # Obstacles → damage / death
        if self.player.alive:
            for z in self.zappers:
                if z.alive and z.collides(pr):
                    if self.player.hurt(fatal=True):
                        self._die()
                        return
            for m in self.missiles:
                if m.alive and m.collides(pr):
                    m.alive = False
                    emit(m.x, m.y, NEON_ORANGE, n=20, speed=5, life=25, size=4)
                    if self.player.hurt(fatal=True):
                        self._die()
                        return
            for sp in self.spikes:
                if sp.alive and sp.collides(pr):
                    if self.player.hurt(fatal=True):
                        self._die()
                        return

        self._tick_p()
        if self.flash_t > 0:
            self.flash_t -= 1

    def _die(self):
        self.state = self.DYING
        self.dying_timer = 60

    def _go_name_entry(self):
        self.state = self.NAME_ENTRY
        self.final_score = self.score
        self.name_input = ""

    def _submit_name(self):
        name = self.name_input.strip() or "ANON"
        self.lb_board, self.lb_is_high = add_to_leaderboard(name, self.final_score)
        self.state = self.LB_SCREEN

    def _tick_p(self):
        for p in g_parts:
            p.update(self.speed if self.state == self.PLAYING else 0)
        g_parts[:] = [p for p in g_parts if p.life > 0]

    # ── EVENTS ──
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
                self.start_run()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.start_run()
            return True

        if self.state == self.NAME_ENTRY:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_RETURN:
                    self._submit_name()
                    sfx(SFX_OK)
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
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.full_reset()
            return True

        if self.state == self.GAME_OVER:
            # Skip to name entry
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                self.show_timer = 0
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.show_timer = 0
            return True

        if self.state == self.PLAYING:
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE:
                self.player.thrust_on = True
            if ev.type == pygame.KEYUP and ev.key == pygame.K_SPACE:
                self.player.thrust_on = False
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.player.thrust_on = True
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self.player.thrust_on = False
        return True

    # ── DRAW ──
    def draw(self):
        screen.fill(BG_DARK)
        if self.state == self.TITLE:
            self._d_title()
        elif self.state in (self.PLAYING, self.DYING, self.GAME_OVER):
            self._d_game()
            if self.state == self.GAME_OVER:
                self._d_overlay_gameover()
        elif self.state == self.NAME_ENTRY:
            self._d_name()
        elif self.state == self.LB_SCREEN:
            self._d_lb()
        pygame.display.flip()

    # ── TITLE SCREEN ──
    def _d_title(self):
        self.bg.draw(screen)
        # Top HUD area dimmed
        hud = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 110))
        screen.blit(hud, (0, 0))

        txt_sh(screen, "MATH JETPACK", FONT_XL, NEON_YELLOW, 60)

        # Decorative jetpack character
        cx, cy = WIDTH // 2, 130
        # Jetpack
        pygame.draw.rect(screen, (60, 70, 90), (cx - 20, cy - 12, 12, 28), border_radius=3)
        pygame.draw.rect(screen, (130, 140, 170), (cx - 19, cy - 10, 10, 3), border_radius=2)
        # Body
        pygame.draw.rect(screen, PLAYER_SUIT, (cx - 10, cy - 8, 20, 24), border_radius=5)
        # Head
        pygame.draw.circle(screen, PLAYER_BODY, (cx, cy - 16), 11)
        pygame.draw.rect(screen, NEON_CYAN, (cx - 7, cy - 18, 14, 6), border_radius=2)
        # Flame
        pygame.draw.polygon(screen, JET_OUTER,
                            [(cx - 16, cy + 16), (cx - 8, cy + 30), (cx, cy + 16)])
        pygame.draw.polygon(screen, JET_MID,
                            [(cx - 14, cy + 16), (cx - 8, cy + 26), (cx - 2, cy + 16)])

        pulse = int(200 + 55 * math.sin(self.frame * 0.06))
        txt_c(screen, "Press SPACE or CLICK to Start", FONT_SM,
              (pulse, pulse, min(255, pulse + 20)), 195)
        txt_c(screen, "Hold SPACE: Jetpack ON  |  Release: Fall",
              FONT_XS, GREY, 218)

        # High score
        if self.high_score > 0:
            txt_c(screen, f"HIGH SCORE: {self.high_score}", FONT_MD, GOLD, 250)

        # Leaderboard
        draw_lb_panel(screen, self.title_lb, WIDTH // 2, 280,
                      title="TOP 10 SCORES", pw=380, rh=22)

    # ── GAMEPLAY ──
    def _d_game(self):
        self.bg.draw(screen)

        # Coins (drawn under player)
        for c in self.coins:
            c.draw(screen)
        # Math gates
        for g in self.gates:
            g.draw(screen)
        # Particles (under player so flame trails behind)
        for p in g_parts:
            if not p.is_text:
                p.draw(screen)
        # Player
        if self.player and self.player.alive:
            self.player.draw(screen)
        # Obstacles in front of player
        for sp in self.spikes:
            sp.draw(screen)
        for z in self.zappers:
            z.draw(screen)
        for m in self.missiles:
            m.draw(screen)
        # Text particles on top
        for p in g_parts:
            if p.is_text:
                p.draw(screen)

        # HUD
        self._d_hud()

        # Flash banner
        if self.flash_t > 0:
            af = min(1.0, self.flash_t / 25)
            c = tuple(int(ch * af) for ch in self.flash_col)
            txt_sh(screen, self.flash_txt, FONT_MD, c, HUD_H + 38)

    def _d_hud(self):
        # Top HUD bar
        pygame.draw.rect(screen, HUD_BG, (0, 0, WIDTH, HUD_H))
        pygame.draw.line(screen, PANEL_BORDER, (0, HUD_H), (WIDTH, HUD_H), 2)

        # Distance (left)
        dt = FONT_HUD.render(f"DIST {int(self.distance)}m", True, NEON_CYAN)
        screen.blit(dt, (12, 8))
        st = FONT_XS.render(f"Score: {self.score}", True, WHITE)
        screen.blit(st, (12, 32))

        # Center: math problem if active, else difficulty/speed indicator
        if self.active_question:
            mt = FONT_MD.render(self.active_question, True, GOLD)
            screen.blit(mt, (WIDTH // 2 - mt.get_width() // 2, 6))
            ht = FONT_XS.render("Fly through the correct answer!", True, NEON_CYAN)
            screen.blit(ht, (WIDTH // 2 - ht.get_width() // 2, 34))
        else:
            diff = self.difficulty()
            stars = "*" * diff + "." * (5 - diff)
            mt = FONT_SM.render(f"Difficulty: {stars}", True, NEON_PINK)
            screen.blit(mt, (WIDTH // 2 - mt.get_width() // 2, 8))
            sp_t = FONT_XS.render(f"Speed: {self.speed:.1f}", True, GREY)
            screen.blit(sp_t, (WIDTH // 2 - sp_t.get_width() // 2, 34))

        # Right: coins
        # Coin icon
        cx_icon = WIDTH - 110
        pygame.draw.ellipse(screen, GOLD, (cx_icon, 12, 16, 16))
        pygame.draw.ellipse(screen, GOLD_HI, (cx_icon + 1, 13, 14, 5))
        ds = FONT_XS.render("$", True, (130, 90, 20))
        screen.blit(ds, (cx_icon + 8 - ds.get_width() // 2,
                         20 - ds.get_height() // 2))
        ct = FONT_HUD.render(f"x {self.coin_count}", True, GOLD)
        screen.blit(ct, (cx_icon + 22, 10))
        # Stall warning
        if self.player and self.player.stall_timer > 0:
            wt = FONT_XS.render("JETPACK STALLED!", True, NEON_RED)
            screen.blit(wt, (WIDTH - wt.get_width() - 10, 36))

    def _d_overlay_gameover(self):
        # Dim overlay
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        screen.blit(ov, (0, 0))
        txt_sh(screen, "GAME OVER", FONT_LG, NEON_RED, 200)
        txt_sh(screen, f"Distance: {int(self.distance)}m", FONT_MD, NEON_CYAN, 260)
        txt_sh(screen, f"Coins: {self.coin_count}  ($"
                       f"{self.coin_count * COIN_VAL})", FONT_MD, GOLD, 295)
        txt_sh(screen, f"Final Score: {self.score}", FONT_MD, WHITE, 330)
        secs = max(1, self.show_timer // 60 + 1)
        txt_c(screen, f"Name entry in {secs}s... (or press SPACE)",
              FONT_XS, GREY, 380)

    # ── NAME ENTRY ──
    def _d_name(self):
        self.bg.draw(screen)
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        screen.blit(ov, (0, 0))

        txt_sh(screen, "GAME OVER", FONT_LG, NEON_RED, 80)
        txt_sh(screen, f"Score: {self.final_score}", FONT_MD, WHITE, 130)
        txt_sh(screen, "Enter Your Name:", FONT_MD, NEON_CYAN, 195)
        bw, bh = 340, 50
        bx = WIDTH // 2 - bw // 2
        by = 220
        pygame.draw.rect(screen, INPUT_BG, (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(screen, PANEL_BORDER, (bx, by, bw, bh), 2, border_radius=8)
        nt = FONT_INPUT.render(self.name_input, True, WHITE)
        tx = bx + 16
        ty = by + bh // 2 - nt.get_height() // 2
        screen.blit(nt, (tx, ty))
        if (self.frame // 30) % 2 == 0:
            cur_x = tx + nt.get_width() + 2
            pygame.draw.rect(screen, CURSOR_COL,
                             (cur_x, ty + 2, 3, nt.get_height() - 4))
        cc = FONT_XS.render(f"{len(self.name_input)}/{self.name_max}", True, GREY)
        screen.blit(cc, (bx + bw - cc.get_width() - 8, by + bh + 5))
        txt_c(screen, "Press ENTER to submit", FONT_SM, GOLD, 320)
        txt_c(screen, "(Leave blank for 'ANON')", FONT_XS, GREY, 345)

    # ── LEADERBOARD ──
    def _d_lb(self):
        self.bg.draw(screen)
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 160))
        screen.blit(ov, (0, 0))

        txt_sh(screen, "FINAL RESULTS", FONT_LG, NEON_CYAN, 50)
        txt_sh(screen, f"Score: {self.final_score}", FONT_MD, WHITE, 95)
        if self.lb_is_high:
            t = self.frame * 0.08
            r = int(200 + 55 * math.sin(t))
            g = int(200 + 55 * math.sin(t + 2))
            b = int(200 + 55 * math.sin(t + 4))
            txt_sh(screen, "NEW HIGH SCORE!", FONT_MD, (r, g, b), 130)
        hl_name = self.name_input.strip() or "ANON"
        draw_lb_panel(screen, self.lb_board, WIDTH // 2, 160,
                      title="TOP 10 SCORES", hl_name=hl_name,
                      hl_score=self.final_score, pw=400, rh=24)
        pulse = int(180 + 60 * math.sin(self.frame * 0.05))
        txt_c(screen, "Press SPACE or CLICK for menu", FONT_SM,
              (pulse, pulse, min(255, pulse)), 510)


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