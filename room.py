"""
CSITE Escape Room: The Fibonacci Lab
=====================================
You're locked in the CSITE laboratory.  Six logic puzzles guard
the exit.  Each puzzle reveals one digit of the master code.
The 5 digits together form a famous mathematical constant.
Crack it and escape - before the timer hits zero.

PUZZLES (sequential)
--------------------
  1. Fibonacci Vault   - enter the next 3 numbers in 1,1,2,3,5,8,...
  2. Binary Lock       - toggle 4 bits to match a target decimal
  3. Pattern Panel     - continue the sequence
  4. Algorithm Sort    - click numbers in ascending order
  5. Nature's Code     - identify which flowers have Fibonacci petals
  6. Master Lock       - enter the 5-digit master code

CONTROLS
--------
  Mouse           click any button or interactive element
  0-9             enter digits on keypads
  BACKSPACE       delete last digit
  ENTER           submit answer
  H               use hint (one per puzzle, costs 30 seconds)
  ESC             quit

RUN
---
  pip install pygame
  python escape_room.py
"""

import pygame
import sys
import math
import random


# ============================================================
# CONFIGURATION
# ============================================================
WIDTH, HEIGHT = 800, 600
FPS           = 60
TOTAL_TIME    = 360.0   # 6 minutes - challenging booth play
HINT_PENALTY  = 45.0    # seconds removed when hint is used

# ----- Sci-fi neon palette ---------------------------------
BG_DARK    = (5,   10, 22)
BG_MID     = (8,   18, 36)
NAVY       = (15,  25, 50)
PANEL      = (18,  30, 58)
PANEL_HI   = (30,  48, 88)
NEON_CYAN  = (60,  230, 240)
NEON_GREEN = (60,  240, 130)
NEON_PINK  = (240, 90,  180)
AMBER      = (255, 180, 60)
ALARM_RED  = (255, 80,  80)
RED_DARK   = (90,  20,  30)
GREEN_DARK = (20,  80,  50)
WHITE      = (235, 245, 255)
SOFT       = (170, 195, 220)
DIM        = (90,  110, 140)
GRID_LINE  = (20,  35,  60)


# ============================================================
# UTILITIES
# ============================================================
def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(a, b, t):
    return (int(lerp(a[0], b[0], t)),
            int(lerp(a[1], b[1], t)),
            int(lerp(a[2], b[2], t)))


def gradient_bg(surface, top, bottom):
    """Vertical-gradient background fill."""
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        pygame.draw.line(surface, lerp_color(top, bottom, t),
                         (0, y), (WIDTH, y))


def draw_grid(surface, t_ms):
    """Subtly-animated grid lines for the lab floor effect."""
    spacing = 40
    offset  = (t_ms // 30) % spacing   # slow drift
    for x in range(-spacing, WIDTH + spacing, spacing):
        xx = x + offset
        pygame.draw.line(surface, GRID_LINE, (xx, 0), (xx, HEIGHT), 1)
    for y in range(-spacing, HEIGHT + spacing, spacing):
        yy = y + offset
        pygame.draw.line(surface, GRID_LINE, (0, yy), (WIDTH, yy), 1)


def draw_text(surface, text, font, color, x, y, center=False):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(surf, rect)
    return rect


def wrap_text(text, font, max_width):
    """Word-wrap; '\\n' forces a line break."""
    out = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            out.append('')
            continue
        words, cur = paragraph.split(' '), []
        for w in words:
            test = ' '.join(cur + [w])
            if font.size(test)[0] <= max_width:
                cur.append(w)
            else:
                if cur:
                    out.append(' '.join(cur))
                cur = [w]
        if cur:
            out.append(' '.join(cur))
    return out


def draw_wrapped(surface, text, font, color, x, y,
                 line_h, max_width, center_x=None):
    lines = wrap_text(text, font, max_width)
    for i, line in enumerate(lines):
        if center_x is not None:
            draw_text(surface, line, font, color,
                      center_x, y + i * line_h, center=True)
        else:
            draw_text(surface, line, font, color, x, y + i * line_h)
    return len(lines) * line_h


def fmt_time(seconds):
    """Format seconds as M:SS."""
    s = max(0, int(math.ceil(seconds)))
    return f"{s // 60}:{s % 60:02d}"


def draw_neon_panel(surface, rect, color, fill=PANEL, glow=True):
    """A neon-bordered rectangle. Used everywhere for the lab look."""
    pygame.draw.rect(surface, fill, rect, border_radius=10)
    if glow:
        # Outer glow (drawn as a slightly larger transparent rect)
        glow_surf = pygame.Surface((rect.width + 8, rect.height + 8),
                                   pygame.SRCALPHA)
        pygame.draw.rect(glow_surf,
                         (color[0], color[1], color[2], 50),
                         glow_surf.get_rect(), border_radius=12)
        surface.blit(glow_surf, (rect.x - 4, rect.y - 4))
    pygame.draw.rect(surface, color, rect, width=2, border_radius=10)


# ============================================================
# UI WIDGETS
# ============================================================
class Button:
    """Rounded-rect button with neon hover glow + disabled state."""
    def __init__(self, x, y, w, h, label,
                 color=NEON_CYAN, text_color=WHITE):
        self.rect       = pygame.Rect(x, y, w, h)
        self.label      = label
        self.color      = color
        self.text_color = text_color
        self.hovered    = False
        self.disabled   = False

    def update(self, mouse_pos):
        self.hovered = (not self.disabled
                        and self.rect.collidepoint(mouse_pos))

    def clicked(self, event):
        return (not self.disabled
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))

    def draw(self, surface, font):
        if self.disabled:
            fill, border, txt = (20, 30, 50), DIM, DIM
        else:
            fill   = PANEL_HI if self.hovered else PANEL
            border = self.color
            txt    = self.text_color
        # Hover-only glow
        if self.hovered and not self.disabled:
            g = pygame.Surface((self.rect.w + 12, self.rect.h + 12),
                               pygame.SRCALPHA)
            pygame.draw.rect(g,
                             (border[0], border[1], border[2], 70),
                             g.get_rect(), border_radius=14)
            surface.blit(g, (self.rect.x - 6, self.rect.y - 6))
        pygame.draw.rect(surface, fill, self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, width=2,
                         border_radius=10)
        ts = font.render(self.label, True, txt)
        surface.blit(ts, ts.get_rect(center=self.rect.center))


class Keypad:
    """A 3x4 numeric keypad for code entry. Used by puzzles 1 and 6."""
    def __init__(self, cx, cy, max_len, on_enter):
        # Layout: 3 columns x 4 rows
        # 1 2 3
        # 4 5 6
        # 7 8 9
        # CLR 0 ENT
        self.max_len  = max_len
        self.on_enter = on_enter
        self.value    = ""
        self.shake_t  = 0.0
        bw, bh, gap = 60, 50, 8
        kw = 3 * bw + 2 * gap
        kh = 4 * bh + 3 * gap
        x0 = cx - kw // 2
        y0 = cy - kh // 2
        self.buttons = []
        labels = ["1", "2", "3",
                  "4", "5", "6",
                  "7", "8", "9",
                  "CLR", "0", "ENT"]
        for i, lab in enumerate(labels):
            r, c = divmod(i, 3)
            rect = pygame.Rect(x0 + c * (bw + gap),
                               y0 + r * (bh + gap), bw, bh)
            self.buttons.append((lab, rect))
        # Display: above the keypad
        self.display_rect = pygame.Rect(x0 - 5, y0 - 60, kw + 10, 50)

    def push_digit(self, d):
        if len(self.value) < self.max_len:
            self.value += d

    def clear(self):
        self.value = ""

    def submit(self):
        ok = self.on_enter(self.value)
        if not ok:
            self.shake_t = 0.4   # red shake on wrong code
            self.value = ""
        return ok

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for lab, r in self.buttons:
                if r.collidepoint(event.pos):
                    if lab.isdigit():     self.push_digit(lab)
                    elif lab == "CLR":    self.clear()
                    elif lab == "ENT":    self.submit()
                    return True
        if event.type == pygame.KEYDOWN:
            if pygame.K_0 <= event.key <= pygame.K_9:
                self.push_digit(chr(event.key))
                return True
            if event.key == pygame.K_BACKSPACE:
                self.value = self.value[:-1]; return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.submit(); return True
        return False

    def update(self, dt):
        if self.shake_t > 0:
            self.shake_t -= dt

    def draw(self, surface, font_btn, font_disp):
        mp = pygame.mouse.get_pos()
        # ---- Display screen
        shake_x = (random.randint(-3, 3)
                   if self.shake_t > 0 else 0)
        dr = self.display_rect.move(shake_x, 0)
        border = ALARM_RED if self.shake_t > 0 else NEON_CYAN
        pygame.draw.rect(surface, (5, 12, 24), dr, border_radius=6)
        pygame.draw.rect(surface, border, dr, width=2, border_radius=6)
        # "Slots" - dim dots with entered digits over them
        slot_w = (dr.width - 20) / self.max_len
        for i in range(self.max_len):
            x = dr.x + 10 + slot_w * (i + 0.5)
            ch = self.value[i] if i < len(self.value) else ""
            color = NEON_CYAN if ch else DIM
            text = ch if ch else "_"
            ts = font_disp.render(text, True, color)
            surface.blit(ts, ts.get_rect(center=(x, dr.centery)))
        # ---- Buttons
        for lab, r in self.buttons:
            hov = r.collidepoint(mp)
            if   lab == "ENT":          col = NEON_GREEN
            elif lab == "CLR":          col = AMBER
            else:                       col = NEON_CYAN
            fill = PANEL_HI if hov else PANEL
            pygame.draw.rect(surface, fill, r, border_radius=8)
            pygame.draw.rect(surface, col, r, width=2, border_radius=8)
            ts = font_btn.render(lab, True, col if lab in ("ENT","CLR") else WHITE)
            surface.blit(ts, ts.get_rect(center=r.center))


# ============================================================
# BASE PUZZLE CLASS
# ============================================================
class Puzzle:
    """Common interface for every escape-room puzzle/room."""
    def __init__(self, title, hint_text, fragment):
        self.title       = title       # "ROOM 1: FIBONACCI VAULT"
        self.hint_text   = hint_text   # short hint string
        self.fragment    = fragment    # the digit revealed on success
        self.solved      = False
        self.hint_used   = False
        self.show_hint   = False       # toggled by hint button

    def handle_event(self, event):    pass
    def update(self, dt, mouse_pos):  pass
    def draw_body(self, surface, fonts): pass


# ============================================================
# PUZZLE 1: FIBONACCI VAULT
# ============================================================
class FibonacciVault(Puzzle):
    """Sequence showing Fibonacci numbers. Player enters the next 3.
    Difficulty: randomly pick from easy/medium/hard patterns."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 1 / 6  -  FIBONACCI VAULT",
            hint_text   = "Each number is the SUM of the two before it.",
            fragment    = "1",
        )
        # Multiple difficulty sets
        fib_sets = [
            ([1, 1, 2, 3, 5, 8], [13, 21, 34]),           # easy: classic
            ([2, 3, 5, 8, 13, 21], [34, 55, 89]),         # medium
            ([5, 8, 13, 21, 34, 55], [89, 144, 233]),     # hard: larger numbers
            ([1, 2, 3, 5, 8, 13], [21, 34, 55]),          # variant
        ]
        self.shown, self.target = random.choice(fib_sets)
        self.entered  = []   # list of correct ints already entered
        self.keypad   = Keypad(WIDTH // 2, 415, max_len=3,
                               on_enter=self._on_submit)
        self.flash_t  = 0.0   # green flash on correct entry

    def _on_submit(self, value):
        if not value:
            return False
        try:
            n = int(value)
        except ValueError:
            return False
        expected = self.target[len(self.entered)]
        if n == expected:
            self.entered.append(n)
            self.flash_t = 0.6
            self.keypad.value = ""
            if len(self.entered) == len(self.target):
                self.solved = True
            return True
        return False

    def handle_event(self, event):
        if not self.solved:
            self.keypad.handle_event(event)

    def update(self, dt, mouse_pos):
        self.keypad.update(dt)
        if self.flash_t > 0:
            self.flash_t -= dt

    def draw_body(self, surface, fonts):
        # ---- Story text
        draw_text(surface,
                  "The vault display reads a sequence...",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)
        draw_text(surface,
                  "Enter the next THREE numbers, one at a time.",
                  fonts['small'], DIM, WIDTH // 2, 134, center=True)

        # ---- Sequence display
        seq_y = 180
        # Build display: shown numbers + entered + remaining blanks
        display = [str(x) for x in self.shown]
        for n in self.entered:
            display.append(str(n))
        while len(display) < len(self.shown) + len(self.target):
            display.append("?")
        # Lay them out evenly
        sep = 50
        total_w = sum(fonts['big'].size(s)[0] for s in display) + sep * (len(display) - 1)
        x = WIDTH // 2 - total_w // 2
        glow = (self.flash_t > 0)
        for i, s in enumerate(display):
            shown_idx = i < len(self.shown)
            entered_idx = (len(self.shown) <= i
                           < len(self.shown) + len(self.entered))
            if shown_idx:                  color = NEON_CYAN
            elif entered_idx:              color = NEON_GREEN
            else:                          color = DIM
            ts = fonts['big'].render(s, True, color)
            r  = ts.get_rect(midleft=(x, seq_y))
            if entered_idx and i == len(self.shown) + len(self.entered) - 1 and glow:
                # Glowing halo around just-entered number
                hg = pygame.Surface((r.width + 30, r.height + 30),
                                    pygame.SRCALPHA)
                pygame.draw.ellipse(hg,
                                    (NEON_GREEN[0], NEON_GREEN[1],
                                     NEON_GREEN[2], 90),
                                    hg.get_rect())
                surface.blit(hg, (r.x - 15, r.y - 15))
            surface.blit(ts, r)
            x += ts.get_width() + sep

        # ---- Progress text
        draw_text(surface,
                  f"Numbers entered: {len(self.entered)} / {len(self.target)}",
                  fonts['small'], AMBER, WIDTH // 2, 250, center=True)

        # ---- Keypad
        self.keypad.draw(surface, fonts['med'], fonts['big'])


# ============================================================
# PUZZLE 2: BINARY LOCK
# ============================================================
class BinaryLock(Puzzle):
    """Player toggles 4 bits to make decimal target.
    Difficulty: randomly choose target from 1-15."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 2 / 6  -  BINARY LOCK",
            hint_text   = "Each bit is a power of two: 8, 4, 2, 1.",
            fragment    = "6",
        )
        # Random target from 1-15 for variety
        self.target = random.randint(1, 15)
        self.bits   = [0, 0, 0, 0]   # MSB first  (8s, 4s, 2s, 1s)
        self.values = [8, 4, 2, 1]
        self.submit_btn = Button(WIDTH // 2 - 90, 460, 180, 50,
                                 "SUBMIT", NEON_GREEN)
        self.shake_t = 0.0
        self._build_layout()

    def _build_layout(self):
        # 4 toggle switches centered horizontally
        sw_w, sw_h, gap = 90, 130, 28
        total = 4 * sw_w + 3 * gap
        x0 = WIDTH // 2 - total // 2
        y0 = 280
        self.switches = [
            pygame.Rect(x0 + i * (sw_w + gap), y0, sw_w, sw_h)
            for i in range(4)
        ]

    def current_value(self):
        return sum(b * v for b, v in zip(self.bits, self.values))

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.switches):
                if r.collidepoint(event.pos):
                    self.bits[i] = 1 - self.bits[i]
                    return
            if self.submit_btn.clicked(event):
                self._try_submit(); return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._try_submit()

    def _try_submit(self):
        if self.current_value() == self.target:
            self.solved = True
        else:
            self.shake_t = 0.4

    def update(self, dt, mouse_pos):
        self.submit_btn.update(mouse_pos)
        if self.shake_t > 0:
            self.shake_t -= dt

    def draw_body(self, surface, fonts):
        # ---- Story
        draw_text(surface,
                  "The 4-bit lock awaits.  Set the bits to match the target.",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)

        # ---- Target panel
        cur = self.current_value()
        match = (cur == self.target)
        shake = (random.randint(-2, 2) if self.shake_t > 0 else 0)
        tgt_rect = pygame.Rect(WIDTH//2 - 220, 150, 200, 90).move(shake, 0)
        draw_neon_panel(surface, tgt_rect, NEON_CYAN)
        draw_text(surface, "TARGET", fonts['small'], NEON_CYAN,
                  tgt_rect.centerx, tgt_rect.y + 22, center=True)
        draw_text(surface, str(self.target), fonts['huge'], WHITE,
                  tgt_rect.centerx, tgt_rect.y + 60, center=True)
        # Live value panel
        live_rect = pygame.Rect(WIDTH//2 + 20, 150, 200, 90)
        col = NEON_GREEN if match else AMBER
        draw_neon_panel(surface, live_rect, col)
        draw_text(surface, "CURRENT", fonts['small'], col,
                  live_rect.centerx, live_rect.y + 22, center=True)
        draw_text(surface, str(cur), fonts['huge'], WHITE,
                  live_rect.centerx, live_rect.y + 60, center=True)

        # ---- 4 toggle switches
        mp = pygame.mouse.get_pos()
        for i, r in enumerate(self.switches):
            on    = bool(self.bits[i])
            hover = r.collidepoint(mp) and not self.solved
            color = NEON_GREEN if on else DIM
            fill  = (8, 25, 14) if on else (15, 20, 30)
            if hover:
                fill = lerp_color(fill, WHITE, 0.1)
            pygame.draw.rect(surface, fill, r, border_radius=10)
            pygame.draw.rect(surface, color, r, width=2, border_radius=10)
            # Place-value label
            draw_text(surface, str(self.values[i]), fonts['small'], DIM,
                      r.centerx, r.y - 16, center=True)
            # LED circle
            cx, cy = r.centerx, r.y + 30
            pygame.draw.circle(surface, color, (cx, cy), 18)
            pygame.draw.circle(surface, WHITE, (cx, cy), 18, 2)
            if on:
                # Bright inner glow on the LED
                pygame.draw.circle(surface,
                                   lerp_color(color, WHITE, 0.5),
                                   (cx, cy), 9)
            # Bit value (1/0) below
            draw_text(surface, "1" if on else "0", fonts['big'], color,
                      r.centerx, r.y + 80, center=True)
            # ON/OFF label
            draw_text(surface, "ON" if on else "OFF",
                      fonts['tiny'], color,
                      r.centerx, r.bottom - 16, center=True)

        # ---- Submit button
        self.submit_btn.draw(surface, fonts['med'])


# ============================================================
# PUZZLE 3: PATTERN PANEL
# ============================================================
class PatternPanel(Puzzle):
    """Continue the sequence. Multiple patterns: powers, arithmetic, Fibonacci variations."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 3 / 6  -  PATTERN PANEL",
            hint_text   = "Look at the ratio or difference between each pair.",
            fragment    = "1",
        )
        # Multiple pattern sets with their correct answers
        patterns = [
            ([2, 4, 8, 16, 32], ["48", "56", "64", "128"], 2),         # powers of 2
            ([3, 6, 12, 24, 48], ["60", "72", "96", "192"], 2),        # multiply by 2
            ([1, 4, 9, 16, 25], ["36", "30", "32", "49"], 0),         # perfect squares
            ([2, 5, 10, 17, 26], ["33", "37", "40", "52"], 1),        # n^2+1
            ([1, 1, 2, 3, 5, 8], ["13", "11", "12", "15"], 0),        # Fibonacci
        ]
        seq, choices, correct_idx = random.choice(patterns)
        self.sequence = seq
        self.choices  = choices
        self.correct  = correct_idx
        self.selected = -1
        self.shake_t  = 0.0
        bw, bh, gap = 120, 80, 18
        total = 4 * bw + 3 * gap
        x0 = (WIDTH - total) // 2
        self.choice_rects = [
            pygame.Rect(x0 + i * (bw + gap), 380, bw, bh)
            for i in range(4)
        ]
        self.submit_btn = Button(WIDTH // 2 - 90, 490, 180, 50,
                                 "SUBMIT", NEON_GREEN)

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.choice_rects):
                if r.collidepoint(event.pos):
                    self.selected = i
                    return
            if self.submit_btn.clicked(event):
                self._try_submit()
        if event.type == pygame.KEYDOWN:
            keymap = {pygame.K_1: 0, pygame.K_a: 0,
                      pygame.K_2: 1, pygame.K_b: 1,
                      pygame.K_3: 2, pygame.K_c: 2,
                      pygame.K_4: 3, pygame.K_d: 3}
            if event.key in keymap:
                self.selected = keymap[event.key]
            elif event.key == pygame.K_RETURN and self.selected >= 0:
                self._try_submit()

    def _try_submit(self):
        if self.selected < 0:
            return
        if self.selected == self.correct:
            self.solved = True
        else:
            self.shake_t = 0.4

    def update(self, dt, mouse_pos):
        self.submit_btn.disabled = (self.selected < 0)
        self.submit_btn.update(mouse_pos)
        if self.shake_t > 0:
            self.shake_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface,
                  "What number completes the pattern?",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)

        # ---- Sequence row
        shake_x = random.randint(-2, 2) if self.shake_t > 0 else 0
        items   = [str(n) for n in self.sequence] + ["?"]
        cw, gap = 70, 14
        total = len(items) * cw + (len(items) - 1) * gap
        x0 = (WIDTH - total) // 2 + shake_x
        for i, val in enumerate(items):
            r = pygame.Rect(x0 + i * (cw + gap), 200, cw, 80)
            is_q = (val == "?")
            border = AMBER if is_q else NEON_CYAN
            fill   = (40, 25, 8) if is_q else PANEL
            pygame.draw.rect(surface, fill, r, border_radius=10)
            pygame.draw.rect(surface, border, r, width=2, border_radius=10)
            draw_text(surface, val, fonts['big'],
                      AMBER if is_q else WHITE,
                      r.centerx, r.centery, center=True)

        # ---- Choices
        mp = pygame.mouse.get_pos()
        for i, r in enumerate(self.choice_rects):
            picked = (i == self.selected)
            hover  = r.collidepoint(mp) and not self.solved
            if   picked:   bg, border = PANEL_HI, AMBER
            elif hover:    bg, border = PANEL_HI, NEON_CYAN
            else:          bg, border = PANEL,    NEON_CYAN
            pygame.draw.rect(surface, bg, r, border_radius=10)
            pygame.draw.rect(surface, border, r, width=2, border_radius=10)
            draw_text(surface, self.choices[i], fonts['big'], WHITE,
                      r.centerx, r.centery, center=True)

        # ---- Submit
        self.submit_btn.draw(surface, fonts['med'])


# ============================================================
# PUZZLE 4: ALGORITHM SORT
# ============================================================
class AlgorithmSort(Puzzle):
    """Click numbers in ascending order. Multiple difficulty sets."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 4 / 6  -  ALGORITHM SORT",
            hint_text   = "Click cards smallest to largest. "
                          "This is selection sort by hand.",
            fragment    = "8",
        )
        # Multiple sets with different ranges and count
        number_sets = [
            [42, 17, 23, 8, 31],                      # standard
            [5, 28, 13, 39, 7, 22],                   # 6 numbers
            [87, 12, 56, 34, 91, 19, 48],             # 7 numbers: larger range
            [100, 25, 60, 10, 75],                    # round numbers
        ]
        self.numbers   = random.choice(number_sets)
        self.target    = sorted(self.numbers)
        self.clicked   = []     # indices in click order
        self.flash_idx = -1
        self.flash_t   = 0.0
        self._build_layout()

    def _build_layout(self):
        n  = len(self.numbers)
        cw, ch, gap = 100, 100, 20
        total = n * cw + (n - 1) * gap
        sx = (WIDTH - total) // 2
        y  = 280
        self.rects = [pygame.Rect(sx + i * (cw + gap), y, cw, ch)
                      for i in range(n)]

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if not r.collidepoint(event.pos):
                    continue
                if i in self.clicked:
                    return
                expected = self.target[len(self.clicked)]
                if self.numbers[i] == expected:
                    self.clicked.append(i)
                    if len(self.clicked) == len(self.numbers):
                        self.solved = True
                else:
                    self.flash_idx = i
                    self.flash_t   = 0.45
                return

    def update(self, dt, mouse_pos):
        if self.flash_t > 0:
            self.flash_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface,
                  "Click the numbers in ASCENDING order (smallest first).",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)
        draw_text(surface,
                  "Wrong clicks just flash red - no penalty.",
                  fonts['small'], DIM, WIDTH // 2, 138, center=True)
        # progress
        draw_text(surface,
                  f"Sorted: {len(self.clicked)} / {len(self.numbers)}",
                  fonts['med'], AMBER, WIDTH // 2, 220, center=True)

        mp = pygame.mouse.get_pos()
        for i, r in enumerate(self.rects):
            order = self.clicked.index(i) if i in self.clicked else -1
            flash = (self.flash_t > 0 and self.flash_idx == i)
            if   flash:                   bg, bd = RED_DARK,   ALARM_RED
            elif order >= 0:              bg, bd = GREEN_DARK, NEON_GREEN
            elif r.collidepoint(mp) and not self.solved:
                                          bg, bd = PANEL_HI,   NEON_CYAN
            else:                         bg, bd = PANEL,      NEON_CYAN
            pygame.draw.rect(surface, bg, r, border_radius=14)
            pygame.draw.rect(surface, bd, r, width=3, border_radius=14)
            draw_text(surface, str(self.numbers[i]), fonts['huge'], WHITE,
                      r.centerx, r.centery - 6, center=True)
            if order >= 0:
                pygame.draw.circle(surface, NEON_GREEN,
                                   (r.right - 18, r.bottom - 18), 13)
                draw_text(surface, str(order + 1), fonts['small'],
                          BG_DARK, r.right - 18, r.bottom - 18, center=True)


# ============================================================
# PUZZLE 5: NATURE'S CODE  (Fibonacci flowers)
# ============================================================
def draw_flower(surface, cx, cy, n_petals,
                petal_color=(255, 150, 200),
                petal_outline=(255, 80, 160),
                size=46):
    """Procedurally drawn flower with leaf-shaped petals + center."""
    petal_len, petal_w = size, size * 0.45
    for i in range(n_petals):
        ang = i * (2 * math.pi / n_petals) - math.pi / 2
        ca, sa = math.cos(ang), math.sin(ang)
        N, pts = 12, []
        for t in range(N + 1):
            tt = t / N
            r  = math.sin(tt * math.pi)
            ax = ca * petal_len * tt - sa * r * petal_w
            ay = sa * petal_len * tt + ca * r * petal_w
            pts.append((cx + ax, cy + ay))
        for t in range(N, -1, -1):
            tt = t / N
            r  = math.sin(tt * math.pi)
            ax = ca * petal_len * tt + sa * r * petal_w
            ay = sa * petal_len * tt - ca * r * petal_w
            pts.append((cx + ax, cy + ay))
        pygame.draw.polygon(surface, petal_color, pts)
        pygame.draw.polygon(surface, petal_outline, pts, 2)
    pygame.draw.circle(surface, (255, 215, 80), (cx, cy), int(size * 0.32))
    pygame.draw.circle(surface, (200, 150, 60), (cx, cy), int(size * 0.32), 2)


class NaturesCode(Puzzle):
    """Click flowers with Fibonacci petal counts. Multiple flower sets."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 5 / 6  -  NATURE'S CODE",
            hint_text   = "Fibonacci numbers: 1, 2, 3, 5, 8, 13, 21, 34...",
            fragment    = "0",
        )
        self.fib_set    = {1, 2, 3, 5, 8, 13, 21, 34, 55}
        # Multiple flower sets for variety
        flower_sets = [
            [4, 5, 6, 8],                    # 2 Fibonacci (5, 8)
            [6, 8, 13, 15],                  # 2 Fibonacci (8, 13)
            [3, 7, 11, 13, 21],              # 3 Fibonacci (3, 13, 21)
            [2, 5, 9, 21],                   # 3 Fibonacci (2, 5, 21)
        ]
        self.flowers    = random.choice(flower_sets)
        n = len(self.flowers)
        color_palette = [
            (255, 130, 90), (255, 180, 220), (180, 220, 255),
            (220, 255, 150), (200, 150, 255), (255, 200, 150)
        ]
        outline_palette = [
            (220, 80, 40), (220, 100, 170), (90, 140, 220),
            (140, 200, 80), (150, 80, 200), (220, 150, 80)
        ]
        self.colors     = color_palette[:n]
        self.outlines   = outline_palette[:n]
        self.selected   = [False] * n
        self.shake_t    = 0.0
        self._build_layout()
        self.submit_btn = Button(WIDTH // 2 - 90, 490, 180, 50,
                                 "SUBMIT", NEON_GREEN)

    def _build_layout(self):
        n = len(self.flowers)
        cw, ch, gap = 140, 180, 30
        total = n * cw + (n - 1) * gap
        x0 = (WIDTH - total) // 2
        self.rects = [pygame.Rect(x0 + i * (cw + gap), 200, cw, ch)
                      for i in range(n)]

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.selected[i] = not self.selected[i]
                    return
            if self.submit_btn.clicked(event):
                self._try_submit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._try_submit()

    def _try_submit(self):
        # Correct = exactly the flowers with Fibonacci petal counts selected
        for i, n in enumerate(self.flowers):
            should = (n in self.fib_set)
            if self.selected[i] != should:
                self.shake_t = 0.4
                return
        self.solved = True

    def update(self, dt, mouse_pos):
        self.submit_btn.update(mouse_pos)
        if self.shake_t > 0:
            self.shake_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface,
                  "Select EVERY flower with a Fibonacci number of petals.",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)
        draw_text(surface,
                  "Click to toggle - then SUBMIT.",
                  fonts['small'], DIM, WIDTH // 2, 138, center=True)

        mp = pygame.mouse.get_pos()
        shake_x = random.randint(-2, 2) if self.shake_t > 0 else 0
        for i, r in enumerate(self.rects):
            r2 = r.move(shake_x, 0)
            sel   = self.selected[i]
            hover = r2.collidepoint(mp) and not self.solved
            if   sel:    bg, border = PANEL_HI, NEON_GREEN
            elif hover:  bg, border = PANEL_HI, NEON_CYAN
            else:        bg, border = PANEL,    NEON_CYAN
            pygame.draw.rect(surface, bg, r2, border_radius=14)
            pygame.draw.rect(surface, border, r2, width=3, border_radius=14)
            # Flower
            draw_flower(surface, r2.centerx, r2.centery - 18,
                        self.flowers[i],
                        petal_color=self.colors[i],
                        petal_outline=self.outlines[i],
                        size=42)
            # Petal count label
            draw_text(surface,
                      f"{self.flowers[i]} petals",
                      fonts['med'], WHITE,
                      r2.centerx, r2.bottom - 22, center=True)
            # Selection check mark
            if sel:
                cx, cy = r2.right - 22, r2.y + 22
                pygame.draw.circle(surface, NEON_GREEN, (cx, cy), 14)
                pygame.draw.line(surface, BG_DARK,
                                 (cx - 6, cy), (cx - 1, cy + 6), 3)
                pygame.draw.line(surface, BG_DARK,
                                 (cx - 1, cy + 6), (cx + 7, cy - 5), 3)

        self.submit_btn.draw(surface, fonts['med'])


# ============================================================
# PUZZLE 6: PRIME FINDER  (new puzzle)
# ============================================================
class PrimeFinder(Puzzle):
    """Identify prime numbers from a set. Multiple difficulty sets."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 6 / 6  -  PRIME FINDER",
            hint_text   = "Prime numbers are only divisible by 1 and themselves.",
            fragment    = "2",
        )
        # Multiple number sets with prime indices marked
        prime_sets = [
            ([4, 7, 9, 11, 15, 19], [1, 3, 5]),           # primes: 7, 11, 19
            ([2, 6, 13, 15, 17, 21, 23], [0, 2, 4, 6]),   # primes: 2, 13, 17, 23
            ([5, 10, 14, 20, 25, 29], [0, 5]),             # primes: 5, 29
        ]
        nums, self.prime_indices = random.choice(prime_sets)
        self.numbers = nums
        self.selected = set()
        self.shake_t = 0.0
        self._build_layout()
        self.submit_btn = Button(WIDTH // 2 - 90, 490, 180, 50,
                                 "SUBMIT", NEON_GREEN)

    def _build_layout(self):
        n = len(self.numbers)
        cw, ch, gap = 100, 100, 16
        total = n * cw + (n - 1) * gap
        x0 = (WIDTH - total) // 2
        self.rects = [pygame.Rect(x0 + i * (cw + gap), 280, cw, ch)
                      for i in range(n)]

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    if i in self.selected:
                        self.selected.remove(i)
                    else:
                        self.selected.add(i)
                    return
            if self.submit_btn.clicked(event):
                self._try_submit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._try_submit()

    def _try_submit(self):
        if set(self.prime_indices) == self.selected:
            self.solved = True
        else:
            self.shake_t = 0.4

    def update(self, dt, mouse_pos):
        self.submit_btn.update(mouse_pos)
        if self.shake_t > 0:
            self.shake_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface,
                  "Click EVERY prime number in the set.",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)
        draw_text(surface,
                  "Prime = divisible only by 1 and itself.",
                  fonts['small'], DIM, WIDTH // 2, 138, center=True)

        mp = pygame.mouse.get_pos()
        shake_x = random.randint(-2, 2) if self.shake_t > 0 else 0
        for i, r in enumerate(self.rects):
            r2 = r.move(shake_x, 0)
            selected = (i in self.selected)
            hover = r2.collidepoint(mp) and not self.solved
            if selected:    bg, bd = PANEL_HI, NEON_GREEN
            elif hover:     bg, bd = PANEL_HI, NEON_CYAN
            else:           bg, bd = PANEL, NEON_CYAN
            pygame.draw.rect(surface, bg, r2, border_radius=10)
            pygame.draw.rect(surface, bd, r2, width=2, border_radius=10)
            draw_text(surface, str(self.numbers[i]), fonts['huge'], WHITE,
                      r2.centerx, r2.centery, center=True)
            if selected:
                pygame.draw.circle(surface, NEON_GREEN, (r2.right - 14, r2.top + 14), 9)
                pygame.draw.line(surface, BG_DARK, (r2.right - 18, r2.top + 14),
                                 (r2.right - 13, r2.top + 19), 2)
                pygame.draw.line(surface, BG_DARK, (r2.right - 13, r2.top + 19),
                                 (r2.right - 7, r2.top + 10), 2)

        self.submit_btn.draw(surface, fonts['med'])


# ============================================================
# PUZZLE 7: HEX MATH  (new puzzle)
# ============================================================
class HexMath(Puzzle):
    """Convert hex to decimal or solve hex arithmetic."""
    def __init__(self):
        super().__init__(
            title       = "ROOM 7 / 6  -  HEX MATH",
            hint_text   = "Hex uses 0-9 and A-F. A=10, F=15.",
            fragment    = "3",
        )
        # Problem sets: (question, answer_choices, correct_index)
        problems = [
            ("What is 0x1F in decimal?", ["25", "31", "35", "30"], 1),
            ("What is 0xA in decimal?", ["10", "15", "20", "5"], 0),
            ("What is 0x20 + 0x10?", ["32", "30", "48", "50"], 2),
            ("What is 0xFF?", ["255", "200", "256", "128"], 0),
        ]
        self.question_text, self.choices, self.correct = random.choice(problems)
        self.selected = -1
        self.shake_t = 0.0
        bw, bh, gap = 120, 80, 18
        total = 4 * bw + 3 * gap
        x0 = (WIDTH - total) // 2
        self.choice_rects = [
            pygame.Rect(x0 + i * (bw + gap), 360, bw, bh)
            for i in range(4)
        ]
        self.submit_btn = Button(WIDTH // 2 - 90, 480, 180, 50,
                                 "SUBMIT", NEON_GREEN)

    def handle_event(self, event):
        if self.solved:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.choice_rects):
                if r.collidepoint(event.pos):
                    self.selected = i
                    return
            if self.submit_btn.clicked(event):
                self._try_submit()
        if event.type == pygame.KEYDOWN:
            keymap = {pygame.K_1: 0, pygame.K_a: 0, pygame.K_2: 1, pygame.K_b: 1,
                      pygame.K_3: 2, pygame.K_c: 2, pygame.K_4: 3, pygame.K_d: 3}
            if event.key in keymap:
                self.selected = keymap[event.key]
            elif event.key == pygame.K_RETURN and self.selected >= 0:
                self._try_submit()

    def _try_submit(self):
        if self.selected < 0:
            return
        if self.selected == self.correct:
            self.solved = True
        else:
            self.shake_t = 0.4

    def update(self, dt, mouse_pos):
        self.submit_btn.disabled = (self.selected < 0)
        self.submit_btn.update(mouse_pos)
        if self.shake_t > 0:
            self.shake_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface,
                  self.question_text,
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)
        draw_text(surface,
                  "Select the correct answer.",
                  fonts['small'], DIM, WIDTH // 2, 138, center=True)

        mp = pygame.mouse.get_pos()
        for i, r in enumerate(self.choice_rects):
            picked = (i == self.selected)
            hover = r.collidepoint(mp) and not self.solved
            if picked:   bg, border = PANEL_HI, AMBER
            elif hover:  bg, border = PANEL_HI, NEON_CYAN
            else:        bg, border = PANEL, NEON_CYAN
            pygame.draw.rect(surface, bg, r, border_radius=10)
            pygame.draw.rect(surface, border, r, width=2, border_radius=10)
            draw_text(surface, self.choices[i], fonts['big'], WHITE,
                      r.centerx, r.centery, center=True)

        self.submit_btn.draw(surface, fonts['med'])


# ============================================================
# PUZZLE 8: MASTER LOCK
# ============================================================
class MasterLock(Puzzle):
    """Final 5-digit lock. Player enters the 5 collected fragments."""
    def __init__(self, fragments):
        super().__init__(
            title       = "ROOM 8 / 8  -  MASTER LOCK",
            hint_text   = "Look at your fragments at the bottom of the screen.",
            fragment    = "",      # no fragment - this is the goal
        )
        self.target = ''.join(fragments)   # e.g. "16180"
        self.keypad = Keypad(WIDTH // 2, 410, max_len=5,
                             on_enter=self._on_submit)

    def _on_submit(self, value):
        if value == self.target:
            self.solved = True
            return True
        return False

    def handle_event(self, event):
        if not self.solved:
            self.keypad.handle_event(event)

    def update(self, dt, mouse_pos):
        self.keypad.update(dt)

    def draw_body(self, surface, fonts):
        draw_text(surface,
                  "Combine your 5 code fragments into the master key.",
                  fonts['text'], SOFT, WIDTH // 2, 110, center=True)
        draw_text(surface,
                  "Hint: these 5 digits begin a famous mathematical constant.",
                  fonts['small'], AMBER, WIDTH // 2, 138, center=True)

        # Big lock icon above keypad
        icon_y = 220
        pygame.draw.circle(surface, NEON_PINK, (WIDTH // 2, icon_y), 38, 4)
        # Lock shackle (an arc)
        pygame.draw.arc(surface, NEON_PINK,
                        (WIDTH // 2 - 22, icon_y - 56, 44, 50),
                        0, math.pi, 4)
        # Body of the lock (rect)
        body = pygame.Rect(WIDTH//2 - 26, icon_y - 14, 52, 38)
        pygame.draw.rect(surface, PANEL_HI, body, border_radius=6)
        pygame.draw.rect(surface, NEON_PINK, body, width=3, border_radius=6)
        # Keyhole
        pygame.draw.circle(surface, NEON_PINK,
                           (WIDTH // 2, icon_y + 2), 4)

        self.keypad.draw(surface, fonts['med'], fonts['big'])


# ============================================================
# CALL-TO-ACTION BANNERS for the victory screen
# ============================================================
CTAS = [
    ("LEARN HOW TO CODE",                        AMBER),
    ("ENROLL IN CSITE NOW!",                     NEON_GREEN),
    ("BUILD THE FUTURE WITH FIBONACCI BLUEPRINT", NEON_CYAN),
    ("THINK LIKE AN ENGINEER -- JOIN CSITE",     NEON_PINK),
]


# ============================================================
# THE GAME
# ============================================================
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(
            "CSITE Escape Room: The Fibonacci Lab")
        self.clock = pygame.time.Clock()
        self._load_fonts()

        # state machine
        self.state = "intro"   # intro | briefing | playing | unlock | victory | defeat

        # game state
        self.time_left   = TOTAL_TIME
        self.fragments   = []     # fragments collected so far
        self.score       = 0
        self.hints_used  = 0
        self.unlock_t    = 0.0    # progress of door-unlock animation
        self.q_index     = 0
        self.puzzles     = []
        self._build_puzzles()

        # buttons (persistent across states)
        self.intro_start = Button(WIDTH//2 - 130, 460, 260, 60,
                                  "ENTER THE LAB", NEON_GREEN)
        self.brief_begin = Button(WIDTH//2 - 130, 510, 260, 55,
                                  "I'M READY - START", NEON_GREEN)
        self.brief_back  = Button(40, 530, 110, 40,
                                  "< Back", NEON_CYAN)
        self.hint_btn    = Button(WIDTH - 130, 70, 110, 36,
                                  "HINT (-30s)", AMBER)
        self.victory_again = Button(WIDTH - 200, 545, 170, 40,
                                    "Play Again", NEON_GREEN)
        self.victory_quit  = Button(30, 545, 110, 40,
                                    "Quit", NEON_CYAN)

    # ---------------------------------------------------------
    def _load_fonts(self):
        self.f_huge  = pygame.font.SysFont("arial", 56, bold=True)
        self.f_big   = pygame.font.SysFont("arial", 36, bold=True)
        self.f_med   = pygame.font.SysFont("arial", 24, bold=True)
        self.f_text  = pygame.font.SysFont("arial", 19)
        self.f_q     = pygame.font.SysFont("arial", 22, bold=True)
        self.f_small = pygame.font.SysFont("arial", 16)
        self.f_tiny  = pygame.font.SysFont("arial", 13, bold=True)
        self.f_mono  = pygame.font.SysFont("couriernew,courier", 22, bold=True)

    def _build_puzzles(self):
        """Order matters - fragments are collected in this order."""
        # First 7 puzzles each contribute one digit
        self.puzzles = [
            FibonacciVault(),       # fragment "1"
            BinaryLock(),           # fragment "6"
            PatternPanel(),         # fragment "1"
            AlgorithmSort(),        # fragment "8"
            NaturesCode(),          # fragment "0"
            PrimeFinder(),          # fragment "2"
            HexMath(),              # fragment "3"
        ]
        # Master lock built once we know what the fragments are
        master_target = [p.fragment for p in self.puzzles]
        self.puzzles.append(MasterLock(master_target))

    def _font_dict(self):
        return {'huge': self.f_huge, 'big': self.f_big, 'med': self.f_med,
                'text': self.f_text, 'q': self.f_q, 'small': self.f_small,
                'tiny': self.f_tiny, 'mono': self.f_mono}

    # ---------------------------------------------------------
    # GAME-FLOW HELPERS
    # ---------------------------------------------------------
    def _reset(self):
        self.time_left  = TOTAL_TIME
        self.fragments  = []
        self.score      = 0
        self.hints_used = 0
        self.q_index    = 0
        self.unlock_t   = 0.0
        self._build_puzzles()
        self.state = "playing"

    def _on_puzzle_solved(self, p):
        """Called once when a puzzle transitions from unsolved to solved."""
        if p.fragment:                 # rooms 1-5
            self.fragments.append(p.fragment)
        self.score += 100
        if p is self.puzzles[-1]:
            # Last puzzle - victory
            self.score += int(self.time_left * 2)   # time bonus
            self.state = "victory"
        else:
            self.unlock_t = 0.0
            self.state = "unlock"

    def _advance_room(self):
        self.q_index += 1
        self.state = "playing"

    def _use_hint(self):
        p = self.puzzles[self.q_index]
        if not p.hint_used and not p.solved:
            p.hint_used = True
            p.show_hint = True
            self.hints_used += 1
            self.time_left = max(0, self.time_left - HINT_PENALTY)

    # ---------------------------------------------------------
    # INTRO SCREEN
    # ---------------------------------------------------------
    def _draw_intro(self):
        gradient_bg(self.screen, BG_MID, BG_DARK)
        draw_grid(self.screen, pygame.time.get_ticks())

        t_ms  = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(t_ms / 700)

        # Title halo
        halo = pygame.Surface((WIDTH, 200), pygame.SRCALPHA)
        pygame.draw.ellipse(
            halo,
            (NEON_CYAN[0], NEON_CYAN[1], NEON_CYAN[2],
             int(40 + 50 * pulse)),
            halo.get_rect().inflate(-100, -50))
        self.screen.blit(halo, (0, 100))

        draw_text(self.screen, "CSITE ESCAPE ROOM", self.f_huge,
                  NEON_CYAN, WIDTH // 2, 150, center=True)
        draw_text(self.screen, "THE FIBONACCI LAB", self.f_big,
                  AMBER, WIDTH // 2, 215, center=True)

        # Subtitle / hook
        draw_text(self.screen,
                  "You have 8 minutes.  Six puzzles.  One way out.",
                  self.f_text, SOFT, WIDTH // 2, 280, center=True)
        draw_text(self.screen,
                  "Crack the code.  Escape the lab.  Unlock the golden secret.",
                  self.f_small, DIM, WIDTH // 2, 310, center=True)

        # Warning bar (red blinking)
        if int(t_ms / 500) % 2:
            bar = pygame.Rect(WIDTH//2 - 200, 360, 400, 36)
            pygame.draw.rect(self.screen, RED_DARK, bar, border_radius=18)
            pygame.draw.rect(self.screen, ALARM_RED, bar, 2, border_radius=18)
            draw_text(self.screen, "// LAB LOCKDOWN ENGAGED //",
                      self.f_small, ALARM_RED,
                      bar.centerx, bar.centery, center=True)

        self.intro_start.draw(self.screen, self.f_med)
        draw_text(self.screen,
                  "College of Science, Information Technology & Engineering",
                  self.f_tiny, DIM, WIDTH // 2, HEIGHT - 22, center=True)

    def _handle_intro(self, events, mp):
        self.intro_start.update(mp)
        for e in events:
            if self.intro_start.clicked(e):
                self.state = "briefing"
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN,
                                                      pygame.K_SPACE):
                self.state = "briefing"

    # ---------------------------------------------------------
    # BRIEFING SCREEN
    # ---------------------------------------------------------
    def _draw_briefing(self):
        gradient_bg(self.screen, BG_MID, BG_DARK)
        draw_grid(self.screen, pygame.time.get_ticks())
        draw_text(self.screen, "MISSION BRIEFING", self.f_big,
                  NEON_CYAN, WIDTH // 2, 50, center=True)

        # Briefing card
        card = pygame.Rect(50, 100, WIDTH - 100, 380)
        draw_neon_panel(self.screen, card, NEON_CYAN)

        story = [
            "> SYSTEM: You are locked inside the CSITE Fibonacci Lab.",
            "> Six security panels guard the exit.",
            "> Each panel reveals one digit of the master code.",
            "> Solve all six panels before the timer reaches zero.",
            "",
            ">> CONTROLS:",
            "   Mouse: click any button or interactive element",
            "   0-9 / ENTER: type and submit on keypads",
            "   H: use a hint (one per puzzle, costs 30 seconds)",
            "   ESC: abort mission",
            "",
            ">> The 5 collected digits form a famous constant.",
            "   Find it.  Escape.  Build the future."
        ]
        y = card.y + 24
        for line in story:
            color = NEON_GREEN if line.startswith(">>") else \
                    AMBER      if line.startswith(">") and not line.startswith(">>") else \
                    SOFT
            draw_text(self.screen, line, self.f_mono, color,
                      card.x + 22, y)
            y += 26

        self.brief_back.draw(self.screen, self.f_text)
        self.brief_begin.draw(self.screen, self.f_med)

    def _handle_briefing(self, events, mp):
        self.brief_back.update(mp)
        self.brief_begin.update(mp)
        for e in events:
            if self.brief_back.clicked(e):
                self.state = "intro"
            if self.brief_begin.clicked(e):
                self._reset()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN,
                                                      pygame.K_SPACE):
                self._reset()

    # ---------------------------------------------------------
    # PLAYING - top bar / inventory / room
    # ---------------------------------------------------------
    def _draw_top_bar(self):
        bar_h = 56
        pygame.draw.rect(self.screen, BG_DARK, (0, 0, WIDTH, bar_h))
        pygame.draw.line(self.screen, NEON_CYAN, (0, bar_h), (WIDTH, bar_h), 2)

        # ---- Timer (left) - alarm red when low
        critical = self.time_left < 60
        blink = int(pygame.time.get_ticks() / 300) % 2
        timer_col = ALARM_RED if (critical and blink) else \
                    AMBER     if critical else NEON_CYAN
        draw_text(self.screen, "TIME", self.f_tiny, DIM, 20, 8)
        draw_text(self.screen, fmt_time(self.time_left),
                  self.f_big, timer_col, 20, 22)

        # ---- Score (centre)
        draw_text(self.screen, "SCORE", self.f_tiny, DIM,
                  WIDTH // 2, 8, center=True)
        draw_text(self.screen, str(self.score), self.f_big, AMBER,
                  WIDTH // 2, 32, center=True)

        # ---- Progress dots (right)
        n = len(self.puzzles)
        cx = WIDTH - 250
        for i in range(n):
            x = cx + i * 24
            y = 28
            if self.puzzles[i].solved:
                pygame.draw.circle(self.screen, NEON_GREEN, (x, y), 8)
                pygame.draw.circle(self.screen, WHITE, (x, y), 8, 1)
            elif i == self.q_index:
                pygame.draw.circle(self.screen, AMBER, (x, y), 8)
                # pulsing ring
                pulse = 4 + int(3 + 3 * math.sin(pygame.time.get_ticks() / 200))
                pygame.draw.circle(self.screen, AMBER, (x, y), 8 + pulse, 1)
            else:
                pygame.draw.circle(self.screen, DIM, (x, y), 8, 2)
        draw_text(self.screen, "ROOMS",
                  self.f_tiny, DIM,
                  cx + (n - 1) * 12, 8, center=True)

    def _draw_inventory(self):
        # Bottom strip - 5 fragment slots
        strip_y = HEIGHT - 56
        pygame.draw.rect(self.screen, BG_DARK,
                         (0, strip_y, WIDTH, 56))
        pygame.draw.line(self.screen, NEON_CYAN,
                         (0, strip_y), (WIDTH, strip_y), 2)
        # Label (left)
        draw_text(self.screen, "CODE FRAGMENTS",
                  self.f_tiny, DIM, 20, strip_y + 10)
        # 5 slots starting at x=20 a bit lower
        slot_w = 38
        gap    = 8
        sx = 20
        sy = strip_y + 22
        for i in range(5):
            r = pygame.Rect(sx + i * (slot_w + gap), sy, slot_w, 30)
            if i < len(self.fragments):
                pygame.draw.rect(self.screen, GREEN_DARK, r, border_radius=6)
                pygame.draw.rect(self.screen, NEON_GREEN, r, width=2,
                                 border_radius=6)
                draw_text(self.screen, self.fragments[i],
                          self.f_med, NEON_GREEN,
                          r.centerx, r.centery, center=True)
            else:
                pygame.draw.rect(self.screen, PANEL, r, border_radius=6)
                pygame.draw.rect(self.screen, DIM, r, width=2,
                                 border_radius=6)
                draw_text(self.screen, "?", self.f_med, DIM,
                          r.centerx, r.centery, center=True)

        # Right side: hint button + ESC reminder
        draw_text(self.screen, "ESC = quit",
                  self.f_tiny, DIM, WIDTH - 75, strip_y + 22)

    def _draw_playing(self):
        gradient_bg(self.screen, BG_MID, BG_DARK)
        draw_grid(self.screen, pygame.time.get_ticks())
        self._draw_top_bar()

        p = self.puzzles[self.q_index]

        # Room title strip
        draw_text(self.screen, p.title, self.f_med, NEON_CYAN,
                  WIDTH // 2, 76, center=True)

        # Puzzle body
        p.draw_body(self.screen, self._font_dict())

        # Hint button - top-right (above the puzzle area)
        if not p.solved:
            self.hint_btn.disabled = p.hint_used
            self.hint_btn.label = "HINT USED" if p.hint_used else "HINT (-30s)"
            self.hint_btn.draw(self.screen, self.f_small)

        # Persistent hint banner once used
        if p.show_hint:
            hint_rect = pygame.Rect(40, HEIGHT - 110, WIDTH - 80, 38)
            draw_neon_panel(self.screen, hint_rect, AMBER, fill=(40, 30, 8))
            draw_text(self.screen, "HINT: " + p.hint_text,
                      self.f_small, AMBER,
                      hint_rect.centerx, hint_rect.centery, center=True)

        self._draw_inventory()

    def _handle_playing(self, events, mp, dt):
        # Tick down timer
        self.time_left -= dt
        if self.time_left <= 0:
            self.time_left = 0
            self.state = "defeat"
            return

        p = self.puzzles[self.q_index]

        # Update puzzle (animations, etc)
        p.update(dt, mp)

        # Hint button hover
        if not p.solved:
            self.hint_btn.disabled = p.hint_used
            self.hint_btn.update(mp)

        # Process events
        for e in events:
            # Hint button
            if (not p.solved and not p.hint_used
                and self.hint_btn.clicked(e)):
                self._use_hint()
                continue
            if e.type == pygame.KEYDOWN and e.key == pygame.K_h:
                self._use_hint()
                continue
            # Forward event to puzzle
            p.handle_event(e)

        # Detect solve transition
        if p.solved:
            self._on_puzzle_solved(p)

    # ---------------------------------------------------------
    # UNLOCK ANIMATION (between rooms)
    # ---------------------------------------------------------
    UNLOCK_DURATION = 1.6

    def _draw_unlock(self):
        gradient_bg(self.screen, BG_MID, BG_DARK)
        draw_grid(self.screen, pygame.time.get_ticks())
        self._draw_top_bar()
        self._draw_inventory()

        t = self.unlock_t / self.UNLOCK_DURATION   # 0..1

        # Door panels sliding apart from center
        door_w     = WIDTH // 2
        door_h     = 360
        door_y     = (HEIGHT - door_h) // 2
        gap_open   = int(door_w * t)
        # Left door
        ldr = pygame.Rect(-gap_open, door_y, door_w, door_h)
        # Right door
        rdr = pygame.Rect(WIDTH - door_w + gap_open, door_y, door_w, door_h)

        # Light leaking through gap
        if t > 0:
            light = pygame.Rect(door_w - gap_open, door_y,
                                gap_open * 2, door_h)
            light_surf = pygame.Surface(light.size, pygame.SRCALPHA)
            light_surf.fill((NEON_GREEN[0], NEON_GREEN[1],
                             NEON_GREEN[2], int(120 * (1 - t * 0.5))))
            self.screen.blit(light_surf, light)

        # Doors
        for r in (ldr, rdr):
            pygame.draw.rect(self.screen, PANEL_HI, r)
            pygame.draw.rect(self.screen, NEON_CYAN, r, 3)
            # Panel detailing
            for k in range(1, 4):
                y = r.y + door_h * k // 4
                pygame.draw.line(self.screen, NEON_CYAN,
                                 (r.x + 20, y), (r.right - 20, y), 1)

        # ACCESS GRANTED banner
        if t > 0.2:
            alpha = min(255, int(255 * (t - 0.2) / 0.4))
            banner = pygame.Surface((520, 70), pygame.SRCALPHA)
            pygame.draw.rect(banner,
                             (NEON_GREEN[0], NEON_GREEN[1],
                              NEON_GREEN[2], alpha),
                             banner.get_rect(), border_radius=10)
            self.screen.blit(banner, (WIDTH // 2 - 260,
                                      HEIGHT // 2 - 35))
            ts = self.f_big.render("ACCESS GRANTED", True, BG_DARK)
            ts.set_alpha(alpha)
            self.screen.blit(
                ts, ts.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        # Fragment-collected chip floats up
        if self.fragments and t < 0.9:
            frag = self.fragments[-1]
            cy   = HEIGHT // 2 + 60 - int(40 * t)
            chip = pygame.Rect(WIDTH // 2 - 110, cy, 220, 38)
            pygame.draw.rect(self.screen, GREEN_DARK, chip,
                             border_radius=8)
            pygame.draw.rect(self.screen, NEON_GREEN, chip, width=2,
                             border_radius=8)
            draw_text(self.screen,
                      f"FRAGMENT COLLECTED: {frag}",
                      self.f_small, NEON_GREEN,
                      chip.centerx, chip.centery, center=True)

    def _handle_unlock(self, events, mp, dt):
        self.time_left = max(0, self.time_left - dt)   # timer keeps ticking
        self.unlock_t += dt
        if self.unlock_t >= self.UNLOCK_DURATION:
            self._advance_room()

    # ---------------------------------------------------------
    # VICTORY SCREEN
    # ---------------------------------------------------------
    def _draw_victory(self):
        gradient_bg(self.screen, BG_MID, BG_DARK)
        draw_grid(self.screen, pygame.time.get_ticks())

        t = pygame.time.get_ticks() / 1000.0

        # Big bobbing title
        bob = math.sin(t * 2) * 4
        draw_text(self.screen, "YOU ESCAPED THE LAB!",
                  self.f_huge, NEON_GREEN,
                  WIDTH // 2, 70 + bob, center=True)

        # Golden ratio reveal
        draw_text(self.screen,
                  "The 5 fragments revealed a famous constant:",
                  self.f_text, SOFT, WIDTH // 2, 130, center=True)
        # phi panel
        phi_panel = pygame.Rect(WIDTH//2 - 240, 150, 480, 56)
        draw_neon_panel(self.screen, phi_panel, AMBER,
                        fill=(40, 30, 8))
        draw_text(self.screen, "phi  ~  1.6180   ( the GOLDEN RATIO )",
                  self.f_big, AMBER,
                  phi_panel.centerx, phi_panel.centery, center=True)

        # Stats line
        draw_text(self.screen,
                  f"Final Score: {self.score}    "
                  f"Time Left: {fmt_time(self.time_left)}    "
                  f"Hints Used: {self.hints_used}",
                  self.f_small, WHITE,
                  WIDTH // 2, 226, center=True)

        # CTA banners
        y = 260
        for i, (label, color) in enumerate(CTAS):
            pulse = 1 + 0.015 * math.sin(t * 3 + i * 0.7)
            h = 50
            w = int((WIDTH - 80) * pulse)
            r = pygame.Rect(0, 0, w, h)
            r.center = (WIDTH // 2, y + h // 2)
            pygame.draw.rect(self.screen, color, r, border_radius=14)
            pygame.draw.rect(self.screen, WHITE, r, 2, border_radius=14)
            # readable text colour
            lum = 0.299*color[0] + 0.587*color[1] + 0.114*color[2]
            tcol = BG_DARK if lum > 165 else WHITE
            draw_text(self.screen, label, self.f_med, tcol,
                      WIDTH // 2, y + h // 2, center=True)
            y += h + 10

        draw_text(self.screen,
                  "*  COLLEGE OF SCIENCE, INFORMATION TECHNOLOGY & ENGINEERING  *",
                  self.f_tiny, AMBER,
                  WIDTH // 2, HEIGHT - 70, center=True)

        self.victory_again.draw(self.screen, self.f_text)
        self.victory_quit.draw(self.screen, self.f_text)

    def _handle_victory(self, events, mp):
        self.victory_again.update(mp)
        self.victory_quit.update(mp)
        for e in events:
            if self.victory_again.clicked(e):
                self._reset()
            if self.victory_quit.clicked(e):
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE,
                                                      pygame.K_RETURN):
                self._reset()

    # ---------------------------------------------------------
    # DEFEAT SCREEN
    # ---------------------------------------------------------
    def _draw_defeat(self):
        gradient_bg(self.screen, (40, 8, 14), BG_DARK)
        draw_grid(self.screen, pygame.time.get_ticks())

        t = pygame.time.get_ticks() / 1000.0
        # blinking title
        if int(t * 2) % 2:
            draw_text(self.screen, "TIME EXPIRED",
                      self.f_huge, ALARM_RED,
                      WIDTH // 2, 110, center=True)
        else:
            draw_text(self.screen, "TIME EXPIRED",
                      self.f_huge, RED_DARK,
                      WIDTH // 2, 110, center=True)

        draw_text(self.screen, "The lab remains locked... for now.",
                  self.f_big, SOFT, WIDTH // 2, 180, center=True)
        draw_text(self.screen,
                  f"You collected {len(self.fragments)} of 5 code fragments.",
                  self.f_text, AMBER, WIDTH // 2, 230, center=True)
        draw_text(self.screen,
                  f"Score: {self.score}",
                  self.f_med, WHITE, WIDTH // 2, 265, center=True)

        # Encourage retry
        msg_card = pygame.Rect(80, 320, WIDTH - 160, 140)
        draw_neon_panel(self.screen, msg_card, NEON_CYAN)
        draw_text(self.screen, "Real engineers debug. Try again.",
                  self.f_med, NEON_CYAN,
                  msg_card.centerx, msg_card.y + 35, center=True)
        draw_text(self.screen,
                  "Every CS, IT, and Engineering student fails first,",
                  self.f_text, SOFT,
                  msg_card.centerx, msg_card.y + 75, center=True)
        draw_text(self.screen,
                  "then learns, then builds the future.  Welcome to CSITE.",
                  self.f_text, SOFT,
                  msg_card.centerx, msg_card.y + 100, center=True)

        self.victory_again.label = "Try Again"
        self.victory_again.draw(self.screen, self.f_text)
        self.victory_quit.draw(self.screen, self.f_text)

    def _handle_defeat(self, events, mp):
        self.victory_again.update(mp)
        self.victory_quit.update(mp)
        for e in events:
            if self.victory_again.clicked(e):
                self._reset()
            if self.victory_quit.clicked(e):
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE,
                                                      pygame.K_RETURN):
                self._reset()

    # ---------------------------------------------------------
    # MAIN LOOP
    # ---------------------------------------------------------
    def run(self):
        while True:
            dt     = self.clock.tick(FPS) / 1000.0
            mp     = pygame.mouse.get_pos()
            events = pygame.event.get()

            # Global events (quit + ESC)
            for e in events:
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

            # State dispatch
            if   self.state == "intro":
                self._handle_intro(events, mp);     self._draw_intro()
            elif self.state == "briefing":
                self._handle_briefing(events, mp);  self._draw_briefing()
            elif self.state == "playing":
                self._handle_playing(events, mp, dt); self._draw_playing()
            elif self.state == "unlock":
                self._handle_unlock(events, mp, dt);  self._draw_unlock()
            elif self.state == "victory":
                self._handle_victory(events, mp);     self._draw_victory()
            elif self.state == "defeat":
                self._handle_defeat(events, mp);      self._draw_defeat()

            pygame.display.flip()


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    Game().run()