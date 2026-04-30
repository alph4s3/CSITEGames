"""
CSITE Logic Challenge
=====================
Six interactive logic puzzles for the CSITE booth.
Visitors don't just pick A/B/C/D - they fill truth tables, match
binary numbers, and sort cards by clicking.

PUZZLES
-------
  1. Pattern Sleuth     - Number sequence (Fibonacci, multiple choice)
  2. Syllogism Solver   - Logical reasoning (multiple choice)
  3. Truth Table Lab    - Fill an AND-gate truth table (toggle 0/1)
  4. Binary Match       - Pair binary numbers with their decimals
  5. Algorithm Sort     - Click numbers in ascending order
  6. CS Riddle          - Lateral thinking with a CS twist

CONTROLS
--------
  Mouse              click any button or interactive element
  1-4 / A-D          quick-pick choices on multiple-choice puzzles
  ENTER              submit when the SUBMIT button is enabled
  ESC                quit at any time

RUN
---
  pip install pygame
  python logic_challenge.py
"""

import pygame
import sys
import math
import random


# ============================================================
# CONFIGURATION
# ============================================================
WIDTH, HEIGHT       = 800, 600
FPS                 = 60
QUESTION_TIME_LIMIT = 60.0   # seconds per puzzle (set 0 to disable)

# ----- Colour palette (booth-friendly: blues / purples / greens, gold accent)
DEEP_BLUE  = (15, 30, 60)
DARK_BLUE  = (8,  15, 35)
BLUE       = (60, 140, 230)
BLUE_HI    = (100, 170, 255)
PURPLE     = (140, 100, 220)
PURPLE_HI  = (175, 140, 255)
GREEN      = (80, 220, 130)
GREEN_DK   = (40, 110, 70)
TEAL       = (50, 200, 200)
YELLOW     = (255, 210, 70)
RED        = (255, 110, 110)
RED_DK     = (110, 40, 50)
WHITE      = (245, 245, 250)
SOFT       = (185, 195, 220)
DIM        = (110, 120, 145)
CARD       = (28, 40, 70)
CARD_HI    = (45, 60, 100)


# ============================================================
# SMALL UTILITIES
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


def text_on(bg):
    """Pick a readable text colour given a background colour."""
    lum = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return DARK_BLUE if lum > 165 else WHITE


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


# ============================================================
# UI WIDGETS
# ============================================================
class Button:
    """Rounded-rect button with hover highlight and disabled state."""
    def __init__(self, x, y, w, h, label,
                 color=BLUE, text_color=WHITE, accent=None):
        self.rect       = pygame.Rect(x, y, w, h)
        self.label      = label
        self.color      = color
        self.text_color = text_color
        self.accent     = accent or WHITE
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
            base, border, txt = (30, 40, 70), DIM, DIM
        else:
            base   = (lerp_color(self.color, WHITE, 0.22)
                      if self.hovered else self.color)
            border = self.accent
            txt    = self.text_color
        pygame.draw.rect(surface, base, self.rect, border_radius=12)
        pygame.draw.rect(surface, border, self.rect,
                         width=2, border_radius=12)
        ts = font.render(self.label, True, txt)
        surface.blit(ts, ts.get_rect(center=self.rect.center))


# ============================================================
# PUZZLE BASE CLASS
# ============================================================
class Puzzle:
    """Common interface for every mini-puzzle."""
    def __init__(self):
        self.category    = ""        # tag at top of screen
        self.cat_color   = BLUE      # tag colour
        self.question    = ""
        self.explanation = ""
        self.submitted   = False
        self.correct     = False

    # ----- Subclasses override these ----------------------------
    def can_submit(self):    return True
    def evaluate(self):      return False
    def handle_event(self, event):    pass
    def update(self, dt, mouse_pos):  pass
    def draw_body(self, surface, fonts): pass

    # ----- Shared --------------------------------------------------
    def submit(self):
        if not self.submitted:
            self.correct   = self.evaluate()
            self.submitted = True


# ============================================================
# PUZZLE 1 / 2 / 6 :  multiple-choice puzzle
# ============================================================
class MultipleChoicePuzzle(Puzzle):
    """A 4-option multiple choice puzzle."""
    def __init__(self, category, cat_color, question,
                 choices, correct_idx, explanation):
        super().__init__()
        self.category    = category
        self.cat_color   = cat_color
        self.question    = question
        self.choices     = choices
        self.correct_idx = correct_idx
        self.explanation = explanation
        self.selected    = -1
        self._build_layout()

    def _build_layout(self):
        # 2x2 grid for the four answers.
        bw, bh, gap = 360, 64, 14
        positions = [
            (30,            380),
            (30 + bw + gap, 380),
            (30,            380 + bh + gap),
            (30 + bw + gap, 380 + bh + gap),
        ]
        self.rects = [pygame.Rect(x, y, bw, bh) for (x, y) in positions]

    def can_submit(self):
        return self.selected >= 0

    def evaluate(self):
        return self.selected == self.correct_idx

    def handle_event(self, event):
        if self.submitted:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.selected = i
                    return
        if event.type == pygame.KEYDOWN:
            keymap = {
                pygame.K_1: 0, pygame.K_a: 0,
                pygame.K_2: 1, pygame.K_b: 1,
                pygame.K_3: 2, pygame.K_c: 2,
                pygame.K_4: 3, pygame.K_d: 3,
            }
            if event.key in keymap and keymap[event.key] < len(self.rects):
                self.selected = keymap[event.key]

    def draw_body(self, surface, fonts):
        # ---- Question text (vertically centred above the choice grid)
        lines = wrap_text(self.question, fonts['q'], WIDTH - 80)
        block_h = len(lines) * 30
        y0 = 130 + max(0, (220 - block_h) // 2)
        for i, line in enumerate(lines):
            draw_text(surface, line, fonts['q'], WHITE,
                      WIDTH // 2, y0 + i * 30, center=True)

        # ---- 4 choice buttons (with reveal colours after submit)
        mp = pygame.mouse.get_pos()
        for i, r in enumerate(self.rects):
            if self.submitted:
                if i == self.correct_idx:
                    bg, border = GREEN_DK, GREEN
                elif i == self.selected:
                    bg, border = RED_DK, RED
                else:
                    bg, border = (24, 28, 50), DIM
            elif self.selected == i:
                bg, border = CARD_HI, YELLOW
            elif r.collidepoint(mp):
                bg, border = CARD_HI, TEAL
            else:
                bg, border = CARD, BLUE
            pygame.draw.rect(surface, bg, r, border_radius=12)
            pygame.draw.rect(surface, border, r, width=2, border_radius=12)
            # A/B/C/D badge
            bx, by = r.x + 30, r.centery
            pygame.draw.circle(surface, PURPLE_HI, (bx, by), 18)
            ls = fonts['badge'].render(chr(ord('A') + i), True, WHITE)
            surface.blit(ls, ls.get_rect(center=(bx, by)))
            ts = fonts['text'].render(self.choices[i], True, WHITE)
            surface.blit(ts, (bx + 28, by - ts.get_height() // 2))


# ============================================================
# PUZZLE 3 :  truth-table lab (interactive 0/1 toggles)
# ============================================================
class TruthTablePuzzle(Puzzle):
    """Player fills out a 4-row truth table by clicking 0 or 1 per row."""
    def __init__(self, gate_name, gate_func, explanation):
        super().__init__()
        self.category    = "BINARY LOGIC"
        self.cat_color   = TEAL
        self.gate_name   = gate_name
        self.question    = f"Complete the truth table for {gate_name}:"
        self.explanation = explanation
        self.inputs       = [(0, 0), (0, 1), (1, 0), (1, 1)]
        self.user_answers = [-1, -1, -1, -1]
        self.correct_ans  = [int(gate_func(a, b)) for (a, b) in self.inputs]
        self._build_layout()

    def _build_layout(self):
        self.col_w  = 90
        self.row_h  = 50
        self.tbl_x  = 220       # left edge of table
        self.tbl_y  = 200       # top of header row
        # Two clickable cells per row (0 button, 1 button) on the right
        self.row_btns = []
        for i in range(4):
            y = self.tbl_y + (i + 1) * self.row_h + 5
            r0 = pygame.Rect(self.tbl_x + 3 * self.col_w + 20, y, 40, 40)
            r1 = pygame.Rect(self.tbl_x + 3 * self.col_w + 70, y, 40, 40)
            self.row_btns.append((r0, r1))

    def can_submit(self):
        return all(a >= 0 for a in self.user_answers)

    def evaluate(self):
        return self.user_answers == self.correct_ans

    def handle_event(self, event):
        if self.submitted:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, (r0, r1) in enumerate(self.row_btns):
                if r0.collidepoint(event.pos):
                    self.user_answers[i] = 0; return
                if r1.collidepoint(event.pos):
                    self.user_answers[i] = 1; return

    def draw_body(self, surface, fonts):
        # ---- Question + hint
        draw_text(surface, self.question, fonts['q'], WHITE,
                  WIDTH // 2, 130, center=True)
        draw_text(surface, "Click 0 or 1 in each row, then SUBMIT.",
                  fonts['small'], SOFT, WIDTH // 2, 162, center=True)

        # ---- Header strip (A | B | gate)
        headers = ['A', 'B', self.gate_name]
        for j, h in enumerate(headers):
            cx = self.tbl_x + j * self.col_w + self.col_w // 2
            r  = pygame.Rect(cx - 38, self.tbl_y + 4, 76, 36)
            pygame.draw.rect(surface, BLUE, r, border_radius=8)
            draw_text(surface, h, fonts['med'], WHITE,
                      r.centerx, r.centery, center=True)

        mp = pygame.mouse.get_pos()
        # ---- Rows
        for i, (a, b) in enumerate(self.inputs):
            cy = self.tbl_y + (i + 1) * self.row_h + 25
            # Light row banding
            band = pygame.Rect(self.tbl_x - 6,
                               self.tbl_y + (i + 1) * self.row_h + 2,
                               3 * self.col_w + 14, self.row_h - 2)
            if i % 2 == 0:
                pygame.draw.rect(surface, (22, 32, 56),
                                 band, border_radius=6)
            # A and B values
            for col, val in enumerate([a, b]):
                draw_text(surface, str(val), fonts['med'], WHITE,
                          self.tbl_x + col * self.col_w + self.col_w // 2,
                          cy, center=True)
            # Two answer buttons (0 / 1)
            r0, r1 = self.row_btns[i]
            for val, r in [(0, r0), (1, r1)]:
                if self.submitted:
                    is_pick    = (self.user_answers[i] == val)
                    is_correct = (val == self.correct_ans[i])
                    if is_pick and is_correct:
                        bg, border = GREEN_DK, GREEN
                    elif is_pick and not is_correct:
                        bg, border = RED_DK, RED
                    elif (not is_pick) and is_correct:
                        bg, border = CARD, GREEN     # show right answer
                    else:
                        bg, border = (24, 28, 50), DIM
                elif self.user_answers[i] == val:
                    bg, border = YELLOW, YELLOW
                elif r.collidepoint(mp):
                    bg, border = CARD_HI, TEAL
                else:
                    bg, border = CARD, BLUE
                pygame.draw.rect(surface, bg, r, border_radius=8)
                pygame.draw.rect(surface, border, r, width=2,
                                 border_radius=8)
                draw_text(surface, str(val), fonts['med'], text_on(bg),
                          r.centerx, r.centery, center=True)


# ============================================================
# PUZZLE 4 :  binary <-> decimal matching
# ============================================================
class MatchingPuzzle(Puzzle):
    """
    Click a left card, then click its match on the right.
    Wrong matches flash red and revert; right ones latch green.
    """
    def __init__(self, category, cat_color, question,
                 left_items, right_items, pairs, explanation):
        super().__init__()
        self.category    = category
        self.cat_color   = cat_color
        self.question    = question
        self.explanation = explanation
        self.left_items  = left_items
        self.right_items = right_items
        # pairs is a list of (left_idx, right_idx_in_displayed_order)
        self.pair_set    = set(pairs)
        self.matched     = [-1] * len(left_items)   # matched[L] = R or -1
        self.selected_L  = -1
        self.flash_L     = -1
        self.flash_R     = -1
        self.flash_t     = 0.0
        self._build_layout()

    def _build_layout(self):
        n      = len(self.left_items)
        cw, ch = 140, 50
        gap_y  = 16
        total  = n * ch + (n - 1) * gap_y
        start_y = 200 + max(0, (240 - total) // 2)
        self.left_rects, self.right_rects = [], []
        for i in range(n):
            y = start_y + i * (ch + gap_y)
            self.left_rects.append(pygame.Rect(180, y, cw, ch))
            self.right_rects.append(pygame.Rect(WIDTH - 180 - cw, y, cw, ch))

    def can_submit(self):
        return all(m >= 0 for m in self.matched)

    def evaluate(self):
        return all((L, R) in self.pair_set
                   for L, R in enumerate(self.matched))

    def handle_event(self, event):
        if self.submitted:
            return
        if not (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
            return
        # Click a left card -> select it (only if not yet matched)
        for i, r in enumerate(self.left_rects):
            if r.collidepoint(event.pos):
                if self.matched[i] == -1:
                    self.selected_L = i
                return
        # Click a right card -> try to match
        if self.selected_L >= 0:
            for j, r in enumerate(self.right_rects):
                if not r.collidepoint(event.pos):
                    continue
                if j in self.matched:           # already used
                    return
                if (self.selected_L, j) in self.pair_set:
                    self.matched[self.selected_L] = j
                    self.selected_L = -1
                else:
                    self.flash_L = self.selected_L
                    self.flash_R = j
                    self.flash_t = 0.55
                    self.selected_L = -1
                return

    def update(self, dt, mouse_pos):
        if self.flash_t > 0:
            self.flash_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface, self.question, fonts['q'], WHITE,
                  WIDTH // 2, 130, center=True)
        draw_text(surface,
                  "Click a left card, then click its match on the right.",
                  fonts['small'], SOFT, WIDTH // 2, 162, center=True)

        mp = pygame.mouse.get_pos()
        # ---- Lines for matched pairs (drawn first so cards sit on top)
        for L, R in enumerate(self.matched):
            if R >= 0:
                lr = self.left_rects[L]
                rr = self.right_rects[R]
                pygame.draw.line(surface, GREEN,
                                 (lr.right, lr.centery),
                                 (rr.left,  rr.centery), 3)

        # ---- Left cards
        for i, r in enumerate(self.left_rects):
            matched = self.matched[i] >= 0
            flash   = (self.flash_t > 0 and self.flash_L == i)
            sel     = (self.selected_L == i)
            if flash:                           bg, bd = RED_DK,  RED
            elif matched:                       bg, bd = GREEN_DK, GREEN
            elif sel:                           bg, bd = CARD_HI, YELLOW
            elif r.collidepoint(mp):            bg, bd = CARD_HI, TEAL
            else:                               bg, bd = CARD,    BLUE
            pygame.draw.rect(surface, bg, r, border_radius=10)
            pygame.draw.rect(surface, bd, r, width=2, border_radius=10)
            draw_text(surface, self.left_items[i], fonts['med'], WHITE,
                      r.centerx, r.centery, center=True)
            # tiny header tag
            draw_text(surface, "BINARY", fonts['tiny'], DIM,
                      r.centerx, r.y - 12, center=True)

        # ---- Right cards
        for j, r in enumerate(self.right_rects):
            used  = j in self.matched
            flash = (self.flash_t > 0 and self.flash_R == j)
            if flash:                           bg, bd = RED_DK,  RED
            elif used:                          bg, bd = GREEN_DK, GREEN
            elif (self.selected_L >= 0
                  and r.collidepoint(mp)):       bg, bd = CARD_HI, TEAL
            else:                               bg, bd = CARD,    BLUE
            pygame.draw.rect(surface, bg, r, border_radius=10)
            pygame.draw.rect(surface, bd, r, width=2, border_radius=10)
            draw_text(surface, self.right_items[j], fonts['med'], WHITE,
                      r.centerx, r.centery, center=True)
            draw_text(surface, "DECIMAL", fonts['tiny'], DIM,
                      r.centerx, r.y - 12, center=True)


# ============================================================
# PUZZLE 5 :  algorithm sort (click in ascending order)
# ============================================================
class SortingPuzzle(Puzzle):
    """Click number cards in ascending order; wrong clicks just flash red."""
    def __init__(self, numbers, explanation):
        super().__init__()
        self.category    = "ALGORITHM THINKING"
        self.cat_color   = PURPLE_HI
        self.question    = ("Click the numbers in ASCENDING order "
                            "(smallest first).")
        self.explanation = explanation
        self.numbers     = list(numbers)
        self.target      = sorted(numbers)
        self.clicked     = []      # indices into self.numbers, in click order
        self.flash_idx   = -1
        self.flash_t     = 0.0
        self._build_layout()

    def _build_layout(self):
        n  = len(self.numbers)
        cw, ch, gap = 100, 100, 18
        total_w = n * cw + (n - 1) * gap
        sx = (WIDTH - total_w) // 2
        y  = 290
        self.rects = [pygame.Rect(sx + i * (cw + gap), y, cw, ch)
                      for i in range(n)]

    def can_submit(self):
        return len(self.clicked) == len(self.numbers)

    def evaluate(self):
        return [self.numbers[i] for i in self.clicked] == self.target

    def handle_event(self, event):
        if self.submitted:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if not r.collidepoint(event.pos):
                    continue
                if i in self.clicked:           # already picked
                    return
                next_expected = self.target[len(self.clicked)]
                if self.numbers[i] == next_expected:
                    self.clicked.append(i)
                else:
                    self.flash_idx = i
                    self.flash_t   = 0.45
                return

    def update(self, dt, mouse_pos):
        if self.flash_t > 0:
            self.flash_t -= dt

    def draw_body(self, surface, fonts):
        draw_text(surface, self.question, fonts['q'], WHITE,
                  WIDTH // 2, 130, center=True)
        draw_text(surface, "Wrong clicks flash red and don't count.",
                  fonts['small'], SOFT, WIDTH // 2, 162, center=True)

        # progress
        step = len(self.clicked)
        n    = len(self.numbers)
        draw_text(surface, f"Picked  {step} / {n}", fonts['med'], YELLOW,
                  WIDTH // 2, 220, center=True)

        mp = pygame.mouse.get_pos()
        for i, r in enumerate(self.rects):
            order = self.clicked.index(i) if i in self.clicked else -1
            flash = (self.flash_t > 0 and self.flash_idx == i)
            if flash:                bg, bd = RED_DK,  RED
            elif order >= 0:         bg, bd = GREEN_DK, GREEN
            elif r.collidepoint(mp): bg, bd = CARD_HI, TEAL
            else:                    bg, bd = CARD,    BLUE
            pygame.draw.rect(surface, bg, r, border_radius=14)
            pygame.draw.rect(surface, bd, r, width=3, border_radius=14)
            draw_text(surface, str(self.numbers[i]), fonts['big'], WHITE,
                      r.centerx, r.centery - 6, center=True)
            # order badge
            if order >= 0:
                pygame.draw.circle(surface, YELLOW,
                                   (r.right - 18, r.bottom - 18), 13)
                draw_text(surface, str(order + 1), fonts['small'], DARK_BLUE,
                          r.right - 18, r.bottom - 18, center=True)


# ============================================================
# CALL-TO-ACTION BANNERS for the ending screen
# ============================================================
CTAS = [
    ("LEARN LOGIC.  BUILD THE FUTURE.",       YELLOW),
    ("ENROLL IN CSITE TODAY!",                GREEN),
    ("CODE  *  SOLVE  *  ENGINEER",           TEAL),
    ("THINK LIKE AN ENGINEER -- JOIN CSITE",  PURPLE_HI),
]


# ============================================================
# THE GAME
# ============================================================
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("CSITE Logic Challenge")
        self.clock = pygame.time.Clock()
        self._load_fonts()

        # State machine - 'menu' | 'instructions' | 'playing' | 'feedback' | 'ending'
        self.state   = 'menu'
        self.score   = 0
        self.q_index = 0
        self.q_time  = 0.0

        self.puzzles = []
        self._build_puzzles()

        self._build_buttons()
        self.symbols = self._init_symbols()

    # -------- Setup helpers ----------------------------------
    def _load_fonts(self):
        self.f_huge  = pygame.font.SysFont("arial", 60, bold=True)
        self.f_big   = pygame.font.SysFont("arial", 36, bold=True)
        self.f_med   = pygame.font.SysFont("arial", 24, bold=True)
        self.f_q     = pygame.font.SysFont("arial", 22, bold=True)
        self.f_text  = pygame.font.SysFont("arial", 19)
        self.f_small = pygame.font.SysFont("arial", 16)
        self.f_tiny  = pygame.font.SysFont("arial", 13, bold=True)
        self.f_badge = pygame.font.SysFont("arial", 20, bold=True)

    def _build_puzzles(self):
        """Create the 6 puzzles in order."""
        self.puzzles = []

        # 1. Number sequence (Fibonacci) ----------------------
        self.puzzles.append(MultipleChoicePuzzle(
            category    = "PATTERN RECOGNITION",
            cat_color   = YELLOW,
            question    = ("What number comes next in this sequence?\n"
                           "1, 1, 2, 3, 5, 8, 13, ?"),
            choices     = ["18", "20", "21", "26"],
            correct_idx = 2,
            explanation = ("This is the FIBONACCI sequence - each term is the "
                           "sum of the two before it: 8 + 13 = 21. Fibonacci "
                           "shows up everywhere in nature (flower petals, "
                           "pinecones, galaxy spirals) and in computer science "
                           "as a classic example for recursion and dynamic "
                           "programming."),
        ))

        # 2. Syllogism ----------------------------------------
        self.puzzles.append(MultipleChoicePuzzle(
            category    = "LOGICAL REASONING",
            cat_color   = PURPLE_HI,
            question    = ("All algorithms must terminate.\n"
                           "QuickSort is an algorithm.\n"
                           "Therefore..."),
            choices     = ["QuickSort is fast",
                           "QuickSort must terminate",
                           "All sorts are algorithms",
                           "Fast things must terminate"],
            correct_idx = 1,
            explanation = ("Classic deductive logic (modus ponens): If A "
                           "implies B, and X is A, then X implies B. Engineers "
                           "use formal logic every day to write provably "
                           "correct software, design digital circuits, and "
                           "verify safety-critical systems."),
        ))

        # 3. Truth-table -------------------------------------
        self.puzzles.append(TruthTablePuzzle(
            gate_name   = "A AND B",
            gate_func   = lambda a, b: int(bool(a) and bool(b)),
            explanation = ("The AND gate outputs 1 only when BOTH inputs are 1. "
                           "AND, OR, and NOT gates are the building blocks of "
                           "every computer chip - billions of them, etched in "
                           "silicon, executing your every Google search and "
                           "video stream."),
        ))

        # 4. Binary <-> decimal matching ---------------------
        # left[i] (binary) maps to its decimal value at right[pair_R]
        # right_items are intentionally shuffled.
        self.puzzles.append(MatchingPuzzle(
            category    = "BINARY MATCH",
            cat_color   = TEAL,
            question    = "Match each binary number to its decimal value.",
            left_items  = ["101", "1110", "11", "1001"],   # 5, 14, 3, 9
            right_items = ["3", "5", "9", "14"],
            pairs       = [(0, 1), (1, 3), (2, 0), (3, 2)],
            explanation = ("Binary uses just two digits: 1001 = 8 + 0 + 0 + 1 "
                           "= 9. Computers store EVERYTHING (text, music, "
                           "video, this very game) as long binary strings - "
                           "billions of bits flipped per second."),
        ))

        # 5. Sorting -----------------------------------------
        self.puzzles.append(SortingPuzzle(
            numbers     = [42, 7, 13, 28, 5],
            explanation = ("You just performed selection sort by hand! Sorting "
                           "lets us search and analyze data efficiently. "
                           "QuickSort, MergeSort, and HeapSort all do this in "
                           "different clever ways - choosing the right "
                           "algorithm can make code thousands of times faster."),
        ))

        # 6. CS riddle (lateral thinking) -------------------
        self.puzzles.append(MultipleChoicePuzzle(
            category    = "CS RIDDLE",
            cat_color   = GREEN,
            question    = ("A book has pages numbered 1 to 100.\n"
                           "How many times does the digit '7' appear in total?"),
            choices     = ["10", "11", "19", "20"],
            correct_idx = 3,
            explanation = ("20 times. The digit 7 appears 10 times in the ones "
                           "place (7, 17, 27, ..., 97) and 10 times in the "
                           "tens place (70, 71, ..., 79). Note 77 contains "
                           "two 7s - one counted in each group. Total: 20. "
                           "Engineers count carefully - off-by-one errors "
                           "are a leading cause of software bugs!"),
        ))

    def _build_buttons(self):
        # Main menu
        self.menu_start = Button(WIDTH//2 - 130, 320, 260, 60,
                                 "START GAME", BLUE, accent=YELLOW)
        self.menu_inst  = Button(WIDTH//2 - 130, 395, 260, 50,
                                 "Instructions", CARD_HI, accent=TEAL)
        self.menu_quit  = Button(WIDTH//2 - 130, 460, 260, 50,
                                 "Quit", CARD_HI, accent=DIM)
        # Instructions
        self.inst_back  = Button(40, 530, 110, 45,
                                 "< Back", CARD_HI, accent=DIM)
        self.inst_begin = Button(WIDTH - 220, 525, 180, 55,
                                 "BEGIN", GREEN_DK, accent=GREEN)
        # Playing
        self.submit_btn = Button(WIDTH - 200, 525, 170, 55,
                                 "SUBMIT", BLUE, accent=YELLOW)
        # Feedback
        self.next_btn   = Button(WIDTH//2 - 110, 525, 220, 55,
                                 "NEXT >", BLUE, accent=YELLOW)
        # Ending
        self.end_again  = Button(WIDTH - 200, 540, 170, 45,
                                 "Play Again", BLUE, accent=YELLOW)
        self.end_quit   = Button(30, 540, 110, 45,
                                 "Quit", CARD_HI, accent=DIM)

    def _init_symbols(self):
        """Floating math/CS glyphs for the title + ending screens."""
        labels = ["phi", "pi", "Sigma", "0", "1", "10", "01",
                  "{ }", "->", "fib(n)", "O(n)", "delta", "x^2",
                  "AND", "OR", "if-else"]
        out = []
        for _ in range(18):
            txt   = random.choice(labels)
            size  = random.randint(15, 32)
            f     = pygame.font.SysFont("arial", size, bold=True)
            color = random.choice([BLUE_HI, TEAL, YELLOW, PURPLE_HI])
            surf  = f.render(txt, True, color).convert_alpha()
            surf.set_alpha(random.randint(45, 110))
            out.append({
                'surf': surf,
                'x':    random.uniform(0, WIDTH),
                'y':    random.uniform(0, HEIGHT),
                'vx':   random.uniform(-10, 10),
                'vy':   random.uniform(-22, -6),
            })
        return out

    # -------- Game-flow helpers ------------------------------
    def _start_question(self):
        self.q_time = QUESTION_TIME_LIMIT

    def _on_submit(self):
        """Submit current puzzle, score it, switch to feedback state."""
        p = self.puzzles[self.q_index]
        if p.submitted or not p.can_submit():
            return
        p.submit()
        if p.correct:
            time_bonus = max(0, int(self.q_time * 3))   # up to ~180
            self.score += 100 + time_bonus
        self.state = 'feedback'

    def _next_question(self):
        self.q_index += 1
        if self.q_index >= len(self.puzzles):
            self.state = 'ending'
        else:
            self._start_question()
            self.state = 'playing'

    def _reset(self):
        # Rebuild puzzles to clear all per-question state.
        self._build_puzzles()
        self.score   = 0
        self.q_index = 0
        self._start_question()
        self.state = 'playing'

    # -------- Decoration ------------------------------------
    def _update_symbols(self, dt):
        for s in self.symbols:
            s['x'] += s['vx'] * dt
            s['y'] += s['vy'] * dt
            if s['y'] < -50:
                s['y'] = HEIGHT + 30
                s['x'] = random.uniform(0, WIDTH)
            if s['x'] < -50:
                s['x'] = WIDTH + 30
            elif s['x'] > WIDTH + 50:
                s['x'] = -30

    def _draw_symbols(self):
        for s in self.symbols:
            self.screen.blit(s['surf'], (s['x'], s['y']))

    # -------- MAIN MENU --------------------------------------
    def _draw_menu(self):
        gradient_bg(self.screen, DEEP_BLUE, DARK_BLUE)
        self._draw_symbols()

        # Pulsing halo behind title
        t_ms  = pygame.time.get_ticks()
        pulse = 0.5 + 0.5 * math.sin(t_ms / 700)
        halo  = pygame.Surface((WIDTH, 200), pygame.SRCALPHA)
        pygame.draw.ellipse(
            halo, (BLUE[0], BLUE[1], BLUE[2], int(40 + 40 * pulse)),
            halo.get_rect().inflate(-100, -50))
        self.screen.blit(halo, (0, 80))

        draw_text(self.screen, "CSITE", self.f_huge, YELLOW,
                  WIDTH // 2, 130, center=True)
        draw_text(self.screen, "LOGIC CHALLENGE", self.f_big, TEAL,
                  WIDTH // 2, 200, center=True)
        draw_text(self.screen,
                  "6 puzzles. One question - how do you think?",
                  self.f_small, SOFT, WIDTH // 2, 260, center=True)

        self.menu_start.draw(self.screen, self.f_med)
        self.menu_inst.draw(self.screen, self.f_text)
        self.menu_quit.draw(self.screen, self.f_text)

        draw_text(self.screen,
                  "College of Science, Information Technology & Engineering",
                  self.f_tiny, DIM, WIDTH // 2, HEIGHT - 22, center=True)

    def _handle_menu(self, events, mp):
        for b in (self.menu_start, self.menu_inst, self.menu_quit):
            b.update(mp)
        for e in events:
            if self.menu_start.clicked(e):
                self._reset()
            if self.menu_inst.clicked(e):
                self.state = 'instructions'
            if self.menu_quit.clicked(e):
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN,
                                                      pygame.K_SPACE):
                self._reset()

    # -------- INSTRUCTIONS -----------------------------------
    def _draw_instructions(self):
        gradient_bg(self.screen, DEEP_BLUE, DARK_BLUE)
        draw_text(self.screen, "HOW TO PLAY", self.f_big, YELLOW,
                  WIDTH // 2, 60, center=True)

        card = pygame.Rect(50, 110, WIDTH - 100, 390)
        pygame.draw.rect(self.screen, CARD, card, border_radius=18)
        pygame.draw.rect(self.screen, BLUE, card, width=2, border_radius=18)

        rules = [
            "6 short logic puzzles - sequences, gates, sorting, riddles.",
            f"You have {int(QUESTION_TIME_LIMIT)} seconds for each puzzle.",
            "Some puzzles are click-to-pick; others are interactive.",
            "Click the SUBMIT button (or press ENTER) when you're ready.",
            "Faster correct answers earn bigger time bonuses.",
            "Each answer is followed by a short explanation - that's the prize.",
            "Press ESC at any time to quit.",
        ]
        y = 145
        for line in rules:
            # Diamond bullet
            pts = [(card.x + 35, y + 13), (card.x + 47, y + 25),
                   (card.x + 35, y + 37), (card.x + 23, y + 25)]
            pygame.draw.polygon(self.screen, YELLOW, pts)
            draw_text(self.screen, line, self.f_text, WHITE,
                      card.x + 70, y + 8)
            y += 46

        # Discipline tags
        tags = [("LOGIC",    PURPLE_HI),
                ("BINARY",   TEAL),
                ("ALGORITHM", BLUE_HI),
                ("FIBONACCI", YELLOW)]
        tx = card.x + 35
        ty = card.y + card.height - 50
        for label, color in tags:
            tw = self.f_small.size(label)[0] + 24
            r  = pygame.Rect(tx, ty, tw, 28)
            pygame.draw.rect(self.screen, color, r, border_radius=14)
            draw_text(self.screen, label, self.f_small, DARK_BLUE,
                      r.centerx, r.centery, center=True)
            tx += tw + 10

        self.inst_back.draw(self.screen, self.f_text)
        self.inst_begin.draw(self.screen, self.f_med)

    def _handle_instructions(self, events, mp):
        self.inst_back.update(mp)
        self.inst_begin.update(mp)
        for e in events:
            if self.inst_back.clicked(e):
                self.state = 'menu'
            if self.inst_begin.clicked(e):
                self._reset()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_RETURN,
                                                      pygame.K_SPACE):
                self._reset()

    # -------- PLAYING ----------------------------------------
    def _draw_top_bar(self):
        pygame.draw.rect(self.screen, (10, 16, 36), (0, 0, WIDTH, 56))
        pygame.draw.line(self.screen, BLUE, (0, 56), (WIDTH, 56), 2)
        # Counter (left)
        draw_text(self.screen,
                  f"Puzzle {self.q_index + 1} / {len(self.puzzles)}",
                  self.f_med, WHITE, 20, 16)
        # Score (right)
        sl = f"Score: {self.score}"
        sw = self.f_med.size(sl)[0]
        draw_text(self.screen, sl, self.f_med, YELLOW, WIDTH - 20 - sw, 16)
        # Timer bar (centre)
        tx, ty, tw, th = WIDTH // 2 - 100, 22, 200, 14
        pygame.draw.rect(self.screen, CARD, (tx, ty, tw, th),
                         border_radius=7)
        if QUESTION_TIME_LIMIT > 0:
            frac = max(0.0, min(1.0, self.q_time / QUESTION_TIME_LIMIT))
            color = (GREEN if frac > 0.5 else
                     (YELLOW if frac > 0.25 else RED))
            fw = max(0, int(tw * frac))
            if fw > 0:
                pygame.draw.rect(self.screen, color, (tx, ty, fw, th),
                                 border_radius=7)
            pygame.draw.rect(self.screen, WHITE, (tx, ty, tw, th),
                             width=1, border_radius=7)
            draw_text(self.screen, f"{int(math.ceil(self.q_time))}s",
                      self.f_small, WHITE, tx + tw // 2, ty + th + 10,
                      center=True)

    def _draw_playing(self):
        gradient_bg(self.screen, DEEP_BLUE, DARK_BLUE)
        self._draw_top_bar()
        p = self.puzzles[self.q_index]

        # Category badge
        tag_w = self.f_tiny.size(p.category)[0] + 28
        tag_r = pygame.Rect(WIDTH // 2 - tag_w // 2, 70, tag_w, 24)
        pygame.draw.rect(self.screen, p.cat_color, tag_r, border_radius=12)
        draw_text(self.screen, p.category, self.f_tiny, DARK_BLUE,
                  tag_r.centerx, tag_r.centery, center=True)

        # Body (puzzle-specific)
        fonts = {'q': self.f_q, 'big': self.f_big, 'med': self.f_med,
                 'text': self.f_text, 'small': self.f_small,
                 'tiny': self.f_tiny, 'badge': self.f_badge}
        p.draw_body(self.screen, fonts)

        # Submit button
        self.submit_btn.disabled = not p.can_submit()
        self.submit_btn.draw(self.screen, self.f_med)

        # Hint strip
        draw_text(self.screen, "ENTER = submit  *  ESC = quit",
                  self.f_small, DIM, 20, HEIGHT - 18)

    def _handle_playing(self, events, mp, dt):
        p = self.puzzles[self.q_index]

        # Timer
        if QUESTION_TIME_LIMIT > 0:
            self.q_time -= dt
            if self.q_time <= 0:
                self.q_time = 0
                p.submit()                       # likely wrong (incomplete)
                if p.correct:
                    self.score += 100
                self.state = 'feedback'
                return

        # Update puzzle (handles internal animations like flash timers)
        p.update(dt, mp)

        # Submit button hover
        self.submit_btn.update(mp)

        for e in events:
            p.handle_event(e)
            if self.submit_btn.clicked(e):
                self._on_submit()
                return
            if (e.type == pygame.KEYDOWN
                and e.key in (pygame.K_RETURN,)
                and p.can_submit()):
                self._on_submit()
                return

    # -------- FEEDBACK ---------------------------------------
    def _draw_feedback(self):
        gradient_bg(self.screen, DEEP_BLUE, DARK_BLUE)
        self._draw_top_bar()
        p = self.puzzles[self.q_index]

        if p.correct:
            color, label, sub = GREEN, "CORRECT!", "Nice thinking!"
        else:
            color, label, sub = RED, "NOT QUITE", "Check the explanation below."

        # Translucent banner
        tint = pygame.Surface((WIDTH, 90), pygame.SRCALPHA)
        tint.fill((color[0], color[1], color[2], 36))
        self.screen.blit(tint, (0, 70))
        pygame.draw.line(self.screen, color, (0, 70),  (WIDTH, 70),  2)
        pygame.draw.line(self.screen, color, (0, 160), (WIDTH, 160), 2)
        draw_text(self.screen, label, self.f_big, color,
                  WIDTH // 2, 100, center=True)
        draw_text(self.screen, sub, self.f_med, WHITE,
                  WIDTH // 2, 138, center=True)

        # Explanation card
        card = pygame.Rect(40, 185, WIDTH - 80, 300)
        pygame.draw.rect(self.screen, CARD, card, border_radius=18)
        pygame.draw.rect(self.screen, p.cat_color, card,
                         width=2, border_radius=18)
        draw_text(self.screen, "WHY IT MATTERS", self.f_med, p.cat_color,
                  card.x + 24, card.y + 18)
        draw_wrapped(self.screen, p.explanation, self.f_text, SOFT,
                     x=card.x + 24, y=card.y + 60,
                     line_h=26, max_width=card.width - 48)

        # Next button (label changes for last puzzle)
        if self.q_index == len(self.puzzles) - 1:
            self.next_btn.label = "SEE RESULTS >"
        else:
            self.next_btn.label = "NEXT >"
        self.next_btn.draw(self.screen, self.f_med)

        hint = ("SPACE / ENTER for results"
                if self.q_index == len(self.puzzles) - 1
                else "SPACE / ENTER to continue")
        hw = self.f_small.size(hint)[0]
        draw_text(self.screen, hint, self.f_small, DIM,
                  WIDTH - 30 - hw, 545)

    def _handle_feedback(self, events, mp):
        self.next_btn.update(mp)
        for e in events:
            if self.next_btn.clicked(e):
                self._next_question()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE,
                                                      pygame.K_RETURN):
                self._next_question()

    # -------- ENDING -----------------------------------------
    def _rank(self):
        max_per = 100 + int(QUESTION_TIME_LIMIT * 3)
        max_total = max_per * len(self.puzzles)
        pct = self.score / max_total if max_total else 0
        if pct >= 0.85: return "CSITE GENIUS!",   YELLOW
        if pct >= 0.6:  return "FUTURE ENGINEER", TEAL
        if pct >= 0.3:  return "LOGICAL THINKER", PURPLE_HI
        return                "CURIOUS BEGINNER", GREEN

    def _draw_ending(self):
        gradient_bg(self.screen, DEEP_BLUE, DARK_BLUE)
        self._draw_symbols()

        t = pygame.time.get_ticks() / 1000.0
        bob = math.sin(t * 2) * 4
        draw_text(self.screen, "WELL DONE!", self.f_huge, YELLOW,
                  WIDTH // 2, 60 + bob, center=True)

        draw_text(self.screen, f"Final Score: {self.score}",
                  self.f_big, WHITE, WIDTH // 2, 125, center=True)

        rank, rcolor = self._rank()
        rw = self.f_med.size(rank)[0] + 40
        rr = pygame.Rect(WIDTH // 2 - rw // 2, 170, rw, 38)
        pygame.draw.rect(self.screen, rcolor, rr, border_radius=19)
        draw_text(self.screen, rank, self.f_med, DARK_BLUE,
                  rr.centerx, rr.centery, center=True)

        # CTA banners (subtle pulse)
        y = 235
        for i, (label, color) in enumerate(CTAS):
            pulse = 1 + 0.015 * math.sin(t * 3 + i * 0.7)
            h = 50
            w = int((WIDTH - 80) * pulse)
            r = pygame.Rect(0, 0, w, h)
            r.center = (WIDTH // 2, y + h // 2)
            pygame.draw.rect(self.screen, color, r, border_radius=14)
            pygame.draw.rect(self.screen, WHITE, r, width=2,
                             border_radius=14)
            draw_text(self.screen, label, self.f_med, text_on(color),
                      WIDTH // 2, y + h // 2, center=True)
            y += h + 10

        draw_text(self.screen,
                  "*  COLLEGE OF SCIENCE, INFORMATION TECHNOLOGY & ENGINEERING  *",
                  self.f_tiny, YELLOW, WIDTH // 2, HEIGHT - 75, center=True)

        self.end_again.draw(self.screen, self.f_text)
        self.end_quit.draw(self.screen, self.f_text)

    def _handle_ending(self, events, mp):
        self.end_again.update(mp)
        self.end_quit.update(mp)
        for e in events:
            if self.end_again.clicked(e):
                self._reset()
            if self.end_quit.clicked(e):
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE,
                                                      pygame.K_RETURN):
                self._reset()

    # -------- MAIN LOOP --------------------------------------
    def run(self):
        while True:
            dt     = self.clock.tick(FPS) / 1000.0
            mp     = pygame.mouse.get_pos()
            events = pygame.event.get()

            # Global events
            for e in events:
                if e.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

            # Background animation only on menu/ending
            if self.state in ('menu', 'ending'):
                self._update_symbols(dt)

            # State dispatch
            if   self.state == 'menu':
                self._handle_menu(events, mp);          self._draw_menu()
            elif self.state == 'instructions':
                self._handle_instructions(events, mp);  self._draw_instructions()
            elif self.state == 'playing':
                self._handle_playing(events, mp, dt);   self._draw_playing()
            elif self.state == 'feedback':
                self._handle_feedback(events, mp);      self._draw_feedback()
            elif self.state == 'ending':
                self._handle_ending(events, mp);        self._draw_ending()

            pygame.display.flip()


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    Game().run()