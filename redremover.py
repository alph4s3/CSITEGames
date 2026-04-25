#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════╗
║  MATH REMOVER — A Physics Puzzle for Sharp Minds                 ║
║                                                                   ║
║  Controls:                                                        ║
║    Left Click on RED block  Trigger a math problem                ║
║    Click an answer button   Pick your answer                      ║
║    R                        Restart current level                  ║
║    N                        Skip to next level (after winning)    ║
║    ESC                      Back to menu / quit                    ║
║                                                                   ║
║  GOAL: Remove all RED blocks. KEEP all GREEN blocks on screen!    ║
║  Solve math problems to remove blocks. Wrong answer = brief lock. ║
╚═══════════════════════════════════════════════════════════════════╝
"""

import pygame
import math
import random
import json
import os
import subprocess
import sys
from typing import List, Tuple, Optional, Dict

# ═══════════════════════════════════════════════════════════════════
#  INITIALIZATION & CONSTANTS
# ═══════════════════════════════════════════════════════════════════
pygame.init()

WIDTH, HEIGHT = 960, 600
HUD_H = 56
PLAY_TOP = HUD_H
PLAY_BOT = HEIGHT
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Math Remover")
clock = pygame.time.Clock()

# ═══════════════════════════════════════════════════════════════════
#  COLORS
# ═══════════════════════════════════════════════════════════════════
BLACK        = (10, 10, 16)
WHITE        = (240, 240, 245)
BG_TOP       = (40, 60, 90)
BG_BOT       = (20, 30, 55)
HUD_BG       = (12, 14, 28)
GROUND_COL   = (60, 50, 90)
GROUND_TOP   = (110, 90, 160)

# Block colors
RED          = (220, 60, 60)
RED_HI       = (255, 110, 110)
RED_DARK     = (160, 30, 30)
DARK_RED     = (130, 30, 30)
DARK_RED_HI  = (180, 60, 60)
GREEN        = (70, 200, 90)
GREEN_HI     = (130, 240, 150)
GREEN_DARK   = (40, 140, 60)
BLUE         = (70, 130, 220)
BLUE_HI      = (120, 170, 255)
BLUE_DARK    = (40, 80, 150)

# UI colors
GOLD         = (255, 210, 50)
GOLD_HI      = (255, 240, 150)
NEON_CYAN    = (80, 220, 240)
NEON_PINK    = (255, 100, 180)
ORANGE       = (255, 150, 40)
PURPLE       = (160, 80, 220)
GREY         = (110, 110, 130)
GREY_DIM     = (60, 60, 80)
GREY_DARK    = (35, 35, 55)
PANEL_BG     = (18, 16, 35)
PANEL_BORDER = (80, 65, 130)
INPUT_BG     = (25, 22, 45)
CURSOR_COL   = (255, 220, 100)
ANSWER_BG    = (40, 50, 90)
ANSWER_HOVER = (70, 90, 150)
ANSWER_BORDER = (180, 180, 220)

# ═══════════════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════════════
FONT_XL     = pygame.font.SysFont("consolas", 56, bold=True)
FONT_LG     = pygame.font.SysFont("consolas", 38, bold=True)
FONT_MD     = pygame.font.SysFont("consolas", 26, bold=True)
FONT_SM     = pygame.font.SysFont("consolas", 19)
FONT_XS     = pygame.font.SysFont("consolas", 15)
FONT_HUD    = pygame.font.SysFont("consolas", 18, bold=True)
FONT_PROB   = pygame.font.SysFont("consolas", 32, bold=True)
FONT_ANS    = pygame.font.SysFont("consolas", 26, bold=True)
FONT_INPUT  = pygame.font.SysFont("consolas", 30, bold=True)
FONT_LB     = pygame.font.SysFont("consolas", 17, bold=True)
FONT_LB_HDR = pygame.font.SysFont("consolas", 20, bold=True)

# ═══════════════════════════════════════════════════════════════════
#  PHYSICS CONSTANTS
# ═══════════════════════════════════════════════════════════════════
GRAVITY        = 0.45
MAX_FALL_SPEED = 14
FRICTION       = 0.85       # horizontal damping when on ground
AIR_FRICTION   = 0.99
RESTITUTION    = 0.15       # bounce factor
MIN_VEL        = 0.05
WRONG_LOCK     = 30         # frames of lock after wrong answer

# Block types
B_RED      = 'red'
B_GREEN    = 'green'
B_BLUE     = 'blue'        # immovable
B_DARK_RED = 'dark_red'    # needs 2 correct answers

# ═══════════════════════════════════════════════════════════════════
#  LEADERBOARD (JSON persistence)
# ═══════════════════════════════════════════════════════════════════
LB_FILE = "leaderboardRR.json"
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


SFX_CLICK = _synth(550, 40, 0.08)
SFX_OK    = _synth(880, 160, 0.13)
SFX_BAD   = _synth(180, 220, 0.12)
SFX_POP   = _synth(700, 100, 0.11)
SFX_LAND  = _synth(120, 80, 0.08)
SFX_WIN   = _synth(1047, 280, 0.13)
SFX_LOSE  = _synth(150, 400, 0.14)
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


# Pre-render gradient background
_bg = pygame.Surface((WIDTH, HEIGHT))
for _y in range(HEIGHT):
    _t = _y / HEIGHT
    _r = int(BG_TOP[0] * (1 - _t) + BG_BOT[0] * _t)
    _g = int(BG_TOP[1] * (1 - _t) + BG_BOT[1] * _t)
    _b = int(BG_TOP[2] * (1 - _t) + BG_BOT[2] * _t)
    pygame.draw.line(_bg, (_r, _g, _b), (0, _y), (WIDTH, _y))
# Star dots
_srng = random.Random(99)
for _ in range(40):
    _sx, _sy = _srng.randint(0, WIDTH), _srng.randint(HUD_H, HEIGHT - 100)
    _br = _srng.randint(50, 110)
    pygame.draw.circle(_bg, (_br, _br, _br + 20), (_sx, _sy), _srng.choice([1, 1, 2]))


# ═══════════════════════════════════════════════════════════════════
#  PARTICLE
# ═══════════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'life', 'max_life',
                 'size', 'is_text', 'text', 'gravity')

    def __init__(self, x, y, vx, vy, color, life=30, size=3, text=None, gravity=0.1):
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


def emit(x, y, color, n=14, speed=4.5, life=28, size=3, gravity=0.1):
    for _ in range(n):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(0.8, speed)
        g_parts.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd - 1.5,
            color, random.randint(life // 2, life),
            random.uniform(size * 0.5, size), gravity=gravity))


def emit_text(x, y, text, color, life=60):
    g_parts.append(Particle(x, y - 10, 0, -1.0, color, life, text=text, gravity=0))


# ═══════════════════════════════════════════════════════════════════
#  BLOCK CLASS — physics-enabled rectangle
# ═══════════════════════════════════════════════════════════════════
class Block:
    """A rectangular block with simple AABB physics."""

    def __init__(self, x, y, w, h, btype):
        self.x = float(x)
        self.y = float(y)
        self.w = float(w)
        self.h = float(h)
        self.vx = 0.0
        self.vy = 0.0
        self.btype = btype
        self.alive = True
        self.on_ground = False
        # State
        self.flash_timer = 0       # red wrong-flash
        self.click_lock = 0        # frames before clickable again
        self.hp = 2 if btype == B_DARK_RED else 1   # dark red needs 2 hits
        # Animation
        self.scale = 1.0           # for spawn / removal animation
        self.removing = False
        self.remove_timer = 0
        # ID for hashing (unique per game)
        self.bobbing_phase = random.uniform(0, math.tau)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.w), int(self.h))

    @property
    def center(self):
        return (self.x + self.w / 2, self.y + self.h / 2)

    @property
    def is_immovable(self):
        return self.btype == B_BLUE

    @property
    def is_clickable(self):
        return self.btype in (B_RED, B_DARK_RED) and self.alive and not self.removing

    def contains_point(self, px, py):
        return (self.x <= px <= self.x + self.w and
                self.y <= py <= self.y + self.h)

    def update(self, all_blocks):
        if self.removing:
            self.remove_timer -= 1
            self.scale = max(0, self.remove_timer / 15)
            if self.remove_timer <= 0:
                self.alive = False
            return

        if self.is_immovable:
            return

        # Apply gravity
        self.vy += GRAVITY
        if self.vy > MAX_FALL_SPEED:
            self.vy = MAX_FALL_SPEED

        # Air friction
        self.vx *= AIR_FRICTION

        # Move horizontally + resolve
        self.x += self.vx
        for other in all_blocks:
            if other is self or not other.alive or other.removing:
                continue
            if self.rect.colliderect(other.rect):
                if self.vx > 0:
                    self.x = other.x - self.w
                elif self.vx < 0:
                    self.x = other.x + other.w
                self.vx = -self.vx * RESTITUTION
                if abs(self.vx) < MIN_VEL:
                    self.vx = 0

        # Move vertically + resolve
        self.y += self.vy
        was_on_ground = self.on_ground
        self.on_ground = False
        for other in all_blocks:
            if other is self or not other.alive or other.removing:
                continue
            if self.rect.colliderect(other.rect):
                if self.vy > 0:
                    self.y = other.y - self.h
                    if self.vy > 2 and not was_on_ground:
                        sfx(SFX_LAND)
                        emit(self.center[0], self.y + self.h, GREY,
                             n=4, speed=2, life=12, size=2, gravity=0.1)
                    self.vy = -self.vy * RESTITUTION
                    if abs(self.vy) < 0.5:
                        self.vy = 0
                    self.on_ground = True
                    self.vx *= FRICTION
                elif self.vy < 0:
                    self.y = other.y + other.h
                    self.vy = -self.vy * RESTITUTION

        # Floor (ground)
        if self.y + self.h > PLAY_BOT - 20:
            self.y = PLAY_BOT - 20 - self.h
            if self.vy > 2 and not was_on_ground:
                sfx(SFX_LAND)
                emit(self.center[0], self.y + self.h, GROUND_TOP,
                     n=6, speed=3, life=15, size=3)
            self.vy = -self.vy * RESTITUTION
            if abs(self.vy) < 0.5:
                self.vy = 0
            self.on_ground = True
            self.vx *= FRICTION

        # Walls
        if self.x < 0:
            self.x = 0
            self.vx = -self.vx * RESTITUTION
        if self.x + self.w > WIDTH:
            self.x = WIDTH - self.w
            self.vx = -self.vx * RESTITUTION

        # Stop tiny vibrations
        if abs(self.vx) < MIN_VEL:
            self.vx = 0

        # Decrement timers
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.click_lock > 0:
            self.click_lock -= 1

    def has_fallen_off(self):
        """Green block fell off the bottom of the world."""
        return self.y > HEIGHT + 50

    def start_remove(self):
        self.removing = True
        self.remove_timer = 15
        cx, cy = self.center
        emit(cx, cy, self._main_color(), n=24, speed=5, life=30, size=4)

    def hit(self):
        """Take a damage hit (for dark red blocks)."""
        self.hp -= 1
        if self.hp <= 0:
            self.start_remove()
            return True
        else:
            # Flash white briefly
            self.flash_timer = 15
            cx, cy = self.center
            emit(cx, cy, WHITE, n=10, speed=3, life=15)
            return False

    def _main_color(self):
        return {B_RED: RED, B_GREEN: GREEN, B_BLUE: BLUE,
                B_DARK_RED: DARK_RED}[self.btype]

    def _hi_color(self):
        return {B_RED: RED_HI, B_GREEN: GREEN_HI, B_BLUE: BLUE_HI,
                B_DARK_RED: DARK_RED_HI}[self.btype]

    def _dark_color(self):
        return {B_RED: RED_DARK, B_GREEN: GREEN_DARK, B_BLUE: BLUE_DARK,
                B_DARK_RED: (80, 20, 20)}[self.btype]

    def draw(self, surf, hovered=False, locked=False):
        if not self.alive:
            return
        # Compute scaled rect for spawn/remove animation
        scale = self.scale
        cx, cy = self.center
        sw = self.w * scale
        sh = self.h * scale
        rx = int(cx - sw / 2)
        ry = int(cy - sh / 2)
        rw = max(1, int(sw))
        rh = max(1, int(sh))

        # Body color (red flash if wrong-clicked)
        if self.flash_timer > 0:
            t = self.flash_timer / 15
            base = self._main_color()
            flash = (255, 255, 255)
            body = tuple(int(base[i] * (1 - t) + flash[i] * t) for i in range(3))
        else:
            body = self._main_color()
        dark = self._dark_color()
        hi = self._hi_color()

        # Shadow
        pygame.draw.rect(surf, (0, 0, 0, 80),
                         (rx + 2, ry + 4, rw, rh), border_radius=4)
        # Main body
        pygame.draw.rect(surf, dark, (rx, ry, rw, rh), border_radius=4)
        pygame.draw.rect(surf, body, (rx + 2, ry + 2, rw - 4, rh - 4), border_radius=3)
        # Highlight stripe (top)
        pygame.draw.rect(surf, hi, (rx + 2, ry + 2, rw - 4, 4), border_radius=2)
        # Highlight stripe (left)
        pygame.draw.rect(surf, hi, (rx + 2, ry + 2, 3, rh - 4), border_radius=2)

        # Special markings
        if self.btype == B_BLUE:
            # Bolts at corners
            for bx, by in [(rx + 6, ry + 6), (rx + rw - 7, ry + 6),
                            (rx + 6, ry + rh - 7), (rx + rw - 7, ry + rh - 7)]:
                pygame.draw.circle(surf, GREY_DARK, (bx, by), 2)
        elif self.btype == B_DARK_RED:
            # HP indicator (1 or 2 dots)
            for i in range(self.hp):
                dot_x = rx + rw // 2 - (self.hp - 1) * 5 + i * 10
                pygame.draw.circle(surf, GOLD, (dot_x, ry + rh // 2), 3)
        elif self.btype == B_RED and not self.removing:
            # Subtle pulse to invite clicking
            pulse = 0.5 + 0.5 * math.sin(self.bobbing_phase + pygame.time.get_ticks() * 0.005)
            r_dot = max(2, int(3 + pulse * 1))
            pygame.draw.circle(surf, RED_HI, (rx + rw // 2, ry + rh // 2), r_dot)
        elif self.btype == B_GREEN:
            # Smile :)
            mid_x = rx + rw // 2
            mid_y = ry + rh // 2
            # Eyes
            pygame.draw.circle(surf, BLACK, (mid_x - 4, mid_y - 2), 1)
            pygame.draw.circle(surf, BLACK, (mid_x + 4, mid_y - 2), 1)
            # Smile arc
            pygame.draw.arc(surf, BLACK, (mid_x - 5, mid_y - 1, 10, 8),
                            math.pi * 1.1, math.pi * 1.9, 1)

        # Hover/lock overlay for clickable red blocks
        if self.is_clickable and not self.removing:
            if locked or self.click_lock > 0:
                # Locked overlay (greyed out)
                lock_s = pygame.Surface((rw, rh), pygame.SRCALPHA)
                lock_s.fill((30, 30, 30, 120))
                surf.blit(lock_s, (rx, ry))
                # Lock icon
                pygame.draw.rect(surf, GOLD,
                                 (rx + rw // 2 - 3, ry + rh // 2, 6, 5))
                pygame.draw.arc(surf, GOLD,
                                (rx + rw // 2 - 4, ry + rh // 2 - 5, 8, 8),
                                0, math.pi, 2)
            elif hovered:
                # Glowing outline
                pygame.draw.rect(surf, NEON_YELLOW := (255, 230, 80),
                                 (rx - 2, ry - 2, rw + 4, rh + 4), 3, border_radius=5)


# ═══════════════════════════════════════════════════════════════════
#  MATH PROBLEM GENERATOR
# ═══════════════════════════════════════════════════════════════════
def gen_problem(difficulty: int):
    """difficulty 1..5; returns (question_str, answer_int)."""
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
#  MATH PROBLEM POPUP — handles displaying & answering
# ═══════════════════════════════════════════════════════════════════
class MathProblem:
    """A modal math problem popup with 4 answer buttons."""

    PANEL_W = 460
    PANEL_H = 280
    BTN_W = 100
    BTN_H = 50

    def __init__(self, difficulty, target_block):
        self.target_block = target_block       # the Block being attacked
        question, answer = gen_problem(difficulty)
        self.question = question + " = ?"
        self.answer = answer
        self.options = gen_wrong(answer, 3, 4 + difficulty * 2)
        self.options.append(answer)
        random.shuffle(self.options)
        self.btn_rects = self._compute_btn_rects()
        self.active = True
        self.result = None      # 'correct', 'wrong', or None
        self.flash_timer = 0
        self.flash_color = WHITE
        self.flash_index = -1   # which button to flash
        self.appear_t = 0       # animation in
        self.dismiss_timer = 0  # frames before closing after answer

    @property
    def panel_rect(self):
        return pygame.Rect(WIDTH // 2 - self.PANEL_W // 2,
                           HEIGHT // 2 - self.PANEL_H // 2,
                           self.PANEL_W, self.PANEL_H)

    def _compute_btn_rects(self):
        pr = pygame.Rect(WIDTH // 2 - self.PANEL_W // 2,
                         HEIGHT // 2 - self.PANEL_H // 2,
                         self.PANEL_W, self.PANEL_H)
        # 2x2 grid of buttons
        gap_x = 20
        gap_y = 16
        total_w = self.BTN_W * 2 + gap_x
        start_x = pr.centerx - total_w // 2
        start_y = pr.y + 150
        rects = []
        for i in range(4):
            row = i // 2
            col = i % 2
            bx = start_x + col * (self.BTN_W + gap_x)
            by = start_y + row * (self.BTN_H + gap_y)
            rects.append(pygame.Rect(bx, by, self.BTN_W, self.BTN_H))
        return rects

    def update(self):
        self.appear_t = min(1.0, self.appear_t + 0.15)
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.dismiss_timer > 0:
            self.dismiss_timer -= 1
            if self.dismiss_timer <= 0:
                self.active = False

    def handle_click(self, mx, my):
        """Returns 'correct', 'wrong', 'cancel', or None."""
        if self.dismiss_timer > 0 or not self.active:
            return None
        # Check button clicks
        for i, r in enumerate(self.btn_rects):
            if r.collidepoint(mx, my):
                chosen = self.options[i]
                self.flash_index = i
                self.flash_timer = 30
                if chosen == self.answer:
                    self.result = 'correct'
                    self.flash_color = GREEN
                    self.dismiss_timer = 30
                    return 'correct'
                else:
                    self.result = 'wrong'
                    self.flash_color = RED
                    self.dismiss_timer = 30
                    return 'wrong'
        # Click outside panel cancels
        if not self.panel_rect.collidepoint(mx, my):
            self.active = False
            return 'cancel'
        return None

    def draw(self, surf, mouse_pos):
        # Dim background
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 130))
        surf.blit(ov, (0, 0))

        # Panel with appear animation (scale)
        scale = self.appear_t
        pw = int(self.PANEL_W * scale)
        ph = int(self.PANEL_H * scale)
        px = WIDTH // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2

        if scale < 0.99:
            # Just draw a scaled rect outline during anim
            pygame.draw.rect(surf, PANEL_BG, (px, py, pw, ph), border_radius=10)
            pygame.draw.rect(surf, PANEL_BORDER, (px, py, pw, ph), 3, border_radius=10)
            return

        pr = self.panel_rect
        # Panel
        pygame.draw.rect(surf, PANEL_BG, pr, border_radius=10)
        pygame.draw.rect(surf, PANEL_BORDER, pr, 3, border_radius=10)
        # Header bar
        hdr = pygame.Rect(pr.x, pr.y, pr.w, 38)
        pygame.draw.rect(surf, GREY_DARK, hdr, border_top_left_radius=10, border_top_right_radius=10)
        ht = FONT_MD.render("MATH CHALLENGE", True, GOLD)
        surf.blit(ht, (pr.centerx - ht.get_width() // 2,
                       pr.y + 19 - ht.get_height() // 2))

        # Question
        qt = FONT_PROB.render(self.question, True, WHITE)
        surf.blit(qt, (pr.centerx - qt.get_width() // 2, pr.y + 70))

        # Answer buttons
        for i, r in enumerate(self.btn_rects):
            opt = self.options[i]
            hover = r.collidepoint(mouse_pos)
            # Determine color
            if self.flash_timer > 0 and i == self.flash_index:
                t = self.flash_timer / 30
                base = self.flash_color
                bg = base
                border = WHITE
            else:
                bg = ANSWER_HOVER if hover else ANSWER_BG
                border = ANSWER_BORDER
            pygame.draw.rect(surf, bg, r, border_radius=6)
            pygame.draw.rect(surf, border, r, 2, border_radius=6)
            opt_t = FONT_ANS.render(str(opt), True, WHITE)
            surf.blit(opt_t, (r.centerx - opt_t.get_width() // 2,
                              r.centery - opt_t.get_height() // 2))

        # Hint footer
        ft = FONT_XS.render("Click an answer (or click outside to cancel)", True, GREY)
        surf.blit(ft, (pr.centerx - ft.get_width() // 2, pr.bottom - 22))


# ═══════════════════════════════════════════════════════════════════
#  LEVEL DEFINITIONS — each is a list of block specs
# ═══════════════════════════════════════════════════════════════════
# Each block: (x, y, w, h, type)
# Coordinates are in the playfield (PLAY_TOP to PLAY_BOT)
# Ground is at y = PLAY_BOT - 20

def _y(from_bot):
    """Helper: y from bottom of playfield."""
    return PLAY_BOT - 20 - from_bot


# Standard block sizes for visual consistency
BS = 50  # standard block size

LEVELS: List[Dict] = [
    # ── LEVEL 1: Tutorial — single red on top of green tower ──
    {
        'name': 'First Steps',
        'difficulty': 1,
        'hint': 'Click the red block to remove it!',
        'blocks': [
            (440, _y(BS), BS, BS, B_RED),
            (440, _y(BS * 2), BS, BS, B_GREEN),
        ],
    },
    # ── LEVEL 2: Two red, one green to protect ──
    {
        'name': 'Double Trouble',
        'difficulty': 1,
        'hint': 'Remove both reds without dropping green!',
        'blocks': [
            (300, _y(BS), BS, BS, B_RED),
            (610, _y(BS), BS, BS, B_RED),
            (455, _y(BS), BS, BS, B_GREEN),
        ],
    },
    # ── LEVEL 3: Stacked — order matters ──
    {
        'name': 'Stack Attack',
        'difficulty': 2,
        'hint': 'Be careful — order matters!',
        'blocks': [
            (200, _y(BS), 80, BS, B_BLUE),
            (200, _y(BS * 2), 80, BS, B_RED),
            (200, _y(BS * 3), 80, BS, B_GREEN),
            (500, _y(BS), BS, BS, B_RED),
            (560, _y(BS), BS, BS, B_RED),
            (530, _y(BS * 2), 50, BS, B_GREEN),
        ],
    },
    # ── LEVEL 4: Bridge of red, green sitting on top ──
    {
        'name': 'Red Bridge',
        'difficulty': 2,
        'hint': 'Reds support a green — careful!',
        'blocks': [
            (250, _y(BS), 60, BS, B_BLUE),
            (650, _y(BS), 60, BS, B_BLUE),
            (310, _y(BS), 100, BS, B_RED),
            (550, _y(BS), 100, BS, B_RED),
            (410, _y(BS), 140, BS, B_RED),
            (440, _y(BS * 2), 80, BS, B_GREEN),
        ],
    },
    # ── LEVEL 5: Tower puzzle ──
    {
        'name': 'Tower of Math',
        'difficulty': 3,
        'hint': 'A green nest at the top of red columns',
        'blocks': [
            # Two columns of red
            (180, _y(BS), 60, BS, B_RED),
            (180, _y(BS * 2), 60, BS, B_RED),
            (180, _y(BS * 3), 60, BS, B_RED),
            (720, _y(BS), 60, BS, B_RED),
            (720, _y(BS * 2), 60, BS, B_RED),
            (720, _y(BS * 3), 60, BS, B_RED),
            # Bridge between them
            (240, _y(BS * 4), 480, 30, B_BLUE),
            # Greens on top
            (350, _y(BS * 4 + 50), 60, 50, B_GREEN),
            (550, _y(BS * 4 + 50), 60, 50, B_GREEN),
            # Center support to sacrifice
            (450, _y(BS), 60, BS * 4, B_RED),
        ],
    },
    # ── LEVEL 6: Dark red blocks introduced ──
    {
        'name': 'Tough Customers',
        'difficulty': 3,
        'hint': 'Dark red blocks need TWO correct answers!',
        'blocks': [
            (200, _y(BS), 70, BS, B_DARK_RED),
            (530, _y(BS), 70, BS, B_DARK_RED),
            (700, _y(BS), 70, BS, B_RED),
            (300, _y(BS), 80, BS, B_BLUE),
            (420, _y(BS), 90, BS, B_RED),
            (350, _y(BS * 2), 50, BS, B_GREEN),
        ],
    },
    # ── LEVEL 7: Pyramid ──
    {
        'name': 'Pyramid Peril',
        'difficulty': 4,
        'hint': 'Greens nestled in a red pyramid',
        'blocks': [
            # Base — 5 reds
            (150, _y(BS), BS, BS, B_RED),
            (210, _y(BS), BS, BS, B_RED),
            (270, _y(BS), BS, BS, B_DARK_RED),
            (330, _y(BS), BS, BS, B_RED),
            (390, _y(BS), BS, BS, B_RED),
            # Row 2 — 4 blocks
            (180, _y(BS * 2), BS, BS, B_RED),
            (240, _y(BS * 2), BS, BS, B_GREEN),
            (300, _y(BS * 2), BS, BS, B_GREEN),
            (360, _y(BS * 2), BS, BS, B_RED),
            # Row 3 — 3 blocks
            (210, _y(BS * 3), BS, BS, B_RED),
            (270, _y(BS * 3), BS, BS, B_DARK_RED),
            (330, _y(BS * 3), BS, BS, B_RED),
            # Right side platform
            (600, _y(BS), 90, BS, B_BLUE),
            (600, _y(BS * 2), 90, BS, B_RED),
            (615, _y(BS * 3), 60, BS, B_GREEN),
            (750, _y(BS), 60, BS, B_RED),
        ],
    },
    # ── LEVEL 8: Final boss — complex puzzle ──
    {
        'name': 'The Final Equation',
        'difficulty': 5,
        'hint': 'A masterwork of dangerous arrangements',
        'blocks': [
            # Left tower
            (60, _y(BS), 70, BS, B_BLUE),
            (60, _y(BS * 2), 70, BS, B_RED),
            (60, _y(BS * 3), 70, BS, B_DARK_RED),
            (60, _y(BS * 4), 70, BS, B_GREEN),
            # Right tower
            (830, _y(BS), 70, BS, B_BLUE),
            (830, _y(BS * 2), 70, BS, B_RED),
            (830, _y(BS * 3), 70, BS, B_DARK_RED),
            (830, _y(BS * 4), 70, BS, B_GREEN),
            # Middle bridge supported by reds
            (200, _y(BS), 60, BS * 2, B_RED),
            (700, _y(BS), 60, BS * 2, B_RED),
            (260, _y(BS * 2), 440, 30, B_BLUE),
            # Stuff on top of the bridge
            (300, _y(BS * 2 + 30), BS, BS, B_RED),
            (370, _y(BS * 2 + 30), BS, BS, B_GREEN),
            (440, _y(BS * 2 + 30), BS, BS, B_DARK_RED),
            (510, _y(BS * 2 + 30), BS, BS, B_GREEN),
            (580, _y(BS * 2 + 30), BS, BS, B_RED),
            # Floor pieces
            (350, _y(BS), 80, BS, B_RED),
            (530, _y(BS), 80, BS, B_RED),
            (440, _y(BS), 90, BS, B_DARK_RED),
        ],
    },
]


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
    rank_colors = [GOLD, (200, 200, 210), ORANGE]
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
#  STAR DRAWING
# ═══════════════════════════════════════════════════════════════════
def draw_star(surf, cx, cy, r, color):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    pygame.draw.polygon(surf, color, pts)
    inner = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = (r * 0.5) if i % 2 == 0 else (r * 0.22)
        inner.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    hi = (min(255, color[0] + 40), min(255, color[1] + 40), min(255, color[2] + 30))
    pygame.draw.polygon(surf, hi, inner)


# ═══════════════════════════════════════════════════════════════════
#  GAME CLASS — full state machine
# ═══════════════════════════════════════════════════════════════════
class Game:
    TITLE      = 0
    LEVEL_INTRO = 1
    PLAYING    = 2
    LEVEL_DONE = 3
    LEVEL_FAIL = 4
    WIN        = 5      # all levels cleared
    NAME_ENTRY = 6
    LB_SCREEN  = 7

    NUM_LEVELS = len(LEVELS)

    def __init__(self):
        self.state = self.TITLE
        self.frame = 0
        self.lvl_idx = 0
        self.blocks: List[Block] = []
        self.problem: Optional[MathProblem] = None
        self.click_lock_global = 0     # global lock after wrong answer
        # Per-level metrics
        self.clicks = 0
        self.correct = 0
        self.wrong = 0
        self.level_score = 0
        # Total
        self.total_score = 0
        # Settle timer (wait for physics to stop after problem dismissed)
        self.settle_timer = 0
        # Animations
        self.intro_t = 0
        self.done_t = 0
        # Flash messages
        self.flash_txt = ""
        self.flash_col = WHITE
        self.flash_t = 0
        # Win/Fail state
        self.show_timer = 0
        # Stars earned this level
        self.stars_earned = 0
        # Level selector
        self.level_select = 0       # cursor on title screen for level select
        self.unlocked = 1            # how many levels unlocked
        # Name entry / leaderboard
        self.name_input = ""
        self.name_max = 12
        self.final_score = 0
        self.lb_board: list = []
        self.lb_is_high = False
        self.title_lb = load_leaderboard()
        # Hover state
        self.hovered_block: Optional[Block] = None
        g_parts.clear()

    def full_reset(self):
        self.__init__()

    def start_level(self, lvl_idx: int):
        self.lvl_idx = lvl_idx
        self.state = self.LEVEL_INTRO
        self.intro_t = 90
        self.blocks.clear()
        self.problem = None
        self.click_lock_global = 0
        self.clicks = 0
        self.correct = 0
        self.wrong = 0
        self.level_score = 0
        self.settle_timer = 0
        self.flash_t = 0
        g_parts.clear()
        # Build blocks from level data
        lv = LEVELS[lvl_idx]
        for x, y, w, h, btype in lv['blocks']:
            self.blocks.append(Block(x, y, w, h, btype))

    def flash(self, txt, col, dur=70):
        self.flash_txt = txt
        self.flash_col = col
        self.flash_t = dur

    # ── Helpers ──
    def _alive_reds(self):
        return [b for b in self.blocks if b.alive and not b.removing
                and b.btype in (B_RED, B_DARK_RED)]

    def _alive_greens(self):
        return [b for b in self.blocks if b.alive and not b.removing
                and b.btype == B_GREEN]

    def _physics_settled(self):
        for b in self.blocks:
            if b.alive and not b.is_immovable and not b.removing:
                if abs(b.vy) > 0.3 or abs(b.vx) > 0.3:
                    return False
        return True

    def _check_level_outcome(self):
        """Check if level is won or failed."""
        # Check fallen greens
        for b in list(self.blocks):
            if b.btype == B_GREEN and b.alive and not b.removing:
                if b.has_fallen_off():
                    b.alive = False
                    self.state = self.LEVEL_FAIL
                    self.show_timer = 180
                    sfx(SFX_LOSE)
                    self.flash("Green block fell!", RED, 100)
                    return
        # Win: no reds left and physics settled and not waiting on problem
        if (not self._alive_reds() and self._physics_settled()
                and (self.problem is None or not self.problem.active)):
            self._win_level()

    def _win_level(self):
        # Compute score
        # Star rating based on min clicks needed (= number of reds in level)
        n_reds_orig = sum(1 for b in LEVELS[self.lvl_idx]['blocks']
                          if b[4] in (B_RED, B_DARK_RED))
        # Add extras for dark reds (each needs 2)
        n_dark = sum(1 for b in LEVELS[self.lvl_idx]['blocks'] if b[4] == B_DARK_RED)
        ideal_clicks = n_reds_orig + n_dark   # dark reds need 2 each
        # Stars: 3 if no wrong, 2 if 1-2 wrong, 1 if more
        if self.wrong == 0:
            self.stars_earned = 3
        elif self.wrong <= 2:
            self.stars_earned = 2
        else:
            self.stars_earned = 1

        # Score: base 500/level, +200 per correct, -50 per wrong, +500 for 3-star bonus
        base = 500 * (self.lvl_idx + 1)
        correct_bonus = 200 * self.correct
        wrong_pen = 50 * self.wrong
        star_bonus = {3: 500, 2: 200, 1: 50}[self.stars_earned]
        # Greens saved bonus
        n_greens_orig = sum(1 for b in LEVELS[self.lvl_idx]['blocks'] if b[4] == B_GREEN)
        n_greens_now = len(self._alive_greens())
        green_bonus = 100 * n_greens_now
        self.level_score = max(0, base + correct_bonus - wrong_pen + star_bonus + green_bonus)
        self.total_score += self.level_score
        # Unlock next level
        self.unlocked = max(self.unlocked, self.lvl_idx + 2)
        self.state = self.LEVEL_DONE
        self.done_t = 200
        sfx(SFX_WIN)

    # ── UPDATE ──
    def update(self):
        self.frame += 1

        if self.state == self.TITLE:
            self._tick_p()
            return

        if self.state == self.LEVEL_INTRO:
            self.intro_t -= 1
            if self.intro_t <= 0:
                self.state = self.PLAYING
            self._tick_p()
            return

        if self.state == self.LEVEL_DONE:
            self.done_t -= 1
            if self.frame % 5 == 0:
                emit(random.randint(200, WIDTH - 200), random.randint(150, 350),
                     random.choice([GOLD, GREEN, NEON_CYAN, NEON_PINK]),
                     n=3, speed=3, life=30, size=4)
            self._tick_p()
            return

        if self.state == self.LEVEL_FAIL:
            self.show_timer -= 1
            self._tick_p()
            return

        if self.state == self.WIN:
            self.show_timer -= 1
            if self.frame % 3 == 0:
                emit(random.randint(150, WIDTH - 150), random.randint(100, 350),
                     random.choice([GOLD, GREEN, NEON_CYAN, NEON_PINK, ORANGE]),
                     n=3, speed=3, life=35, size=4)
            self._tick_p()
            if self.show_timer <= 0:
                self._go_name_entry()
            return

        if self.state in (self.NAME_ENTRY, self.LB_SCREEN):
            self._tick_p()
            return

        if self.state != self.PLAYING:
            return

        # ── PLAYING ──
        if self.click_lock_global > 0:
            self.click_lock_global -= 1

        # Update math problem
        if self.problem and self.problem.active:
            self.problem.update()
            self._tick_p()
            return  # Pause physics during math problem

        if self.problem and not self.problem.active:
            # Problem just dismissed
            self.problem = None

        # Update physics
        for b in self.blocks:
            b.update(self.blocks)

        # Cull dead blocks
        self.blocks = [b for b in self.blocks if b.alive or b.removing]

        # Hover detection
        mx, my = pygame.mouse.get_pos()
        self.hovered_block = None
        for b in self.blocks:
            if b.is_clickable and b.contains_point(mx, my):
                self.hovered_block = b
                break

        # Particles
        self._tick_p()

        # Outcome check
        self._check_level_outcome()

        # Flash timer
        if self.flash_t > 0:
            self.flash_t -= 1

    def _tick_p(self):
        for p in g_parts:
            p.update()
        g_parts[:] = [p for p in g_parts if p.life > 0]

    def _go_name_entry(self):
        self.state = self.NAME_ENTRY
        self.final_score = self.total_score
        self.name_input = ""

    def _submit_name(self):
        name = self.name_input.strip() or "ANON"
        self.lb_board, self.lb_is_high = add_to_leaderboard(name, self.final_score)
        self.state = self.LB_SCREEN

    # ── EVENT HANDLER ──
    def handle(self, ev) -> bool:
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            if self.state in (self.LB_SCREEN, self.NAME_ENTRY,
                               self.LEVEL_DONE, self.LEVEL_FAIL):
                self.full_reset()
                return True
            elif self.state == self.PLAYING:
                self.state = self.TITLE
                return True
            return False

        # ── TITLE ──
        if self.state == self.TITLE:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.total_score = 0
                    self.start_level(self.level_select)
                elif ev.key in (pygame.K_LEFT, pygame.K_a):
                    self.level_select = max(0, self.level_select - 1)
                    sfx(SFX_CLICK)
                elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                    self.level_select = min(self.unlocked - 1, self.level_select + 1)
                    sfx(SFX_CLICK)
            return True

        # ── NAME ENTRY ──
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

        # ── LB SCREEN ──
        if self.state == self.LB_SCREEN:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.full_reset()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.full_reset()
            return True

        # ── LEVEL DONE ──
        if self.state == self.LEVEL_DONE:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_n):
                if self.lvl_idx + 1 >= self.NUM_LEVELS:
                    self.state = self.WIN
                    self.show_timer = 240
                else:
                    self.start_level(self.lvl_idx + 1)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.lvl_idx + 1 >= self.NUM_LEVELS:
                    self.state = self.WIN
                    self.show_timer = 240
                else:
                    self.start_level(self.lvl_idx + 1)
            return True

        # ── LEVEL FAIL ──
        if self.state == self.LEVEL_FAIL:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_r):
                    self.start_level(self.lvl_idx)
                elif ev.key == pygame.K_q:
                    self._go_name_entry()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.start_level(self.lvl_idx)
            return True

        # ── WIN ──
        if self.state == self.WIN:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.show_timer = 0
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.show_timer = 0
            return True

        # ── PLAYING ──
        if self.state == self.PLAYING:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_r:
                    self.start_level(self.lvl_idx)
                    return True
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                # If problem active, route click to problem
                if self.problem and self.problem.active and self.problem.dismiss_timer == 0:
                    res = self.problem.handle_click(mx, my)
                    if res == 'correct':
                        self.correct += 1
                        target = self.problem.target_block
                        sfx(SFX_OK)
                        if target and target.alive and not target.removing:
                            killed = target.hit()
                            if killed:
                                self.flash("CORRECT!", GREEN, 50)
                                emit_text(*target.center, "REMOVED!", GREEN)
                            else:
                                self.flash("HIT! One more time...", GOLD, 50)
                                emit_text(*target.center, "CRACKED!", GOLD)
                    elif res == 'wrong':
                        self.wrong += 1
                        sfx(SFX_BAD)
                        target = self.problem.target_block
                        if target and target.alive:
                            target.flash_timer = 15
                            target.click_lock = WRONG_LOCK
                        self.click_lock_global = 20
                        self.flash("WRONG! Block locked briefly.", RED, 60)
                    return True

                # Otherwise, check if clicked on a clickable block
                if self.click_lock_global > 0:
                    return True
                for b in self.blocks:
                    if b.is_clickable and b.click_lock == 0 and b.contains_point(mx, my):
                        self.clicks += 1
                        sfx(SFX_CLICK)
                        # Spawn math problem
                        diff = LEVELS[self.lvl_idx]['difficulty']
                        self.problem = MathProblem(diff, b)
                        return True
        return True

    # ── DRAW ──
    def draw(self):
        screen.blit(_bg, (0, 0))
        if self.state == self.TITLE:
            self._d_title()
        elif self.state == self.LEVEL_INTRO:
            self._d_intro()
        elif self.state == self.PLAYING:
            self._d_game()
        elif self.state == self.LEVEL_DONE:
            self._d_game()
            self._d_overlay_done()
        elif self.state == self.LEVEL_FAIL:
            self._d_game()
            self._d_overlay_fail()
        elif self.state == self.WIN:
            self._d_overlay_win()
        elif self.state == self.NAME_ENTRY:
            self._d_name()
        elif self.state == self.LB_SCREEN:
            self._d_lb()
        pygame.display.flip()

    # ── TITLE ──
    def _d_title(self):
        txt_sh(screen, "MATH REMOVER", FONT_XL, RED_HI, 70)
        txt_sh(screen, "A Physics Puzzle", FONT_MD, GREY, 115)

        # Animated decorative blocks
        t = self.frame * 0.04
        for i, (col, off) in enumerate([(RED, 0), (GREEN, 1), (RED, 2), (BLUE, 3)]):
            cx = WIDTH // 2 - 90 + i * 60
            cy = 165 + int(math.sin(t + off) * 6)
            pygame.draw.rect(screen, tuple(c // 2 for c in col), (cx - 18, cy - 18, 36, 36),
                             border_radius=4)
            pygame.draw.rect(screen, col, (cx - 16, cy - 16, 32, 32), border_radius=3)

        # Level selector
        sel_y = 225
        txt_c(screen, "LEVEL SELECT", FONT_SM, GOLD, sel_y)

        # Level boxes
        n_show = self.NUM_LEVELS
        box_w = 36
        gap = 8
        total_w = n_show * box_w + (n_show - 1) * gap
        start_x = WIDTH // 2 - total_w // 2
        for i in range(n_show):
            bx = start_x + i * (box_w + gap)
            by = sel_y + 18
            unlocked = i < self.unlocked
            sel = i == self.level_select
            if unlocked:
                col = GOLD if sel else GREEN
                pygame.draw.rect(screen, tuple(c // 3 for c in col),
                                 (bx, by, box_w, box_w), border_radius=4)
                pygame.draw.rect(screen, col, (bx + 2, by + 2, box_w - 4, box_w - 4),
                                 border_radius=3)
                ns = FONT_HUD.render(str(i + 1), True, BLACK)
                screen.blit(ns, (bx + box_w // 2 - ns.get_width() // 2,
                                 by + box_w // 2 - ns.get_height() // 2))
                if sel:
                    pygame.draw.rect(screen, WHITE, (bx - 2, by - 2, box_w + 4, box_w + 4),
                                     2, border_radius=5)
            else:
                pygame.draw.rect(screen, GREY_DARK, (bx, by, box_w, box_w), border_radius=4)
                pygame.draw.rect(screen, GREY_DIM, (bx + 2, by + 2, box_w - 4, box_w - 4),
                                 border_radius=3)
                # Lock icon
                pygame.draw.rect(screen, GREY,
                                 (bx + box_w // 2 - 4, by + box_w // 2, 8, 8))
                pygame.draw.arc(screen, GREY,
                                (bx + box_w // 2 - 5, by + box_w // 2 - 6, 10, 10),
                                0, math.pi, 2)
        # Selected level name
        sel_name = LEVELS[self.level_select]['name']
        txt_c(screen, f"< {sel_name} >", FONT_SM, NEON_CYAN, sel_y + 70)

        # Instructions
        pulse = int(200 + 55 * math.sin(self.frame * 0.06))
        txt_c(screen, "Press SPACE to Play  |  Arrows to select level",
              FONT_XS, (pulse, pulse, min(255, pulse + 20)), 320)

        # Leaderboard
        draw_lb_panel(screen, self.title_lb, WIDTH // 2, 350,
                      title="TOP 10 SCORES", pw=380, rh=20)

    # ── LEVEL INTRO ──
    def _d_intro(self):
        # Show blocks but dim
        self._d_game_world(dim=True)
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 100))
        screen.blit(ov, (0, 0))
        lv = LEVELS[self.lvl_idx]
        txt_sh(screen, f"LEVEL {self.lvl_idx + 1}", FONT_LG, GOLD, 200)
        txt_sh(screen, lv['name'], FONT_MD, WHITE, 250)
        d = lv['difficulty']
        stars = "* " * d + ". " * (5 - d)
        txt_c(screen, f"Difficulty: {stars.strip()}", FONT_SM, ORANGE, 290)
        txt_c(screen, lv['hint'], FONT_SM, NEON_CYAN, 320)
        # Progress bar
        frac = 1.0 - self.intro_t / 90
        bw = 220
        bx = WIDTH // 2 - bw // 2
        pygame.draw.rect(screen, GREY_DIM, (bx, 360, bw, 8), border_radius=4)
        pygame.draw.rect(screen, GOLD, (bx, 360, int(bw * frac), 8), border_radius=4)

    # ── GAMEPLAY ──
    def _d_game(self):
        self._d_game_world()
        self._d_hud()
        # Math problem on top
        if self.problem and self.problem.active:
            self.problem.draw(screen, pygame.mouse.get_pos())
        # Flash banner
        if self.flash_t > 0 and (not self.problem or not self.problem.active):
            af = min(1.0, self.flash_t / 25)
            c = tuple(int(ch * af) for ch in self.flash_col)
            txt_sh(screen, self.flash_txt, FONT_MD, c, HUD_H + 30)

    def _d_game_world(self, dim=False):
        # Ground
        pygame.draw.rect(screen, GROUND_COL, (0, PLAY_BOT - 20, WIDTH, 20))
        pygame.draw.rect(screen, GROUND_TOP, (0, PLAY_BOT - 20, WIDTH, 4))
        # Ground texture
        for gx in range(0, WIDTH, 30):
            pygame.draw.line(screen, GROUND_COL, (gx, PLAY_BOT - 16),
                             (gx + 15, PLAY_BOT - 16), 2)

        # Particles under blocks (e.g. dust)
        for p in g_parts:
            if not p.is_text:
                p.draw(screen)

        # Blocks
        for b in self.blocks:
            hovered = (self.hovered_block is b)
            locked = self.click_lock_global > 0
            b.draw(screen, hovered=hovered, locked=locked)

        # Text particles on top
        for p in g_parts:
            if p.is_text:
                p.draw(screen)

        if dim:
            ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 80))
            screen.blit(ov, (0, 0))

    def _d_hud(self):
        # HUD bar
        pygame.draw.rect(screen, HUD_BG, (0, 0, WIDTH, HUD_H))
        pygame.draw.line(screen, PANEL_BORDER, (0, HUD_H), (WIDTH, HUD_H), 2)

        # Left: level + name
        lv = LEVELS[self.lvl_idx]
        lt = FONT_HUD.render(f"LVL {self.lvl_idx + 1}: {lv['name']}", True, WHITE)
        screen.blit(lt, (12, 8))
        # Reds remaining
        n_reds = len(self._alive_reds())
        rt = FONT_XS.render(f"Reds left: {n_reds}", True, GREY)
        screen.blit(rt, (12, 32))

        # Center: hint or stats
        if self.problem and self.problem.active:
            ht = FONT_SM.render("Solve to remove the block!", True, GOLD)
            screen.blit(ht, (WIDTH // 2 - ht.get_width() // 2, 8))
        else:
            ht = FONT_SM.render("Click RED blocks to attack them",
                                True, NEON_CYAN)
            screen.blit(ht, (WIDTH // 2 - ht.get_width() // 2, 8))
        st = FONT_XS.render(f"Clicks: {self.clicks}   Correct: {self.correct}   "
                             f"Wrong: {self.wrong}", True, GREY)
        screen.blit(st, (WIDTH // 2 - st.get_width() // 2, 32))

        # Right: total score + R hint
        tt = FONT_HUD.render(f"Score: {self.total_score}", True, GOLD)
        screen.blit(tt, (WIDTH - tt.get_width() - 12, 8))
        rt = FONT_XS.render("R: restart", True, GREY)
        screen.blit(rt, (WIDTH - rt.get_width() - 12, 32))

    # ── LEVEL DONE ──
    def _d_overlay_done(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 130))
        screen.blit(ov, (0, 0))
        # Panel
        pw, ph = 480, 320
        px = WIDTH // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2
        pygame.draw.rect(screen, PANEL_BG, (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(screen, PANEL_BORDER, (px, py, pw, ph), 3, border_radius=10)

        txt_sh(screen, "LEVEL COMPLETE!", FONT_LG, GREEN, py + 50)

        # Stars
        for i in range(3):
            sx = WIDTH // 2 - 60 + i * 60
            sy = py + 120
            col = GOLD if i < self.stars_earned else GREY_DIM
            draw_star(screen, sx, sy, 22, col)

        # Stats
        txt_sh(screen, f"Level Score: +{self.level_score}", FONT_MD, GOLD, py + 180)
        txt_sh(screen, f"Total: {self.total_score}", FONT_SM, WHITE, py + 215)
        nm = LEVELS[self.lvl_idx]['name']
        if self.lvl_idx + 1 >= self.NUM_LEVELS:
            txt_c(screen, "All levels complete!", FONT_SM, NEON_CYAN, py + 250)
        else:
            nxt = LEVELS[self.lvl_idx + 1]['name']
            txt_c(screen, f"Next: {nxt}", FONT_SM, NEON_CYAN, py + 250)

        pulse = int(180 + 60 * math.sin(self.frame * 0.06))
        txt_c(screen, "Press SPACE to continue", FONT_SM,
              (pulse, pulse, min(255, pulse + 20)), py + 285)

        # Particles
        for p in g_parts:
            if p.is_text:
                p.draw(screen)

    # ── LEVEL FAIL ──
    def _d_overlay_fail(self):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 130))
        screen.blit(ov, (0, 0))
        pw, ph = 480, 280
        px = WIDTH // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2
        pygame.draw.rect(screen, PANEL_BG, (px, py, pw, ph), border_radius=10)
        pygame.draw.rect(screen, RED_DARK, (px, py, pw, ph), 3, border_radius=10)
        txt_sh(screen, "LEVEL FAILED", FONT_LG, RED, py + 60)
        txt_c(screen, "A green block fell off!", FONT_SM, WHITE, py + 110)
        txt_c(screen, "Try a different approach.", FONT_SM, GREY, py + 140)
        pulse = int(180 + 60 * math.sin(self.frame * 0.06))
        txt_c(screen, "Press R or SPACE to retry", FONT_SM,
              (pulse, pulse, min(255, pulse)), py + 200)
        txt_c(screen, "Press Q to quit and save score",
              FONT_XS, GREY, py + 230)

    # ── FINAL WIN ──
    def _d_overlay_win(self):
        screen.blit(_bg, (0, 0))
        txt_sh(screen, "VICTORY!", FONT_XL, GOLD, 130)
        txt_sh(screen, "All Levels Cleared!", FONT_LG, NEON_CYAN, 200)
        txt_sh(screen, f"Total Score: {self.total_score}", FONT_LG, WHITE, 270)
        # Big stars
        for i in range(5):
            draw_star(screen, WIDTH // 2 - 120 + i * 60, 340, 20, GOLD)
        txt_sh(screen, "Math Master!", FONT_MD, GREEN, 400)
        secs = max(1, self.show_timer // 60 + 1)
        txt_c(screen, f"Name entry in {secs}s... (or press SPACE)",
              FONT_XS, GREY, 460)
        for p in g_parts:
            p.draw(screen)

    # ── NAME ENTRY ──
    def _d_name(self):
        screen.blit(_bg, (0, 0))
        txt_sh(screen, "ENTER YOUR NAME", FONT_LG, GOLD, 100)
        txt_sh(screen, f"Score: {self.final_score}", FONT_MD, WHITE, 160)
        # Input box
        bw, bh = 360, 50
        bx = WIDTH // 2 - bw // 2
        by = 230
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
        txt_c(screen, "(Leave blank for 'ANON')", FONT_XS, GREY, 348)

    # ── LEADERBOARD ──
    def _d_lb(self):
        screen.blit(_bg, (0, 0))
        txt_sh(screen, "FINAL RESULTS", FONT_LG, NEON_CYAN, 60)
        txt_sh(screen, f"Score: {self.final_score}", FONT_MD, WHITE, 110)
        if self.lb_is_high:
            t = self.frame * 0.08
            r = int(200 + 55 * math.sin(t))
            g = int(200 + 55 * math.sin(t + 2))
            b = int(200 + 55 * math.sin(t + 4))
            txt_sh(screen, "NEW HIGH SCORE!", FONT_MD, (r, g, b), 145)
        hl_name = self.name_input.strip() or "ANON"
        draw_lb_panel(screen, self.lb_board, WIDTH // 2, 175,
                      title="TOP 10 SCORES", hl_name=hl_name,
                      hl_score=self.final_score, pw=400, rh=24)
        pulse = int(180 + 60 * math.sin(self.frame * 0.05))
        txt_c(screen, "Press SPACE or CLICK for menu", FONT_SM,
              (pulse, pulse, min(255, pulse)), 555)


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