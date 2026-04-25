#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║  MATH ARCHER — A Puzzle Platformer for Sharp Minds           ║
║                                                               ║
║  Controls:                                                    ║
║    A/D  or  ←/→     Move left / right                        ║
║    SPACE or W or ↑   Jump                                     ║
║    Mouse             Aim bow                                  ║
║    Hold Left Click   Charge & release to shoot arrow          ║
║    R                 Restart current level                     ║
║    ESC               Quit                                     ║
║                                                               ║
║  Shoot the target with the CORRECT answer to score!           ║
╚═══════════════════════════════════════════════════════════════╝
"""

import pygame
import math
import random
import os
import subprocess
import sys
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════
#  INITIALIZATION
# ═══════════════════════════════════════════════════════════════
pygame.init()
WIDTH, HEIGHT = 960, 540
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Math Archer")
clock = pygame.time.Clock()

# ═══════════════════════════════════════════════════════════════
#  COLOR PALETTE — vibrant retro style
# ═══════════════════════════════════════════════════════════════
BLACK       = (10, 10, 18)
WHITE       = (240, 240, 245)
BG_TOP      = (12, 12, 28)
BG_BOT      = (28, 20, 52)
GOLD        = (255, 210, 50)
GOLD_DIM    = (180, 150, 40)
RED         = (230, 55, 65)
RED_DIM     = (160, 40, 45)
GREEN       = (50, 210, 90)
GREEN_DIM   = (35, 150, 65)
BLUE        = (60, 140, 255)
CYAN        = (80, 220, 230)
PURPLE      = (160, 80, 220)
ORANGE      = (255, 150, 40)
PINK        = (255, 100, 150)
SKIN        = (235, 185, 140)
BROWN       = (160, 100, 50)
BROWN_LIGHT = (190, 130, 65)
GREY        = (100, 100, 120)
GREY_DIM    = (60, 60, 75)
PLAT_GREEN  = (45, 160, 75)
PLAT_TOP    = (65, 200, 95)
PLAT_BLUE   = (50, 120, 200)
PLAT_BTOP   = (70, 150, 230)

# ═══════════════════════════════════════════════════════════════
#  FONTS
# ═══════════════════════════════════════════════════════════════
FONT_XL     = pygame.font.SysFont("consolas", 54, bold=True)
FONT_LG     = pygame.font.SysFont("consolas", 38, bold=True)
FONT_MD     = pygame.font.SysFont("consolas", 26, bold=True)
FONT_SM     = pygame.font.SysFont("consolas", 20)
FONT_XS     = pygame.font.SysFont("consolas", 16)
FONT_HUD    = pygame.font.SysFont("consolas", 19, bold=True)
FONT_TARGET = pygame.font.SysFont("consolas", 20, bold=True)

# ═══════════════════════════════════════════════════════════════
#  PHYSICS CONSTANTS
# ═══════════════════════════════════════════════════════════════
GRAVITY         = 0.48
PLAYER_SPEED    = 4.2
JUMP_POWER      = -10.8
ARROW_MIN_SPEED = 8.0
ARROW_MAX_SPEED = 17.0
ARROW_GRAVITY   = 0.28
MAX_ARROWS      = 4

# ═══════════════════════════════════════════════════════════════
#  SIMPLE SOUND GENERATION
# ═══════════════════════════════════════════════════════════════
SOUND_ON = False
try:
    pygame.mixer.init(22050, -16, 1, 256)
    SOUND_ON = True
except Exception:
    pass


def _synth(freq, ms, vol=0.12):
    if not SOUND_ON:
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


SFX_SHOOT   = _synth(650, 55, 0.10)
SFX_HIT_OK  = _synth(880, 160, 0.14)
SFX_HIT_BAD = _synth(180, 220, 0.12)
SFX_JUMP    = _synth(520, 35, 0.07)
SFX_LEVEL   = _synth(1047, 280, 0.13)


def sfx(snd):
    if snd:
        try:
            snd.play()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
#  UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════
def lerp(a, b, t):
    return a + (b - a) * t


def text_center(surf, text, font, color, y, x=None):
    r = font.render(text, True, color)
    cx = (x if x is not None else WIDTH // 2) - r.get_width() // 2
    surf.blit(r, (cx, y - r.get_height() // 2))


def text_shadow(surf, text, font, color, y, x=None):
    sc = tuple(max(0, c // 5) for c in color)
    text_center(surf, text, font, sc, y + 2, x)
    text_center(surf, text, font, color, y, x)


# Pre-render starry background
_bg = pygame.Surface((WIDTH, HEIGHT))
for _y in range(0, HEIGHT, 2):
    _t = _y / HEIGHT
    _r = int(BG_TOP[0] * (1 - _t) + BG_BOT[0] * _t)
    _g = int(BG_TOP[1] * (1 - _t) + BG_BOT[1] * _t)
    _b = int(BG_TOP[2] * (1 - _t) + BG_BOT[2] * _t)
    pygame.draw.line(_bg, (_r, _g, _b), (0, _y), (WIDTH, _y))
_star_rng = random.Random(54321)
for _ in range(50):
    _sx, _sy = _star_rng.randint(0, WIDTH), _star_rng.randint(0, HEIGHT - 80)
    _br = _star_rng.randint(50, 130)
    pygame.draw.circle(_bg, (_br, _br, _br + 20), (_sx, _sy), _star_rng.choice([1, 1, 2]))


# ═══════════════════════════════════════════════════════════════
#  PARTICLE CLASS
# ═══════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'color', 'life', 'max_life',
                 'size', 'is_text', 'text')

    def __init__(self, x, y, vx, vy, color, life=30, size=3, text=None):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.is_text = text is not None
        self.text = text

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not self.is_text:
            self.vy += 0.1
        else:
            self.vy *= 0.96
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


# Global particle list
g_parts: List[Particle] = []


def emit(x, y, color, n=14, speed=4.5, life=28, size=3):
    for _ in range(n):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(0.8, speed)
        g_parts.append(Particle(
            x, y, math.cos(ang) * spd, math.sin(ang) * spd - 1.2,
            color, random.randint(life // 2, life), random.uniform(size * 0.5, size)
        ))


def emit_text(x, y, text, color, life=70):
    g_parts.append(Particle(x, y - 10, 0, -1.0, color, life, text=text))


# ═══════════════════════════════════════════════════════════════
#  PLATFORM CLASS
# ═══════════════════════════════════════════════════════════════
class Platform:
    def __init__(self, x, y, w, h, moving=False, axis='x',
                 move_range=0, move_speed=1.0):
        self.base_x, self.base_y = x, y
        self.w, self.h = w, h
        self.moving = moving
        self.axis = axis
        self.move_range = move_range
        self.move_speed = move_speed
        self.phase = random.uniform(0, math.tau)
        self.rect = pygame.Rect(x, y, w, h)
        self.dx = 0.0

    def update(self):
        if not self.moving:
            self.dx = 0
            return
        old_x = self.rect.x
        self.phase += self.move_speed * 0.025
        if self.axis == 'x':
            self.rect.x = int(self.base_x + math.sin(self.phase) * self.move_range)
        else:
            self.rect.y = int(self.base_y + math.sin(self.phase) * self.move_range)
        self.dx = self.rect.x - old_x

    def draw(self, surf):
        r = self.rect
        if self.moving:
            pygame.draw.rect(surf, PLAT_BLUE, r, border_radius=3)
            pygame.draw.rect(surf, PLAT_BTOP, (r.x, r.y, r.w, 4), border_radius=2)
            # Motion arrows
            cx, cy = r.centerx, r.centery
            for d in [-8, 8]:
                pts = [(cx + d - 3, cy), (cx + d + 3, cy - 3), (cx + d + 3, cy + 3)]
                pygame.draw.polygon(surf, PLAT_BTOP, pts)
        else:
            pygame.draw.rect(surf, PLAT_GREEN, r, border_radius=3)
            pygame.draw.rect(surf, PLAT_TOP, (r.x, r.y, r.w, 4), border_radius=2)
            # Grass tufts
            for gx in range(r.x + 6, r.x + r.w - 6, 14):
                pygame.draw.line(surf, (80, 230, 110), (gx, r.y), (gx - 2, r.y - 5), 1)
                pygame.draw.line(surf, (70, 210, 100), (gx + 3, r.y), (gx + 5, r.y - 4), 1)


# ═══════════════════════════════════════════════════════════════
#  TARGET CLASS
# ═══════════════════════════════════════════════════════════════
class Target:
    def __init__(self, x, y, value, correct=False,
                 moving=False, move_range=0, move_speed=1.0):
        self.ox, self.oy = float(x), float(y)
        self.x, self.y = float(x), float(y)
        self.value = value
        self.correct = correct
        self.radius = 27
        self.alive = True
        self.hit_anim = 0
        self.moving = moving
        self.move_range = move_range
        self.move_speed = move_speed
        self.phase = random.uniform(0, math.tau)
        self.bob = random.uniform(0, math.tau)

    def update(self):
        self.bob += 0.04
        bob_off = math.sin(self.bob) * 3.5
        if self.moving:
            self.phase += self.move_speed * 0.018
            self.x = self.ox + math.sin(self.phase) * self.move_range
        self.y = self.oy + bob_off
        if self.hit_anim > 0:
            self.hit_anim -= 1
            if self.hit_anim <= 0:
                self.alive = False

    def draw(self, surf):
        if not self.alive:
            return
        ix, iy, r = int(self.x), int(self.y), self.radius

        # Glow
        glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        pulse = 0.7 + 0.3 * math.sin(self.bob * 1.5)
        ga = int(35 * pulse)
        if self.hit_anim > 0:
            gc = (50, 255, 120, ga) if self.correct else (255, 60, 60, ga)
        else:
            gc = (255, 230, 80, ga)
        pygame.draw.circle(glow, gc, (r * 5 // 2, r * 5 // 2), int(r * 1.8))
        surf.blit(glow, (ix - r * 5 // 2, iy - r * 5 // 2))

        # Rings
        ring_c = GOLD if self.hit_anim == 0 else (GREEN if self.correct else RED)
        pygame.draw.circle(surf, ring_c, (ix, iy), r, 3)
        pygame.draw.circle(surf, ring_c, (ix, iy), r - 6, 2)
        # Fill
        fill = (35, 30, 50) if self.hit_anim == 0 else (GREEN_DIM if self.correct else RED_DIM)
        pygame.draw.circle(surf, fill, (ix, iy), r - 3)
        # Number
        ts = FONT_TARGET.render(str(self.value), True, WHITE)
        surf.blit(ts, (ix - ts.get_width() // 2, iy - ts.get_height() // 2))

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x) - self.radius, int(self.y) - self.radius,
                           self.radius * 2, self.radius * 2)


# ═══════════════════════════════════════════════════════════════
#  ARROW (PROJECTILE) CLASS
# ═══════════════════════════════════════════════════════════════
class Arrow:
    def __init__(self, x, y, vx, vy, wind=0.0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.wind = wind
        self.alive = True
        self.trail: List[Tuple[float, float]] = []

    def update(self, platforms: List[Platform]):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
        self.vx += self.wind
        self.vy += ARROW_GRAVITY
        self.x += self.vx
        self.y += self.vy
        if self.x < -30 or self.x > WIDTH + 30 or self.y > HEIGHT + 30 or self.y < -60:
            self.alive = False
            return
        ar = pygame.Rect(int(self.x) - 3, int(self.y) - 3, 6, 6)
        for p in platforms:
            if ar.colliderect(p.rect):
                self.alive = False
                emit(self.x, self.y, BROWN_LIGHT, n=5, speed=2, life=14, size=2)
                return

    def draw(self, surf):
        if not self.alive:
            return
        for i, (tx, ty) in enumerate(self.trail):
            a = (i + 1) / max(len(self.trail), 1) * 0.4
            c = (int(200 * a), int(170 * a), int(80 * a))
            pygame.draw.circle(surf, c, (int(tx), int(ty)), 1)
        angle = math.atan2(self.vy, self.vx)
        ln = 20
        ex = self.x - math.cos(angle) * ln
        ey = self.y - math.sin(angle) * ln
        pygame.draw.line(surf, BROWN_LIGHT, (int(ex), int(ey)), (int(self.x), int(self.y)), 2)
        # Fletching
        for da in [0.35, -0.35]:
            fx = ex + math.cos(angle + math.pi + da) * 6
            fy = ey + math.sin(angle + math.pi + da) * 6
            pygame.draw.line(surf, RED_DIM, (int(ex), int(ey)), (int(fx), int(fy)), 1)
        pygame.draw.circle(surf, WHITE, (int(self.x), int(self.y)), 2)

    @property
    def hitbox(self):
        return pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)


# ═══════════════════════════════════════════════════════════════
#  PLAYER CLASS
# ═══════════════════════════════════════════════════════════════
class Player:
    W, H = 22, 36

    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = 0.0, 0.0
        self.on_ground = False
        self.facing = 1
        self.anim_t = 0.0
        self.aim_angle = 0.0
        self.charge = 0.0
        self.charging = False
        self.slow_timer = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.W, self.H)

    @property
    def cx(self):
        return self.x + self.W / 2

    @property
    def cy(self):
        return self.y + self.H / 2 - 4

    def update(self, keys, platforms):
        spd = PLAYER_SPEED * (0.45 if self.slow_timer > 0 else 1.0)
        if self.slow_timer > 0:
            self.slow_timer -= 1

        mv = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            mv -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            mv += 1
        self.vx = mv * spd
        if mv != 0:
            self.facing = mv
            self.anim_t += 0.18
        else:
            self.anim_t = 0

        self.vy += GRAVITY
        self.vy = min(self.vy, 14)

        self.x += self.vx
        self._col_x(platforms)
        self.on_ground = False
        self.y += self.vy
        self._col_y(platforms)

        # Ride moving platforms
        if self.on_ground:
            for p in platforms:
                if p.moving and self.rect.inflate(4, 6).colliderect(p.rect):
                    self.x += p.dx
                    break

        self.x = max(0, min(WIDTH - self.W, self.x))
        if self.y > HEIGHT + 20:
            self.y = HEIGHT - 100
            self.vy = 0

        if self.charging:
            self.charge = min(1.0, self.charge + 0.025)

    def _col_x(self, platforms):
        r = self.rect
        for p in platforms:
            if r.colliderect(p.rect):
                if self.vx > 0:
                    self.x = p.rect.left - self.W
                elif self.vx < 0:
                    self.x = p.rect.right

    def _col_y(self, platforms):
        r = self.rect
        for p in platforms:
            if r.colliderect(p.rect):
                if self.vy > 0:
                    self.y = p.rect.top - self.H
                    self.vy = 0
                    self.on_ground = True
                elif self.vy < 0:
                    self.y = p.rect.bottom
                    self.vy = 0

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_POWER
            self.on_ground = False
            sfx(SFX_JUMP)

    def aim_at(self, mx, my):
        self.aim_angle = math.atan2(my - self.cy, mx - self.cx)

    def shoot(self, wind=0.0):
        if self.charge < 0.08:
            self.charge = 0
            self.charging = False
            return None
        power = lerp(ARROW_MIN_SPEED, ARROW_MAX_SPEED, self.charge)
        vx = math.cos(self.aim_angle) * power
        vy = math.sin(self.aim_angle) * power
        self.charge = 0
        self.charging = False
        sfx(SFX_SHOOT)
        return Arrow(self.cx, self.cy, vx, vy, wind)

    def draw(self, surf, mx, my):
        ix, iy = int(self.x), int(self.y)
        cx_i, cy_i = int(self.cx), int(self.cy)

        # Legs
        la = math.sin(self.anim_t) * 5 if abs(self.vx) > 0.3 else 0
        lf = (ix + 6 + int(la), iy + self.H)
        rf = (ix + self.W - 6 - int(la), iy + self.H)
        pygame.draw.line(surf, RED_DIM, (ix + 7, iy + self.H - 10), lf, 3)
        pygame.draw.line(surf, RED_DIM, (ix + self.W - 7, iy + self.H - 10), rf, 3)
        pygame.draw.circle(surf, BROWN, lf, 3)
        pygame.draw.circle(surf, BROWN, rf, 3)

        # Body
        br = pygame.Rect(ix + 3, iy + 8, self.W - 6, self.H - 18)
        pygame.draw.rect(surf, RED, br, border_radius=5)
        pygame.draw.rect(surf, BROWN, (br.x, br.bottom - 5, br.w, 4))
        pygame.draw.circle(surf, GOLD, (br.centerx, br.bottom - 3), 3)

        # Head
        hx, hy = ix + self.W // 2, iy + 6
        pygame.draw.circle(surf, SKIN, (hx, hy), 8)
        pygame.draw.arc(surf, GREEN_DIM, (hx - 9, hy - 10, 18, 14), 0, math.pi, 3)
        eye_d = 1 if mx > cx_i else -1
        pygame.draw.circle(surf, BLACK, (hx + eye_d * 3, hy - 1), 2)

        # Bow
        ang = self.aim_angle
        bd = 15
        bcx = self.cx + math.cos(ang) * bd
        bcy = self.cy + math.sin(ang) * bd
        arc_pts = []
        for i in range(10):
            a = ang - 0.75 + 1.5 * (i / 9)
            arc_pts.append((int(bcx + math.cos(a) * 12), int(bcy + math.sin(a) * 12)))
        if len(arc_pts) >= 2:
            pygame.draw.lines(surf, BROWN, False, arc_pts, 3)
            pygame.draw.line(surf, (210, 210, 210), arc_pts[0], arc_pts[-1], 1)

        # Charge indicator — arrow nocked on bow
        if self.charging and self.charge > 0.02:
            pb = self.charge * 10
            nx = bcx - math.cos(ang) * pb
            ny = bcy - math.sin(ang) * pb
            tx = bcx + math.cos(ang) * 8
            ty = bcy + math.sin(ang) * 8
            pygame.draw.line(surf, BROWN_LIGHT, (int(nx), int(ny)), (int(tx), int(ty)), 2)
            pygame.draw.circle(surf, WHITE, (int(tx), int(ty)), 2)
            # Charge bar
            bw = int(self.charge * 30)
            bx_bar = ix + self.W // 2 - 15
            by_bar = iy - 10
            pygame.draw.rect(surf, GREY_DIM, (bx_bar, by_bar, 30, 5), border_radius=2)
            bc = GREEN if self.charge < 0.6 else (GOLD if self.charge < 0.9 else RED)
            pygame.draw.rect(surf, bc, (bx_bar, by_bar, bw, 5), border_radius=2)

        # Aim trajectory dots
        power = lerp(ARROW_MIN_SPEED, ARROW_MAX_SPEED, max(self.charge, 0.3))
        avx = math.cos(ang) * power
        avy = math.sin(ang) * power
        for i in range(1, 18):
            t = i * 3
            dx = self.cx + avx * t
            dy = self.cy + avy * t + 0.5 * ARROW_GRAVITY * t * t
            if dx < 0 or dx > WIDTH or dy > HEIGHT:
                break
            alpha = max(30, 160 - i * 9)
            pygame.draw.circle(surf, (alpha, alpha, alpha + 10), (int(dx), int(dy)), max(1, 3 - i // 6))

        # Slow debuff
        if self.slow_timer > 0:
            frac = self.slow_timer / 90
            bx_s = ix - 3
            by_s = iy - 16
            pygame.draw.rect(surf, GREY_DIM, (bx_s, by_s, 28, 4), border_radius=2)
            pygame.draw.rect(surf, PURPLE, (bx_s, by_s, int(28 * frac), 4), border_radius=2)
            st = FONT_XS.render("SLOW", True, PURPLE)
            surf.blit(st, (bx_s, by_s - 13))


# ═══════════════════════════════════════════════════════════════
#  MATH PROBLEM GENERATOR
# ═══════════════════════════════════════════════════════════════
def gen_problem(difficulty: int):
    """Return (question_string, correct_answer_int)."""
    types = {
        1: ['add', 'sub', 'mul', 'fib'],
        2: ['add', 'sub', 'mul', 'div', 'fib'],
        3: ['mul', 'div', 'algebra', 'add', 'fib'],
        4: ['algebra', 'mul', 'div', 'percent', 'algebra', 'fib'],
    }
    kind = random.choice(types.get(difficulty, types[4]))

    if kind == 'add':
        a = random.randint(8 * difficulty, 40 * difficulty)
        b = random.randint(8 * difficulty, 40 * difficulty)
        return f"{a} + {b} = ?", a + b
    elif kind == 'sub':
        a = random.randint(15 * difficulty, 50 * difficulty)
        b = random.randint(3, a - 1)
        return f"{a} - {b} = ?", a - b
    elif kind == 'mul':
        a = random.randint(2, 4 + difficulty * 3)
        b = random.randint(2, 4 + difficulty * 3)
        return f"{a} x {b} = ?", a * b
    elif kind == 'div':
        divisor = random.randint(2, 3 + difficulty * 2)
        answer = random.randint(2, 6 + difficulty * 3)
        dividend = divisor * answer
        return f"{dividend} / {divisor} = ?", answer
    elif kind == 'algebra':
        coeff = random.randint(2, 2 + difficulty)
        x_val = random.randint(1, 4 + difficulty * 2)
        const = random.randint(1, 8 + difficulty * 3)
        rhs = coeff * x_val + const
        return f"Solve: {coeff}x + {const} = {rhs}", x_val
    elif kind == 'percent':
        pct = random.choice([10, 20, 25, 50, 75])
        base = random.choice([40, 60, 80, 100, 120, 200, 400])
        return f"{pct}% of {base} = ?", int(base * pct / 100)
    elif kind == 'fib':
        seq_len = random.randint(4 + difficulty, 6 + difficulty)
        seq = [1, 1]
        while len(seq) < seq_len:
            seq.append(seq[-1] + seq[-2])
        shown = ", ".join(str(v) for v in seq[-4:])
        return f"Next in Fibonacci: {shown}, ?", seq[-1] + seq[-2]
    a, b = random.randint(5, 25), random.randint(5, 25)
    return f"{a} + {b} = ?", a + b


def gen_wrong(correct: int, n: int = 4, spread: int = 8) -> List[int]:
    """Generate n unique wrong answers near the correct value."""
    wrong = set()
    att = 0
    while len(wrong) < n and att < 300:
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


# ═══════════════════════════════════════════════════════════════
#  LEVEL DEFINITIONS
# ═══════════════════════════════════════════════════════════════
def ground():
    return Platform(0, HEIGHT - 28, WIDTH, 28)


LEVELS = [
    {
        'name': 'Green Meadows',
        'difficulty': 1,
        'n_problems': 4,
        'wind': 0.0,
        'moving_targets': False,
        'spawn': (60, HEIGHT - 80),
        'platforms': [
            ground(),
            Platform(120, 420, 150, 14),
            Platform(340, 370, 150, 14),
            Platform(560, 320, 170, 14),
            Platform(780, 400, 140, 14),
            Platform(200, 260, 130, 14),
            Platform(660, 220, 140, 14),
        ],
        'zones': [
            (180, 380), (400, 330), (640, 280),
            (260, 220), (730, 180), (850, 360),
        ],
    },
    {
        'name': 'Shifting Ruins',
        'difficulty': 2,
        'n_problems': 4,
        'wind': 0.0,
        'moving_targets': False,
        'spawn': (50, HEIGHT - 80),
        'platforms': [
            ground(),
            Platform(80, 430, 130, 14),
            Platform(270, 370, 120, 14, moving=True, move_range=70, move_speed=1.3),
            Platform(470, 310, 140, 14),
            Platform(670, 390, 110, 14),
            Platform(350, 220, 130, 14, moving=True, move_range=60, move_speed=1.0),
            Platform(140, 260, 110, 14),
            Platform(800, 260, 120, 14),
        ],
        'zones': [
            (140, 390), (330, 330), (530, 270), (730, 350),
            (210, 220), (420, 180), (870, 220),
        ],
    },
    {
        'name': 'Windy Canyon',
        'difficulty': 3,
        'n_problems': 4,
        'wind': 0.035,
        'moving_targets': True,
        'spawn': (50, HEIGHT - 80),
        'platforms': [
            ground(),
            Platform(50, 420, 110, 14),
            Platform(220, 360, 100, 14, moving=True, move_range=55, move_speed=1.5),
            Platform(420, 300, 120, 14),
            Platform(620, 380, 100, 14, moving=True, axis='y', move_range=40, move_speed=1.2),
            Platform(800, 260, 120, 14),
            Platform(300, 200, 110, 14, moving=True, move_range=65, move_speed=0.9),
            Platform(100, 250, 100, 14),
            Platform(600, 180, 100, 14),
        ],
        'zones': [
            (110, 380), (280, 320), (480, 260), (680, 340),
            (860, 220), (370, 160), (160, 210), (660, 140),
        ],
    },
    {
        'name': 'Storm Summit',
        'difficulty': 4,
        'n_problems': 4,
        'wind': 0.055,
        'moving_targets': True,
        'spawn': (40, HEIGHT - 80),
        'platforms': [
            ground(),
            Platform(30, 440, 90, 14),
            Platform(170, 380, 80, 14, moving=True, move_range=50, move_speed=2.0),
            Platform(340, 320, 90, 14),
            Platform(500, 270, 80, 14, moving=True, move_range=55, move_speed=1.6),
            Platform(660, 360, 80, 14),
            Platform(810, 240, 80, 14, moving=True, move_range=45, move_speed=1.8),
            Platform(200, 230, 90, 14),
            Platform(430, 170, 100, 14, moving=True, move_range=60, move_speed=1.1),
            Platform(680, 160, 80, 14),
        ],
        'zones': [
            (80, 400), (230, 340), (390, 280), (550, 230),
            (720, 320), (870, 200), (260, 190), (490, 130),
            (740, 120),
        ],
    },
]


# ═══════════════════════════════════════════════════════════════
#  SCREEN SHAKE
# ═══════════════════════════════════════════════════════════════
class Shake:
    def __init__(self):
        self.timer = 0
        self.power = 0

    def trigger(self, dur=18, power=7):
        self.timer = dur
        self.power = power

    def offset(self):
        if self.timer <= 0:
            return 0, 0
        self.timer -= 1
        m = self.power * (self.timer / 18)
        return random.randint(int(-m), int(m)), random.randint(int(-m), int(m))


# ═══════════════════════════════════════════════════════════════
#  GAME CLASS — full state machine
# ═══════════════════════════════════════════════════════════════
class Game:
    TITLE       = 0
    INTRO       = 1
    PLAYING     = 2
    LEVEL_DONE  = 3
    OVER        = 4
    WIN         = 5

    def __init__(self):
        self.state = self.TITLE
        self.score = 0
        self.lives = 3
        self.lvl = 0
        self.player: Optional[Player] = None
        self.arrows: List[Arrow] = []
        self.targets: List[Target] = []
        self.question = ""
        self.answer = 0
        self.solved = 0
        self.n_prob = 0
        self.intro_t = 0
        self.done_t = 0
        self.shake = Shake()
        self.flash_txt = ""
        self.flash_col = WHITE
        self.flash_t = 0
        self.frame = 0
        g_parts.clear()

    def reset(self):
        self.__init__()

    def start_level(self):
        lv = LEVELS[self.lvl]
        self.state = self.INTRO
        self.intro_t = 160
        px, py = lv['spawn']
        self.player = Player(px, py)
        self.arrows.clear()
        self.targets.clear()
        self.solved = 0
        self.n_prob = lv['n_problems']
        g_parts.clear()
        self._next_q()

    def _next_q(self):
        lv = LEVELS[self.lvl]
        q, a = gen_problem(lv['difficulty'])
        self.question = q
        self.answer = a
        self.targets.clear()
        zones = list(lv['zones'])
        random.shuffle(zones)
        wrongs = gen_wrong(a, 4, 5 + lv['difficulty'] * 2)
        ci = random.randint(0, 4)
        mt = lv.get('moving_targets', False)
        for i in range(5):
            x, y = zones[i % len(zones)]
            is_c = (i == ci)
            val = a if is_c else wrongs.pop(0)
            mv = mt and random.random() < 0.45
            self.targets.append(Target(
                x, y, val, correct=is_c,
                moving=mv,
                move_range=random.randint(25, 55) if mv else 0,
                move_speed=random.uniform(0.9, 1.6) if mv else 0,
            ))

    def flash(self, txt, col, dur=80):
        self.flash_txt = txt
        self.flash_col = col
        self.flash_t = dur

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
                emit(random.randint(200, WIDTH - 200), random.randint(120, 300),
                     random.choice([GOLD, GREEN, CYAN, PINK]), n=4, speed=3, life=30, size=4)
            for p in g_parts:
                p.update()
            g_parts[:] = [p for p in g_parts if p.life > 0]
            if self.done_t <= 0:
                self.lvl += 1
                if self.lvl >= len(LEVELS):
                    self.state = self.WIN
                else:
                    self.start_level()
            return

        if self.state != self.PLAYING:
            for p in g_parts:
                p.update()
            g_parts[:] = [p for p in g_parts if p.life > 0]
            return

        # ── PLAYING ──
        keys = pygame.key.get_pressed()
        lv = LEVELS[self.lvl]
        for pl in lv['platforms']:
            pl.update()

        self.player.update(keys, lv['platforms'])
        mx, my = pygame.mouse.get_pos()
        self.player.aim_at(mx, my)

        wind = lv.get('wind', 0.0)
        for arr in self.arrows:
            arr.update(lv['platforms'])
            if arr.alive:
                for tgt in self.targets:
                    if tgt.alive and tgt.hit_anim == 0 and arr.hitbox.colliderect(tgt.hitbox):
                        arr.alive = False
                        tgt.hit_anim = 25
                        emit(tgt.x, tgt.y, GOLD, n=20, speed=5, life=30, size=3.5)
                        if tgt.correct:
                            self.score += 100
                            self.solved += 1
                            self.flash("+100", GREEN, 60)
                            emit_text(tgt.x, tgt.y - 20, "CORRECT!", GREEN)
                            sfx(SFX_HIT_OK)
                        else:
                            self.score = max(0, self.score - 20)
                            self.player.slow_timer = 90
                            self.shake.trigger(16, 7)
                            self.flash("-20  WRONG!", RED, 60)
                            emit_text(tgt.x, tgt.y - 20, "WRONG", RED)
                            emit(tgt.x, tgt.y, RED, n=12, speed=4, life=22)
                            sfx(SFX_HIT_BAD)
                            self.lives -= 1
                            if self.lives <= 0:
                                self.state = self.OVER
                                return
                        break
        self.arrows = [a for a in self.arrows if a.alive]

        for t in self.targets:
            t.update()

        ct = [t for t in self.targets if t.correct]
        if ct and not ct[0].alive:
            if self.solved >= self.n_prob:
                self.state = self.LEVEL_DONE
                self.done_t = 170
                bonus = 150 * lv['difficulty']
                self.score += bonus
                self.flash(f"Level bonus +{bonus}", GOLD, 100)
                sfx(SFX_LEVEL)
            else:
                self._next_q()

        for p in g_parts:
            p.update()
        g_parts[:] = [p for p in g_parts if p.life > 0]

        if self.flash_t > 0:
            self.flash_t -= 1

    # ─── EVENTS ──────────────────────────────────────────────
    def handle(self, ev) -> bool:
        if ev.type == pygame.QUIT:
            return False
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            return False

        if ev.type == pygame.KEYDOWN:
            if self.state == self.TITLE:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.start_level()
                return True
            if self.state in (self.OVER, self.WIN):
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.reset()
                return True
            if self.state == self.PLAYING:
                if ev.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self.player.jump()
                if ev.key == pygame.K_r:
                    self.start_level()

        if self.state == self.PLAYING:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.player.charging = True
                self.player.charge = 0
            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.player.charging:
                wind = LEVELS[self.lvl].get('wind', 0.0)
                arr = self.player.shoot(wind)
                if arr:
                    if len(self.arrows) >= MAX_ARROWS:
                        self.arrows.pop(0)
                    self.arrows.append(arr)
        return True

    # ─── DRAW ────────────────────────────────────────────────
    def draw(self):
        screen.blit(_bg, (0, 0))
        sx, sy = self.shake.offset()

        if self.state == self.TITLE:
            self._title()
        elif self.state == self.INTRO:
            self._intro()
        elif self.state == self.PLAYING:
            self._gameplay(sx, sy)
        elif self.state == self.LEVEL_DONE:
            self._lvl_done()
        elif self.state == self.OVER:
            self._gameover()
        elif self.state == self.WIN:
            self._winscreen()

        pygame.display.flip()

    # ── Title screen ──
    def _title(self):
        text_shadow(screen, "MATH ARCHER", FONT_XL, GOLD, 125)

        # Decorative bow
        cx, cy = WIDTH // 2, 210
        prev = None
        for i in range(12):
            a = -0.8 + 1.6 * (i / 11)
            bx = int(cx + math.cos(a - math.pi / 2) * 35)
            by = int(cy + math.sin(a - math.pi / 2) * 35)
            if prev:
                pygame.draw.line(screen, BROWN, prev, (bx, by), 3)
            prev = (bx, by)
        # String
        p0x = int(cx + math.cos(-0.8 - math.pi / 2) * 35)
        p0y = int(cy + math.sin(-0.8 - math.pi / 2) * 35)
        p1x = int(cx + math.cos(0.8 - math.pi / 2) * 35)
        p1y = int(cy + math.sin(0.8 - math.pi / 2) * 35)
        pygame.draw.line(screen, WHITE, (p0x, p0y), (p1x, p1y), 1)
        # Arrow
        pygame.draw.line(screen, BROWN_LIGHT, (cx, cy - 50), (cx, cy - 20), 3)
        pygame.draw.polygon(screen, WHITE, [(cx, cy - 55), (cx - 4, cy - 45), (cx + 4, cy - 45)])

        text_center(screen, "Puzzle Platformer", FONT_MD, GREY, 260)

        info = [
            "A/D or Arrows: Move  |  SPACE: Jump",
            "Hold Left Click: Charge bow  |  Release: Shoot",
            "Hit the target with the correct answer!",
        ]
        for i, ln in enumerate(info):
            text_center(screen, ln, FONT_XS, GREY, 315 + i * 24)

        pulse = int(200 + 55 * math.sin(self.frame * 0.06))
        text_center(screen, "Press ENTER or SPACE to begin", FONT_SM,
                    (pulse, pulse, min(255, pulse + 20)), 425)

    # ── Level intro ──
    def _intro(self):
        lv = LEVELS[self.lvl]
        text_shadow(screen, f"LEVEL {self.lvl + 1}", FONT_LG, GOLD, 175)
        text_shadow(screen, lv['name'], FONT_MD, WHITE, 225)
        stars = "* " * lv['difficulty'] + ". " * (4 - lv['difficulty'])
        text_center(screen, f"Difficulty: {stars.strip()}", FONT_SM, ORANGE, 275)
        text_center(screen, f"Problems: {lv['n_problems']}", FONT_SM, GREY, 305)
        if lv['wind'] > 0:
            text_center(screen, "Wind active — arrows will drift!", FONT_SM, CYAN, 340)
        if lv.get('moving_targets'):
            text_center(screen, "Targets may move!", FONT_SM, PINK, 365)
        # Progress bar
        frac = 1.0 - self.intro_t / 160
        bw = 220
        bx = WIDTH // 2 - bw // 2
        pygame.draw.rect(screen, GREY_DIM, (bx, 415, bw, 8), border_radius=4)
        pygame.draw.rect(screen, GOLD, (bx, 415, int(bw * frac), 8), border_radius=4)

    # ── Gameplay ──
    def _gameplay(self, sx, sy):
        gs = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        gs.blit(_bg, (0, 0))
        lv = LEVELS[self.lvl]
        mx, my = pygame.mouse.get_pos()

        for pl in lv['platforms']:
            pl.draw(gs)
        for tgt in self.targets:
            tgt.draw(gs)
        for arr in self.arrows:
            arr.draw(gs)
        self.player.draw(gs, mx, my)
        for p in g_parts:
            p.draw(gs)

        # Wind indicator
        if lv['wind'] > 0:
            wy = HEIGHT - 18
            for i in range(4):
                wx = WIDTH - 120 + i * 20 + int(math.sin(self.frame * 0.1 + i) * 3)
                ca = 100 + i * 30
                pygame.draw.lines(gs, (ca, ca, 255), False,
                                  [(wx, wy - 4), (wx + 6, wy), (wx, wy + 4)], 2)
            wt = FONT_XS.render("WIND", True, (120, 150, 255))
            gs.blit(wt, (WIDTH - 175, wy - 8))

        screen.blit(gs, (sx, sy))
        self._hud()

    def _hud(self):
        hud = pygame.Surface((WIDTH, 52), pygame.SRCALPHA)
        hud.fill((8, 8, 16, 200))
        screen.blit(hud, (0, 0))

        text_center(screen, self.question, FONT_MD, GOLD, 27)

        st = FONT_HUD.render(f"Score: {self.score}", True, WHITE)
        screen.blit(st, (14, 6))
        lt = FONT_XS.render(f"Lvl {self.lvl + 1}", True, GREY)
        screen.blit(lt, (14, 30))

        pt = FONT_HUD.render(f"{self.solved}/{self.n_prob}", True, WHITE)
        screen.blit(pt, (WIDTH - 55, 6))
        sl = FONT_XS.render("solved", True, GREY)
        screen.blit(sl, (WIDTH - 55, 28))

        for i in range(3):
            hx = WIDTH - 130 + i * 24
            hy = 16
            c = RED if i < self.lives else GREY_DIM
            pygame.draw.circle(screen, c, (hx - 4, hy), 6)
            pygame.draw.circle(screen, c, (hx + 4, hy), 6)
            pygame.draw.polygon(screen, c, [(hx - 10, hy + 2), (hx, hy + 14), (hx + 10, hy + 2)])

        if self.flash_t > 0:
            af = min(1.0, self.flash_t / 20)
            c = tuple(int(ch * af) for ch in self.flash_col)
            text_center(screen, self.flash_txt, FONT_MD, c, 72)

    # ── Level done ──
    def _lvl_done(self):
        text_shadow(screen, "LEVEL COMPLETE!", FONT_LG, GREEN, 180)
        lv = LEVELS[self.lvl]
        text_shadow(screen, f"Bonus: +{150 * lv['difficulty']}", FONT_MD, GOLD, 240)
        text_shadow(screen, f"Score: {self.score}", FONT_MD, WHITE, 280)
        for i in range(self.lives):
            _star(screen, WIDTH // 2 - self.lives * 18 + i * 36 + 18, 340, 14, GOLD)
        for p in g_parts:
            p.draw(screen)

    # ── Game over ──
    def _gameover(self):
        text_shadow(screen, "GAME OVER", FONT_LG, RED, 180)
        text_shadow(screen, f"Final Score: {self.score}", FONT_MD, WHITE, 250)
        lv = LEVELS[min(self.lvl, len(LEVELS) - 1)]
        text_center(screen, f"Reached: Level {self.lvl + 1} - {lv['name']}", FONT_SM, GREY, 300)
        pulse = int(180 + 60 * math.sin(self.frame * 0.05))
        text_center(screen, "Press ENTER or SPACE to retry", FONT_SM,
                    (pulse, pulse, min(255, pulse)), 390)

    # ── Win screen ──
    def _winscreen(self):
        text_shadow(screen, "YOU WIN!", FONT_XL, GOLD, 140)
        text_shadow(screen, f"Final Score: {self.score}", FONT_LG, WHITE, 220)
        for i in range(5):
            _star(screen, WIDTH // 2 - 100 + i * 50, 300, 16, GOLD)
        text_shadow(screen, "Math Master!", FONT_MD, GREEN, 355)
        pulse = int(180 + 60 * math.sin(self.frame * 0.05))
        text_center(screen, "Press ENTER or SPACE to play again", FONT_SM,
                    (pulse, pulse, min(255, pulse)), 420)
        if self.frame % 3 == 0:
            emit(random.randint(150, WIDTH - 150), random.randint(100, 350),
                 random.choice([GOLD, GREEN, CYAN, PINK, ORANGE]), n=3, speed=3, life=35, size=4)
        for p in g_parts:
            p.draw(screen)


def _star(surf, cx, cy, r, color):
    """Draw a 5-pointed star."""
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


# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════
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