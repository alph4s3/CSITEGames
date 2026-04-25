# ============================================================
#  FIBONACCI ADVENTURE – Grow Your Own Magic Spiral
#  A Pygame educational game for high school students
# ============================================================
#
#  HOW TO RUN:
#    1. Install Python: https://python.org
#    2. Install Pygame:  pip install pygame
#    3. Run:             python fibonacci_adventure.py
#
#  CONTROLS:
#    SPACE / Click "Add Next" → add the next Fibonacci number
#    LEFT / RIGHT arrow keys  → change theme
#    Mouse                    → click all buttons
#
#  WHAT STUDENTS LEARN:
#    - The Fibonacci sequence  (1, 1, 2, 3, 5, 8, 13 …)
#    - The golden spiral found in flowers, shells, and galaxies
#    - How programming uses loops, lists, math, and events
# ============================================================

import pygame
import math
import random
import os
import subprocess
import sys

# ── Initialise Pygame ─────────────────────────────────────────
pygame.init()

# ── Window Setup ──────────────────────────────────────────────
SCREEN_W, SCREEN_H = 900, 700
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Fibonacci Adventure – Grow Your Own Magic Spiral")

clock = pygame.time.Clock()
FPS   = 60

# ── Fonts ─────────────────────────────────────────────────────
# We load system fonts so no extra files are needed.
def load_font(size, bold=False):
    """Try to get a nice system font; fall back to pygame default."""
    for name in ["Segoe UI", "Arial Rounded MT Bold", "Verdana", "Arial"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)

FONT_HUGE   = load_font(72, bold=True)
FONT_LARGE  = load_font(42, bold=True)
FONT_MEDIUM = load_font(28, bold=True)
FONT_SMALL  = load_font(20)
FONT_TINY   = load_font(15)

# ── Colours ───────────────────────────────────────────────────
BLACK      = (  0,   0,   0)
WHITE      = (255, 255, 255)
GOLD       = (255, 215,   0)
GOLD_DARK  = (180, 140,   0)
CYAN       = (  0, 220, 255)
PURPLE     = (160,  80, 255)
PINK       = (255, 100, 180)
GREEN      = ( 80, 220, 120)
ORANGE     = (255, 140,  40)
RED        = (255,  80,  80)

# ── Game State Constants ───────────────────────────────────────
# We use a simple string to track which screen is active.
STATE_MENU        = "menu"
STATE_PLAYING     = "playing"
STATE_HOW_TO_PLAY = "howtoplay"
STATE_END         = "end"

# ── Theme Definitions ─────────────────────────────────────────
# Each theme changes the background gradient, spiral colour,
# and particle palette.  To add a new theme: just append a dict!
THEMES = [
    {
        "name":         "🌸 Flower Garden",
        "bg_top":       ( 20,  10,  45),
        "bg_bot":       ( 15,  50,  20),
        "spiral_col":   GOLD,
        "particles":    [( 255, 100, 180), (255, 200,  80),
                         (180, 100, 255), (100, 255, 150)],
        "star_colour":  (255, 220, 240),
    },
    {
        "name":         "🐚 Ocean Shells",
        "bg_top":       (  0,  20,  70),
        "bg_bot":       (  0,  60,  90),
        "spiral_col":   (  0, 220, 255),
        "particles":    [(  0, 180, 255), (  0, 255, 200),
                         (100, 200, 255), (200, 240, 255)],
        "star_colour":  (180, 240, 255),
    },
    {
        "name":         "🌌 Space Galaxy",
        "bg_top":       (  5,   0,  25),
        "bg_bot":       ( 25,   0,  60),
        "spiral_col":   (200, 100, 255),
        "particles":    [(255, 255, 100), (200, 100, 255),
                         (100, 200, 255), (255, 150,  50)],
        "star_colour":  (220, 200, 255),
    },
]

# ============================================================
#  HELPER UTILITIES
# ============================================================

def lerp(a, b, t):
    """Linear interpolation: smooth transition between values a→b."""
    return a + (b - a) * t

def lerp_colour(c1, c2, t):
    """Smoothly blend two RGB colours."""
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def draw_text(surface, text, font, colour, cx, cy, alpha=255):
    """Draw centred text.  If alpha < 255 we blit via a temp surface."""
    rendered = font.render(text, True, colour)
    if alpha < 255:
        rendered.set_alpha(alpha)
    rect = rendered.get_rect(center=(cx, cy))
    surface.blit(rendered, rect)
    return rect

def draw_glow_text(surface, text, font, colour, cx, cy, layers=4, spread=6):
    """Draw text with a soft glow halo."""
    r, g, b = colour
    for i in range(layers, 0, -1):
        alpha  = int(80 * (i / layers))
        size   = spread * i // layers
        glow_s = font.render(text, True, colour)
        # Scale up slightly to simulate blur
        gw = glow_s.get_width()  + size * 2
        gh = glow_s.get_height() + size * 2
        glow_big = pygame.transform.smoothscale(glow_s, (gw, gh))
        glow_big.set_alpha(alpha)
        surface.blit(glow_big, (cx - gw // 2, cy - gh // 2))
    # Crisp top layer
    draw_text(surface, text, font, colour, cx, cy)

def gradient_rect(surface, top_col, bot_col, rect):
    """Fill a rectangle with a vertical gradient."""
    x, y, w, h = rect
    for row in range(h):
        t   = row / max(h - 1, 1)
        col = lerp_colour(top_col, bot_col, t)
        pygame.draw.line(surface, col, (x, y + row), (x + w, y + row))


# ============================================================
#  BUTTON CLASS
# ============================================================

class Button:
    """
    A simple rounded rectangle button with hover + glow effects.

    Usage:
        btn = Button(cx, cy, 200, 50, "Click Me!", (80, 200, 120))
        btn.draw(screen)
        if btn.is_clicked(event):
            ...
    """
    def __init__(self, cx, cy, w, h, label, colour, font=None):
        self.rect   = pygame.Rect(0, 0, w, h)
        self.rect.center = (cx, cy)
        self.label  = label
        self.colour = colour          # (R, G, B) base colour
        self.font   = font or FONT_MEDIUM
        self.hovered = False

    def draw(self, surface):
        mx, my = pygame.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mx, my)

        # Decide colour: brighten on hover
        r, g, b = self.colour
        if self.hovered:
            r = min(r + 50, 255)
            g = min(g + 50, 255)
            b = min(b + 50, 255)
        draw_col = (r, g, b)

        # Shadow
        shadow = self.rect.move(3, 4)
        pygame.draw.rect(surface, (0, 0, 0, 100), shadow, border_radius=14)

        # Button body
        pygame.draw.rect(surface, draw_col, self.rect, border_radius=14)

        # Border glow when hovered
        border_col = WHITE if self.hovered else (r//2, g//2, b//2)
        pygame.draw.rect(surface, border_col, self.rect,
                         width=2, border_radius=14)

        # Label
        draw_text(surface, self.label, self.font, WHITE,
                  self.rect.centerx, self.rect.centery)

        # Pointer cursor
        if self.hovered:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


# ============================================================
#  PARTICLE CLASS
# ============================================================

class Particle:
    """
    A single coloured spark / petal / star that flies out from a point,
    drifts under gravity, and fades away.
    """
    SHAPES = ["circle", "petal", "star", "square"]

    def __init__(self, x, y, colour, speed_range=(2, 6)):
        self.x   = x + random.uniform(-40, 40)
        self.y   = y + random.uniform(-40, 40)
        angle    = random.uniform(0, math.tau)
        speed    = random.uniform(*speed_range)
        self.vx  = math.cos(angle) * speed
        self.vy  = math.sin(angle) * speed - random.uniform(1, 3)
        self.col = colour
        self.life = 1.0                          # 1.0 → fully alive → 0.0 dead
        self.decay = random.uniform(0.012, 0.028)
        self.size  = random.uniform(4, 14)
        self.rot   = random.uniform(0, 360)
        self.rot_v = random.uniform(-5, 5)
        self.shape = random.choice(self.SHAPES)

    @property
    def alive(self):
        return self.life > 0

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.vy  += 0.10   # Gravity
        self.life -= self.decay
        self.rot  += self.rot_v
        self.size  = max(0, self.size * 0.99)

    def draw(self, surface):
        if not self.alive:
            return
        alpha = int(self.life * 255)
        r, g, b = self.col
        colour = (clamp(r,0,255), clamp(g,0,255), clamp(b,0,255))

        # All drawing done on a tiny transparent surface so we can set alpha
        s = int(self.size * 2) + 2
        if s < 2:
            return
        surf = pygame.Surface((s, s), pygame.SRCALPHA)
        c    = s // 2  # Centre of mini-surface

        if self.shape == "circle":
            pygame.draw.circle(surf, (*colour, alpha), (c, c),
                               int(self.size))

        elif self.shape == "petal":
            # Stretched ellipse = simple petal
            r_val = int(self.size)
            rect  = pygame.Rect(c - r_val, c - r_val//2,
                                r_val*2, r_val)
            pygame.draw.ellipse(surf, (*colour, alpha), rect)

        elif self.shape == "square":
            hs = int(self.size * 0.7)
            pygame.draw.rect(surf, (*colour, alpha),
                             (c - hs, c - hs, hs*2, hs*2), border_radius=3)

        else:  # star (4-pointed)
            pts = []
            for i in range(8):
                ang = math.radians(i * 45 + self.rot)
                rad = self.size if i % 2 == 0 else self.size * 0.4
                pts.append((c + math.cos(ang)*rad, c + math.sin(ang)*rad))
            if len(pts) >= 3:
                pygame.draw.polygon(surf, (*colour, alpha), pts)

        surface.blit(surf, (int(self.x) - c, int(self.y) - c))


# ============================================================
#  CONFETTI CLASS  (end-screen celebration)
# ============================================================

class Confetti:
    """Flat rectangular confetti pieces that rain from the top of the screen."""
    COLOURS = [RED, GREEN, GOLD, CYAN, PINK, PURPLE, ORANGE, WHITE]

    def __init__(self):
        self.reset(start=True)

    def reset(self, start=False):
        self.x   = random.uniform(0, SCREEN_W)
        self.y   = random.uniform(-200, 0) if start else -20
        self.vx  = random.uniform(-1.5, 1.5)
        self.vy  = random.uniform(3, 7)
        self.col = random.choice(self.COLOURS)
        self.w   = random.randint(8, 18)
        self.h   = random.randint(4, 9)
        self.rot = random.uniform(0, 360)
        self.rot_v = random.uniform(-4, 4)

    def update(self):
        self.x   += self.vx
        self.y   += self.vy
        self.rot  += self.rot_v
        if self.y > SCREEN_H + 20:
            self.reset()

    def draw(self, surface):
        surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        surf.fill((*self.col, 210))
        rotated = pygame.transform.rotate(surf, self.rot)
        surface.blit(rotated, rotated.get_rect(center=(int(self.x), int(self.y))))


# ============================================================
#  ROBOT CHARACTER
# ============================================================

class Robot:
    """
    A friendly pixel-art-style robot drawn with pygame shapes.
    It blinks, waves its arm, and shows a speech bubble with messages.
    """
    MESSAGES_PLAY = [
        "Hi! I'm Phi-Bot! 🤖",
        "Press SPACE or click!",
        "1 + 1 = 2. Easy right?",
        "Each number = last two added!",
        "That's the Fibonacci sequence!",
        "Nature uses this pattern!",
        "Flowers, shells, galaxies…",
        "You're doing amazing! ✨",
        "Watch the spiral grow!",
        "Almost a math wizard!",
        "φ ≈ 1.618 — the golden ratio!",
        "Nature's perfect blueprint!",
        "You finished! Incredible! 🌀",
    ]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.blink_timer  = 0
        self.wave_angle   = 0
        self.msg_index    = 0
        self.bubble_timer = 0   # Counts frames the current message has shown

    def next_message(self):
        """Advance to the next message in the list."""
        self.msg_index  = min(self.msg_index + 1, len(self.MESSAGES_PLAY) - 1)
        self.bubble_timer = 0

    def update(self):
        self.blink_timer += 1
        self.wave_angle  = math.sin(pygame.time.get_ticks() * 0.003) * 25
        self.bubble_timer += 1

    def draw(self, surface):
        x, y = self.x, self.y
        t    = pygame.time.get_ticks()

        # Blinking: eyes close every ~90 frames for 5 frames
        eyes_closed = (self.blink_timer % 90) < 5

        # ── Legs ──────────────────────────────────────────────
        for dx in (-10, 6):
            pygame.draw.rect(surface, (20, 50, 140), (x + dx, y + 65, 10, 22),
                             border_radius=5)
            # Feet
            pygame.draw.rect(surface, (30, 70, 170), (x + dx - 2, y + 85, 14, 8),
                             border_radius=4)

        # ── Body ──────────────────────────────────────────────
        pygame.draw.rect(surface, (25, 55, 150), (x - 22, y + 25, 44, 42),
                         border_radius=7)
        pygame.draw.rect(surface, (100, 160, 255), (x - 22, y + 25, 44, 42),
                         width=2, border_radius=7)

        # Chest glow orb (pulses)
        pulse = int(140 + math.sin(t * 0.005) * 80)
        pygame.draw.circle(surface, (0, pulse, 255), (x, y + 45), 9)
        pygame.draw.circle(surface, WHITE, (x, y + 45), 5)

        # Belly buttons
        for i, col in enumerate([(70,70,200),(110,70,220),(70,70,200)]):
            pygame.draw.circle(surface, col, (x - 8 + i*8, y + 60), 4)

        # ── Arms ──────────────────────────────────────────────
        # Left arm (static)
        pygame.draw.rect(surface, (25, 55, 150), (x - 34, y + 27, 12, 26),
                         border_radius=6)
        pygame.draw.rect(surface, (100, 160, 255), (x - 34, y + 27, 12, 26),
                         width=1, border_radius=6)

        # Right arm (waves)
        arm_len = 26
        arm_angle_rad = math.radians(-90 + self.wave_angle)
        ax = x + 22 + 6
        ay = y + 35
        ex = ax + math.cos(arm_angle_rad) * arm_len
        ey = ay + math.sin(arm_angle_rad) * arm_len
        pygame.draw.line(surface, (25, 55, 150), (ax, ay), (int(ex), int(ey)), 12)
        pygame.draw.line(surface, (100, 160, 255), (ax, ay), (int(ex), int(ey)), 2)
        # Hand / thumbs-up
        pygame.draw.circle(surface, (255, 220, 160), (int(ex), int(ey)), 7)

        # ── Head ──────────────────────────────────────────────
        pygame.draw.rect(surface, (20, 40, 110), (x - 18, y - 5, 36, 28),
                         border_radius=9)
        pygame.draw.rect(surface, (150, 200, 255), (x - 18, y - 5, 36, 28),
                         width=2, border_radius=9)

        # Eyes
        eye_h = 3 if eyes_closed else 9
        for dx in (-7, 5):
            pygame.draw.rect(surface, (0, 220, 255),
                             (x + dx, y + 3, 8, eye_h), border_radius=2)

        # Mouth / smile
        pygame.draw.arc(surface, (150, 200, 255),
                        (x - 7, y + 12, 14, 8), math.pi, math.tau, 2)

        # ── Antenna ───────────────────────────────────────────
        pygame.draw.line(surface, (150, 200, 255), (x, y - 5), (x, y - 18), 3)
        pulse_a = int(180 + math.sin(t * 0.007) * 60)
        pygame.draw.circle(surface, (255, 215, pulse_a % 255), (x, y - 20), 6)

        # ── Speech Bubble ─────────────────────────────────────
        msg = self.MESSAGES_PLAY[self.msg_index]
        bw  = max(FONT_TINY.size(msg)[0] + 20, 100)
        bh  = 30
        bx  = x - bw - 10
        by  = y - 28

        bubble_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(bubble_surf, (255, 255, 255, 220),
                         (0, 0, bw, bh), border_radius=8)
        pygame.draw.rect(bubble_surf, (200, 200, 255, 180),
                         (0, 0, bw, bh), width=1, border_radius=8)
        surface.blit(bubble_surf, (bx, by))

        # Bubble tail
        pygame.draw.polygon(surface, (255, 255, 255),
                            [(bx + bw - 5, by + bh - 5),
                             (bx + bw + 8, by + bh + 6),
                             (bx + bw - 15, by + bh - 5)])

        txt_surf = FONT_TINY.render(msg, True, (40, 40, 80))
        surface.blit(txt_surf, (bx + 10, by + 8))


# ============================================================
#  SPIRAL RENDERER
# ============================================================

class SpiralRenderer:
    """
    Draws a Fibonacci / golden spiral as a series of quarter-circle arcs.

    How it works:
      - The Fibonacci spiral is approximated by placing squares whose
        side lengths follow the Fibonacci sequence (1,1,2,3,5,8,13…).
      - Each square gets one quarter-circle arc inscribed in it.
      - Animating `drawn_angle` from 0 → total_angle gives the smooth
        growth effect.

    The pivot points for arcs follow a simple repeating 4-step pattern:
        right → up → left → down  (rotating CCW)
    """

    # Pre-computed Fibonacci numbers up to index 20
    FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987,
           1597, 2584, 4181, 6765]

    # Maximum scale so spiral fits nicely in the play area
    MAX_SCALE = 3.2

    def __init__(self, cx, cy):
        self.cx         = cx   # Centre of the spiral on screen
        self.cy         = cy
        self.drawn_angle = 0.0  # How many radians are currently drawn (animated)
        self.target_angle = 0.0# We animate drawn_angle toward this
        self.anim_speed  = 0.06 # Radians per frame (controls growth speed)

    def advance(self):
        """Add one more quarter-circle (π/2 radians) to the target."""
        self.target_angle += math.pi / 2

    def update(self):
        """Smoothly animate drawn_angle toward target_angle."""
        if self.drawn_angle < self.target_angle:
            self.drawn_angle = min(
                self.drawn_angle + self.anim_speed,
                self.target_angle
            )

    @property
    def is_animating(self):
        return self.drawn_angle < self.target_angle

    def draw(self, surface, colour):
        """
        Render the spiral up to `drawn_angle` radians.
        colour: (R, G, B) tuple
        """
        self._render(surface, colour, self.drawn_angle)

    def _render(self, surface, colour, angle_limit):
        """Core rendering loop."""
        if angle_limit <= 0:
            return

        # Dynamic scale: shrink as more arcs appear so it always fits
        n_arcs      = int(angle_limit / (math.pi / 2)) + 2
        total_size  = self.FIB[min(n_arcs, len(self.FIB) - 1)]
        scale       = min(self.MAX_SCALE, 200 / max(total_size, 1))

        # Starting pivot and arc direction
        px, py    = 0.0, 0.0  # Relative to spiral centre
        start_ang = math.pi   # Initial arc start angle (in pygame convention)
        # pygame arc angles: 0 = 3 o'clock, going COUNTER-clockwise

        remaining  = angle_limit

        for i, fib in enumerate(self.FIB):
            if remaining <= 0:
                break

            r        = fib * scale  # Radius of this arc
            arc_size = min(math.pi / 2, remaining)

            # Convert to screen coordinates
            sx = self.cx + px - r
            sy = self.cy + py - r

            rect = pygame.Rect(int(sx), int(sy), int(r * 2), int(r * 2))

            # Draw glow layers (drawn from widest/most transparent → thinnest)
            cr, cg, cb = colour
            for gw in range(6, 0, -2):
                alpha = 40 * (gw // 2)
                glow_col = (
                    clamp(cr, 0, 255),
                    clamp(cg, 0, 255),
                    clamp(cb, 0, 255)
                )
                # We can't set alpha on draw_arc directly, so we approximate
                # by drawing with a lighter colour
                blend = lerp_colour(glow_col, (0, 0, 0), 1 - alpha / 255)
                # Actually just draw with reduced RGB → looks close enough
                glow_surf_col = (
                    clamp(cr * alpha // 255, 0, 255),
                    clamp(cg * alpha // 255, 0, 255),
                    clamp(cb * alpha // 255, 0, 255),
                )
                inflated = rect.inflate(gw * 2, gw * 2)
                pygame.draw.arc(surface, glow_surf_col,
                                inflated,
                                start_ang, start_ang + arc_size,
                                width=gw + 2)

            # Main spiral arc
            pygame.draw.arc(surface, colour, rect,
                            start_ang, start_ang + arc_size, width=3)

            # Advance pivot point following the 4-direction cycle
            step = i % 4
            if   step == 0: px += fib * scale
            elif step == 1: py += fib * scale
            elif step == 2: px -= fib * scale
            elif step == 3: py -= fib * scale

            start_ang  += math.pi / 2
            remaining  -= math.pi / 2

        # Golden centre dot
        pygame.draw.circle(surface, colour, (int(self.cx), int(self.cy)), 6)
        pygame.draw.circle(surface, WHITE,  (int(self.cx), int(self.cy)), 3)


# ============================================================
#  FLOATING NUMBER DECORATION
# ============================================================

class FloatingNumber:
    """
    A decorative Fibonacci number that drifts slowly across the background.
    """
    FIB_NUMS = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]

    def __init__(self):
        self.reset(initial=True)

    def reset(self, initial=False):
        self.x     = random.uniform(0, SCREEN_W)
        self.y     = random.uniform(0, SCREEN_H) if initial else SCREEN_H + 20
        self.vy    = random.uniform(-0.5, -1.2)
        self.vx    = random.uniform(-0.3, 0.3)
        self.n     = random.choice(self.FIB_NUMS)
        self.alpha = random.randint(30, 90)
        self.size  = random.randint(14, 30)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.y < -30:
            self.reset()

    def draw(self, surface, colour):
        r, g, b = colour
        surf = FONT_SMALL.render(str(self.n), True, (r, g, b))
        surf.set_alpha(self.alpha)
        surface.blit(surf, (int(self.x), int(self.y)))


# ============================================================
#  BACKGROUND STARS / BUBBLES
# ============================================================

class BackgroundDot:
    """Tiny twinkling dots that vary per theme (stars, bubbles, sparkles)."""
    def __init__(self):
        self.x     = random.randint(0, SCREEN_W)
        self.y     = random.randint(0, SCREEN_H)
        self.base_alpha = random.randint(40, 160)
        self.alpha = self.base_alpha
        self.size  = random.uniform(1, 3.5)
        self.phase = random.uniform(0, math.tau)  # For twinkle offset

    def update(self, t):
        # Twinkle: alpha oscillates
        self.alpha = int(self.base_alpha +
                         math.sin(t * 0.003 + self.phase) * 40)
        self.alpha = clamp(self.alpha, 10, 255)

    def draw(self, surface, colour):
        r, g, b = colour
        surf = pygame.Surface((int(self.size*2)+2, int(self.size*2)+2),
                              pygame.SRCALPHA)
        pygame.draw.circle(surf, (r, g, b, self.alpha),
                           (int(self.size)+1, int(self.size)+1),
                           int(self.size))
        surface.blit(surf, (int(self.x - self.size), int(self.y - self.size)))


# ============================================================
#  MAIN GAME CLASS
# ============================================================

class FibonacciAdventure:
    """
    Master controller for the entire game.

    State machine:
        STATE_MENU  →  STATE_PLAYING  →  STATE_END
                   ↑                          ↓
                   └──────────────────────────┘
    """

    MAX_FIB_TERMS  = 13   # How many terms before end screen

    def __init__(self):
        # ── Theme & visual state ──────────────────────────────
        self.theme_index    = 0

        # ── Game logic ────────────────────────────────────────
        self.fib_sequence   = []      # Builds up as player clicks
        self.state          = STATE_MENU

        # ── Spiral ───────────────────────────────────────────
        spiral_cx = SCREEN_W // 2
        spiral_cy = SCREEN_H // 2 + 10
        self.spiral = SpiralRenderer(spiral_cx, spiral_cy)

        # ── Robot ────────────────────────────────────────────
        self.robot = Robot(SCREEN_W - 95, SCREEN_H - 200)

        # ── Background decoration ────────────────────────────
        self.bg_dots   = [BackgroundDot() for _ in range(80)]
        self.floaters  = [FloatingNumber() for _ in range(12)]

        # ── Particles ────────────────────────────────────────
        self.particles = []

        # ── Confetti (end screen only) ────────────────────────
        self.confetti  = []

        # ── Phi (φ) rotation for menu ─────────────────────────
        self.phi_angle = 0.0

        # ── Build all buttons ─────────────────────────────────
        self._build_buttons()

        # ── Seed with first two Fibonacci numbers at start ────
        # (We add them when the player enters STATE_PLAYING)

    # ── Button setup ──────────────────────────────────────────

    def _build_buttons(self):
        """Create all Button objects.  Called once in __init__."""
        cx = SCREEN_W // 2

        # Menu buttons
        self.btn_start  = Button(cx, 360, 260, 55, "▶  Start Adventure",
                                 (60, 180, 100))
        self.btn_howto  = Button(cx, 430, 260, 55, "❓  How to Play",
                                 (60, 100, 200))
        self.btn_quit   = Button(cx, 500, 260, 55, "✕   Quit",
                                 (180, 60, 60))

        # Gameplay buttons
        self.btn_add    = Button(cx, SCREEN_H - 55, 240, 50,
                                 "➕  Add Next  [SPACE]",
                                 (200, 160, 0))
        self.btn_prev_t = Button(60, SCREEN_H - 55, 100, 40, "◀ Theme",
                                 (80, 60, 180), font=FONT_SMALL)
        self.btn_next_t = Button(SCREEN_W - 60, SCREEN_H - 55, 100, 40,
                                 "Theme ▶", (80, 60, 180), font=FONT_SMALL)

        # End-screen buttons
        self.btn_again  = Button(cx - 130, SCREEN_H - 70, 220, 50,
                                 "🔄  Play Again", (60, 180, 100))
        self.btn_menu   = Button(cx + 130, SCREEN_H - 70, 220, 50,
                                 "🏠  Main Menu", (60, 100, 200))

        # How-to-play back button
        self.btn_back   = Button(cx, SCREEN_H - 60, 200, 48,
                                 "← Back", (80, 80, 160))

    # ── State transitions ─────────────────────────────────────

    def start_game(self):
        """Reset all game data and enter STATE_PLAYING."""
        self.fib_sequence     = [1, 1]
        self.spiral           = SpiralRenderer(SCREEN_W // 2, SCREEN_H // 2 + 10)
        self.spiral.drawn_angle = math.pi / 2
        self.spiral.target_angle = math.pi / 2
        self.particles        = []
        self.robot.msg_index  = 2
        self.robot.blink_timer = 0
        self.state            = STATE_PLAYING

    def go_to_end(self):
        """Transition to the end/celebration screen."""
        self.state    = STATE_END
        self.confetti = [Confetti() for _ in range(140)]

    def go_to_menu(self):
        self.state     = STATE_MENU
        self.confetti  = []
        self.particles = []

    # ── Game logic: add next Fibonacci number ─────────────────

    def add_next_fib(self):
        """
        Compute and add the next term.
        Trigger: player presses SPACE or clicks Add button.
        """
        if self.spiral.is_animating:
            return   # Don't allow spamming while spiral is growing
        if len(self.fib_sequence) >= self.MAX_FIB_TERMS:
            return

        a, b = self.fib_sequence[-2], self.fib_sequence[-1]
        self.fib_sequence.append(a + b)
        self.spiral.advance()
        self.robot.next_message()

        # Spawn a burst of particles at the spiral centre
        theme      = THEMES[self.theme_index]
        n_particles = 35
        for _ in range(n_particles):
            col = random.choice(theme["particles"])
            self.particles.append(
                Particle(self.spiral.cx, self.spiral.cy, col)
            )

        # End condition
        if len(self.fib_sequence) >= self.MAX_FIB_TERMS:
            # Let the animation finish before switching screens
            pygame.time.set_timer(pygame.USEREVENT, 1200, loops=1)

    # ── Theme cycling ─────────────────────────────────────────

    def next_theme(self):
        self.theme_index = (self.theme_index + 1) % len(THEMES)

    def prev_theme(self):
        self.theme_index = (self.theme_index - 1) % len(THEMES)

    # ── Main loop ─────────────────────────────────────────────

    def _return_to_launcher(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        launcher = os.path.join(base_dir, "start_page.py")
        if os.path.exists(launcher):
            subprocess.Popen([sys.executable, launcher], cwd=base_dir)
        pygame.quit()
        sys.exit()

    def _draw_menu_button(self, rect):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = (32, 75, 155) if not hovered else (57, 112, 205)
        pygame.draw.rect(screen, fill, rect, border_radius=8)
        pygame.draw.rect(screen, (210, 235, 255), rect, width=2, border_radius=8)
        txt = FONT_SMALL.render("Menu", True, (245, 245, 245))
        screen.blit(txt, txt.get_rect(center=rect.center))

    def run(self):
        """The main game loop — runs at FPS until the window is closed."""
        menu_btn = pygame.Rect(SCREEN_W - 122, 10, 110, 34)
        running = True
        while running:
            t = pygame.time.get_ticks()

            # ── Event handling ────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if menu_btn.collidepoint(event.pos):
                        self._return_to_launcher()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_0:
                    self._return_to_launcher()

                # Custom timer event → switch to end screen
                if event.type == pygame.USEREVENT:
                    self.go_to_end()

                # Reset hand cursor every frame; buttons set it if hovered
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

                if self.state == STATE_MENU:
                    self._handle_menu(event)
                elif self.state == STATE_PLAYING:
                    self._handle_play(event)
                elif self.state == STATE_END:
                    self._handle_end(event)
                elif self.state == STATE_HOW_TO_PLAY:
                    self._handle_howto(event)

            # ── Update ────────────────────────────────────────
            self._update(t)

            # ── Draw ──────────────────────────────────────────
            self._draw(t)
            self._draw_menu_button(menu_btn)

            pygame.display.flip()
            clock.tick(FPS)

        pygame.quit()
        sys.exit()

    # ── Event handlers per state ──────────────────────────────

    def _handle_menu(self, event):
        if self.btn_start.is_clicked(event): self.start_game()
        if self.btn_howto.is_clicked(event): self.state = STATE_HOW_TO_PLAY
        if self.btn_quit.is_clicked(event):  pygame.quit(); sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN: self.start_game()
            if event.key == pygame.K_q:      pygame.quit(); sys.exit()

    def _handle_play(self, event):
        if self.btn_add.is_clicked(event):    self.add_next_fib()
        if self.btn_next_t.is_clicked(event): self.next_theme()
        if self.btn_prev_t.is_clicked(event): self.prev_theme()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:      self.add_next_fib()
            if event.key == pygame.K_RIGHT:      self.next_theme()
            if event.key == pygame.K_LEFT:       self.prev_theme()
            if event.key == pygame.K_ESCAPE:     self.go_to_menu()

    def _handle_end(self, event):
        if self.btn_again.is_clicked(event): self.start_game()
        if self.btn_menu.is_clicked(event):  self.go_to_menu()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:  self.start_game()
            if event.key == pygame.K_ESCAPE: self.go_to_menu()

    def _handle_howto(self, event):
        if self.btn_back.is_clicked(event): self.go_to_menu()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.go_to_menu()

    # ── Update ────────────────────────────────────────────────

    def _update(self, t):
        # Background decorations — always active
        for dot in self.bg_dots:
            dot.update(t)
        for fl in self.floaters:
            fl.update()

        self.phi_angle += 0.008

        if self.state == STATE_PLAYING:
            self.spiral.update()
            self.robot.update()
            # Update & cull dead particles
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.alive]

        if self.state == STATE_END:
            for c in self.confetti:
                c.update()
            self.robot.update()

    # ── Draw dispatcher ───────────────────────────────────────

    def _draw(self, t):
        theme = THEMES[self.theme_index]

        # Gradient background (covers full screen every frame)
        gradient_rect(screen, theme["bg_top"], theme["bg_bot"],
                      (0, 0, SCREEN_W, SCREEN_H))

        # Twinkling dots on top of background
        for dot in self.bg_dots:
            dot.draw(screen, theme["star_colour"])

        # Floating Fibonacci numbers
        for fl in self.floaters:
            fl.draw(screen, GOLD)

        # Route to the correct screen renderer
        if self.state == STATE_MENU:
            self._draw_menu(t, theme)
        elif self.state == STATE_PLAYING:
            self._draw_play(t, theme)
        elif self.state == STATE_END:
            self._draw_end(t, theme)
        elif self.state == STATE_HOW_TO_PLAY:
            self._draw_howto(t)

    # ── MENU SCREEN ───────────────────────────────────────────

    def _draw_menu(self, t, theme):
        cx = SCREEN_W // 2

        # Faint background spiral preview
        self.spiral.draw(screen, (*theme["spiral_col"], 100))

        # φ rotating symbol
        phi_surf = FONT_HUGE.render("φ", True, (*GOLD, 160))
        phi_surf.set_alpha(120)
        phi_rot  = pygame.transform.rotate(phi_surf, math.degrees(self.phi_angle))
        screen.blit(phi_rot, phi_rot.get_rect(center=(cx, 280)))

        # Title
        draw_glow_text(screen, "FIBONACCI", FONT_HUGE, GOLD, cx, 130,
                       layers=5, spread=8)
        draw_glow_text(screen, "ADVENTURE", FONT_HUGE, GOLD, cx, 210,
                       layers=5, spread=8)

        # Subtitle
        draw_text(screen, "Grow Your Own Magic Spiral! 🌀",
                  FONT_MEDIUM, (200, 240, 255), cx, 268)

        # Buttons
        self.btn_start.draw(screen)
        self.btn_howto.draw(screen)
        self.btn_quit.draw(screen)

        # Footer
        draw_text(screen, "← / → arrow keys change theme | SPACE = add number",
                  FONT_TINY, (140, 160, 200), cx, SCREEN_H - 20)

        # Robot on the side
        self.robot.msg_index = 0
        self.robot.draw(screen)

        # Theme name
        draw_text(screen, theme["name"], FONT_SMALL,
                  (180, 200, 255), cx, SCREEN_H - 40)

    # ── PLAY SCREEN ───────────────────────────────────────────

    def _draw_play(self, t, theme):
        cx = SCREEN_W // 2

        # ── Spiral ───────────────────────────────────────────
        self.spiral.draw(screen, theme["spiral_col"])

        # ── Particles ─────────────────────────────────────────
        for p in self.particles:
            p.draw(screen)

        # ── Top: Sequence display ─────────────────────────────
        self._draw_sequence_bar(theme)

        # ── Theme name ────────────────────────────────────────
        draw_text(screen, theme["name"], FONT_SMALL, (180, 200, 255),
                  cx, SCREEN_H - 90)

        # ── Golden ratio approximation ────────────────────────
        if len(self.fib_sequence) >= 3:
            a = self.fib_sequence[-2]
            b = self.fib_sequence[-1]
            ratio = b / a
            ratio_str = f"φ ratio: {b}/{a} ≈ {ratio:.4f}"
            draw_text(screen, ratio_str, FONT_SMALL, GOLD, cx, SCREEN_H - 108)

        # ── Buttons ───────────────────────────────────────────
        if not self.spiral.is_animating:
            self.btn_add.draw(screen)
        else:
            draw_text(screen, "🌀  Growing…", FONT_MEDIUM, GOLD,
                      cx, SCREEN_H - 55)

        self.btn_prev_t.draw(screen)
        self.btn_next_t.draw(screen)

        # ── Robot ─────────────────────────────────────────────
        self.robot.draw(screen)

        # ── Progress bar ──────────────────────────────────────
        progress = len(self.fib_sequence) / self.MAX_FIB_TERMS
        bar_w    = 300
        bar_x    = cx - bar_w // 2
        bar_y    = SCREEN_H - 145
        pygame.draw.rect(screen, (50, 50, 80),
                         (bar_x, bar_y, bar_w, 10), border_radius=5)
        pygame.draw.rect(screen, GOLD,
                         (bar_x, bar_y, int(bar_w * progress), 10),
                         border_radius=5)
        draw_text(screen, f"Progress: {len(self.fib_sequence)}/{self.MAX_FIB_TERMS}",
                  FONT_TINY, (180, 200, 255), cx, bar_y - 10)

    def _draw_sequence_bar(self, theme):
        """Render the Fibonacci number chips at the top of the play screen."""
        CHIP_W = 52
        CHIP_H = 34
        GAP    = 4
        total_w = len(self.fib_sequence) * (CHIP_W + GAP)
        start_x = (SCREEN_W - total_w) // 2
        y       = 28

        draw_text(screen, "Fibonacci Sequence:", FONT_TINY,
                  (180, 200, 255), SCREEN_W // 2, 8)

        for i, num in enumerate(self.fib_sequence):
            x = start_x + i * (CHIP_W + GAP)

            # Last chip pulses
            is_last = (i == len(self.fib_sequence) - 1)
            pulse   = int(math.sin(pygame.time.get_ticks() * 0.006) * 30) if is_last else 0

            # Chip background
            chip_surf = pygame.Surface((CHIP_W, CHIP_H), pygame.SRCALPHA)
            bg_alpha  = 180 + pulse
            pygame.draw.rect(chip_surf, (50, 30, 90, bg_alpha),
                             (0, 0, CHIP_W, CHIP_H), border_radius=7)
            border_col = (*GOLD, 200) if is_last else (100, 80, 160, 160)
            pygame.draw.rect(chip_surf, border_col,
                             (0, 0, CHIP_W, CHIP_H), width=2, border_radius=7)
            screen.blit(chip_surf, (x, y - CHIP_H // 2))

            # Number label
            font_  = FONT_SMALL if num >= 100 else FONT_MEDIUM
            col_   = GOLD if is_last else WHITE
            draw_text(screen, str(num), font_, col_,
                      x + CHIP_W // 2, y)

    # ── END SCREEN ────────────────────────────────────────────

    def _draw_end(self, t, theme):
        cx = SCREEN_W // 2

        # Confetti
        for c in self.confetti:
            c.draw(screen)

        # Fully drawn spiral
        self.spiral.draw(screen, theme["spiral_col"])

        # Pulsing title
        pulse   = math.sin(t * 0.003) * 6
        title_y = 100 + int(pulse)
        draw_glow_text(screen, "YOU GREW", FONT_LARGE, GOLD,
                       cx, title_y, layers=5, spread=6)
        draw_glow_text(screen, "NATURE'S SECRET BLUEPRINT!", FONT_LARGE,
                       GOLD, cx, title_y + 52, layers=4, spread=5)

        # Golden ratio
        phi_str = f"φ = 1.618033…  |  sequence: {', '.join(map(str, self.fib_sequence))}"
        draw_text(screen, phi_str, FONT_TINY, (200, 240, 200), cx, 210)

        # ── CTA Banners ───────────────────────────────────────
        banners = [
            ("🎓  LEARN HOW TO CODE — ENROLL IN CSITE NOW!",
             (70, 35, 140), (255, 215, 0)),
            ("🚀  BUILDING THE FUTURE, WITH FIBONACCI BLUEPRINT",
             (20, 80, 160), (255, 255, 255)),
            ("🌸  IDENTIFY FLOWERS WITH FIBONACCI NUMBERED PETALS",
             (20, 110, 50), (220, 255, 220)),
        ]

        for j, (text, bg, fg) in enumerate(banners):
            bw, bh = 740, 44
            bx     = (SCREEN_W - bw) // 2
            by     = 420 + j * 56

            # Banner shimmer (subtle wave)
            shimmer = int(math.sin(t * 0.004 + j * 1.2) * 12)
            banner_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(banner_surf, (*bg, 210),
                             (0, 0, bw, bh), border_radius=bh // 2)
            pygame.draw.rect(banner_surf, (*fg, 80),
                             (0, 0, bw, bh), width=2, border_radius=bh // 2)
            screen.blit(banner_surf, (bx, by))

            txt_surf = FONT_SMALL.render(text, True, fg)
            screen.blit(txt_surf,
                        txt_surf.get_rect(center=(cx, by + bh // 2)))

        # Buttons
        self.btn_again.draw(screen)
        self.btn_menu.draw(screen)

        # Robot cheering
        self.robot.msg_index = len(Robot.MESSAGES_PLAY) - 1
        self.robot.draw(screen)

        # Footer hint
        draw_text(screen, "Press SPACE to play again | ESC for menu",
                  FONT_TINY, (140, 160, 200), cx, SCREEN_H - 15)

    # ── HOW TO PLAY ───────────────────────────────────────────

    def _draw_howto(self, t):
        cx = SCREEN_W // 2

        # Panel
        panel = pygame.Surface((700, 520), pygame.SRCALPHA)
        pygame.draw.rect(panel, (20, 15, 50, 220), (0, 0, 700, 520),
                         border_radius=18)
        pygame.draw.rect(panel, (*GOLD, 120), (0, 0, 700, 520),
                         width=2, border_radius=18)
        screen.blit(panel, (100, 70))

        draw_glow_text(screen, "How to Play", FONT_LARGE, GOLD, cx, 110,
                       layers=4, spread=5)

        lines = [
            ("The Fibonacci Sequence:", FONT_MEDIUM, GOLD),
            ("  Each number = the sum of the previous two.", FONT_SMALL, WHITE),
            ("  1, 1, 2, 3, 5, 8, 13, 21, 34, 55 …", FONT_SMALL, CYAN),
            ("", FONT_SMALL, WHITE),
            ("How to play:", FONT_MEDIUM, GOLD),
            ("  ▶  Click 'Start Adventure' from the menu.", FONT_SMALL, WHITE),
            ("  ▶  Press SPACE or click 'Add Next' to grow", FONT_SMALL, WHITE),
            ("      the spiral one step at a time.", FONT_SMALL, WHITE),
            ("  ▶  Use ← / → keys to change the visual theme.", FONT_SMALL, WHITE),
            ("  ▶  Reach all 13 terms to see the celebration!", FONT_SMALL, WHITE),
            ("", FONT_SMALL, WHITE),
            ("Fun fact:", FONT_MEDIUM, GOLD),
            ("  The spiral you grow appears in sunflowers,",  FONT_SMALL, GREEN),
            ("  nautilus shells, galaxies — and even your", FONT_SMALL, GREEN),
            ("  DNA! φ ≈ 1.618 is called the Golden Ratio.", FONT_SMALL, GREEN),
        ]

        y = 160
        for text, font, col in lines:
            if text:
                surf = font.render(text, True, col)
                screen.blit(surf, (130, y))
            y += font.get_height() + 4

        self.btn_back.draw(screen)


# ============================================================
#  ENTRY POINT
# ============================================================

if __name__ == "__main__":
    # ── Quick dependency check ────────────────────────────────
    print("=" * 55)
    print("  FIBONACCI ADVENTURE – Grow Your Own Magic Spiral")
    print("=" * 55)
    print(f"  Python  : {sys.version.split()[0]}")
    print(f"  Pygame  : {pygame.version.ver}")
    print()
    print("  CONTROLS")
    print("  --------")
    print("  SPACE / Click 'Add Next' → grow the spiral")
    print("  ← / → arrow keys         → switch theme")
    print("  ESC                       → back to menu")
    print("=" * 55)
    print()

    game = FibonacciAdventure()
    game.run()

# ============================================================
#  EXTENSION IDEAS  (for curious students!)
# ============================================================
#
#  1. ADD MORE THEMES
#     Simply append a new dict to the THEMES list at the top.
#     Give it: name, bg_top, bg_bot, spiral_col, particles, star_colour.
#
#  2. CHANGE DIFFICULTY
#     Edit MAX_FIB_TERMS in FibonacciAdventure:
#       8  → Easy  (quick game)
#       13 → Normal (default)
#       20 → Hard  (huge spiral!)
#
#  3. QUIZ MODE
#     Instead of showing the next number automatically, ask the player
#     to type it in. Use pygame.KEYDOWN + event.unicode to read input.
#
#  4. SOUND EFFECTS
#     import pygame.mixer; mixer.init()
#     Map each Fibonacci term to a musical note — pentatonic scale
#     sounds great: C, D, E, G, A, C, D, E …
#
#  5. SAVE HIGH SCORES
#     import json; save {player_name: time_taken} to a .json file.
#
#  6. DRAW FIBONACCI PETALS
#     In the Flower Garden theme, draw actual flower petals arranged
#     in groups of 3, 5, 8, 13, 21 — exactly like real sunflowers!
# ============================================================