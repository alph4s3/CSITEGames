"""
CSITE Career Booth — Game 5: BINARY CODE BREAKER
=================================================
A logic / brain-teaser game with a Computer-Science theme.

How computers think
-------------------
Every photo, song, message and game on a computer is just a long
list of 1s and 0s.  This game turns that idea into a puzzle.

Modes
-----
  BUILDER : A decimal number appears.  Toggle the 8 bits ON or OFF
            to make their place-values add up to the target.
            (128, 64, 32, 16, 8, 4, 2, 1)
  DECODER : A binary number appears.  Type the matching decimal.
  ASCII   : A letter appears.  Build the 8-bit ASCII code for it.
            (Refer to the cheat-sheet pop-up if you forget.)

Each round has a 30-second timer; quicker answers earn more points.
After 10 rounds your final score & rank are shown.

Controls : Mouse to toggle bits / press buttons.  Digits + ENTER
           in DECODER mode.  ESC quits.
Resolution: 1024×768
"""

import pygame
import random
import sys
import math

pygame.init()
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CSITE — Binary Code Breaker")
clock = pygame.time.Clock()

# ---- colours ---- #
BG_TOP, BG_BOT = (8, 12, 30), (24, 32, 70)
WHITE = (245, 245, 250)
SOFT  = (190, 200, 220)
DIM   = (130, 140, 160)
GOLD  = (255, 200, 60)
GREEN = (90, 220, 130)
RED   = (255, 110, 110)
BLUE  = (80, 140, 255)
PURPLE= (180, 100, 220)
TEAL  = (60, 200, 200)
NEON  = (50, 255, 180)

# ---- fonts ---- #
F_TITLE = pygame.font.SysFont("arial", 50, bold=True)
F_BIG   = pygame.font.SysFont("arial", 36, bold=True)
F_MED   = pygame.font.SysFont("arial", 26)
F_SMALL = pygame.font.SysFont("arial", 20)
F_TINY  = pygame.font.SysFont("arial", 16)
F_MONO  = pygame.font.SysFont("couriernew", 28, bold=True)
F_BIG_MONO = pygame.font.SysFont("couriernew", 56, bold=True)

# ---- helpers ---- #
def gradient_bg():
    for y in range(HEIGHT):
        t = y / HEIGHT
        col = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t)
                    for i in range(3))
        pygame.draw.line(screen, col, (0, y), (WIDTH, y))


def draw_text(text, font, color, x, y, center=False):
    s = font.render(text, True, color)
    r = s.get_rect()
    if center: r.center = (x, y)
    else:      r.topleft = (x, y)
    screen.blit(s, r)


class Button:
    def __init__(self, x, y, w, h, label, color=BLUE, font=F_MED):
        self.rect, self.label, self.color, self.font = (
            pygame.Rect(x, y, w, h), label, color, font)
    def draw(self, mp, disabled=False):
        hover = self.rect.collidepoint(mp) and not disabled
        c = (60, 60, 80) if disabled else (
            self.color if not hover
            else tuple(min(255, v+35) for v in self.color))
        pygame.draw.rect(screen, c, self.rect, border_radius=10)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=10)
        draw_text(self.label, self.font, WHITE,
                  self.rect.centerx, self.rect.centery, center=True)
    def clicked(self, ev, disabled=False):
        return (not disabled and ev.type == pygame.MOUSEBUTTONDOWN
                and ev.button == 1 and self.rect.collidepoint(ev.pos))


# --------------------------------------------------------------------- #
#  Bits: 8-bit display
# --------------------------------------------------------------------- #
BIT_W, BIT_H = 90, 90
BIT_GAP      = 12
BITS_TOTAL_W = 8 * BIT_W + 7 * BIT_GAP
BITS_X       = WIDTH // 2 - BITS_TOTAL_W // 2
BITS_Y       = 315

PLACE_VALUES = [128, 64, 32, 16, 8, 4, 2, 1]


def bit_rect(i):
    return pygame.Rect(BITS_X + i * (BIT_W + BIT_GAP),
                       BITS_Y, BIT_W, BIT_H)


def draw_bits(bits, interactive=True, glow_correct=False, target=None):
    """Render the 8-bit row.  bits is a list of 0/1 values."""
    # Place-value labels above
    for i in range(8):
        r = bit_rect(i)
        draw_text(str(PLACE_VALUES[i]), F_SMALL, GOLD,
                  r.centerx, r.y - 42, center=True)
        # bit position label below
        draw_text(f"b{7-i}", F_TINY, DIM,
                  r.centerx, r.bottom + 10, center=True)

    # Bit boxes
    for i in range(8):
        r = bit_rect(i)
        on = bits[i] == 1
        col = NEON if on else (40, 50, 80)
        # glow when on
        if on:
            for k in range(8, 0, -2):
                s = pygame.Surface((BIT_W + 2*k, BIT_H + 2*k),
                                   pygame.SRCALPHA)
                pygame.draw.rect(s, (*NEON, 16),
                                 s.get_rect(), border_radius=14)
                screen.blit(s, (r.x - k, r.y - k))
        pygame.draw.rect(screen, col, r, border_radius=10)
        pygame.draw.rect(screen, WHITE, r, 2, border_radius=10)
        draw_text("1" if on else "0", F_BIG_MONO,
                  WHITE if on else SOFT,
                  r.centerx, r.centery, center=True)


def bits_to_int(bits):
    return sum(b * v for b, v in zip(bits, PLACE_VALUES))


def int_to_bits(n):
    return [(n >> (7 - i)) & 1 for i in range(8)]


# --------------------------------------------------------------------- #
#  Game state
# --------------------------------------------------------------------- #
mode = "menu"             # menu / builder / decoder / ascii / over

bits = [0] * 8
target = 0
target_char = ""
typed = ""

round_n     = 0
ROUNDS      = 10
score       = 0
streak      = 0
round_time  = 0.0
ROUND_TIME  = 30.0
msg         = ""
msg_timer   = 0
msg_color   = WHITE

show_ascii_help = False

# --------------------------------------------------------------------- #
#  Round generation
# --------------------------------------------------------------------- #
def new_round_builder():
    global target, bits, round_time
    target = random.randint(1, 255)
    bits = [0] * 8
    round_time = ROUND_TIME

def new_round_decoder():
    global target, bits, typed, round_time
    target = random.randint(1, 255)
    bits = int_to_bits(target)         # shown to player
    typed = ""
    round_time = ROUND_TIME

def new_round_ascii():
    global target, target_char, bits, round_time
    target_char = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                                "abcdefghijklmnopqrstuvwxyz0123456789")
    target = ord(target_char)
    bits = [0] * 8
    round_time = ROUND_TIME

def new_round():
    if mode == "builder":   new_round_builder()
    elif mode == "decoder": new_round_decoder()
    elif mode == "ascii":   new_round_ascii()


def start_game(new_mode):
    global mode, round_n, score, streak, msg, msg_timer
    mode = new_mode
    round_n = 1
    score = 0
    streak = 0
    msg = ""
    msg_timer = 0
    new_round()


def submit_answer():
    """Check current attempt, advance round."""
    global score, streak, msg, msg_timer, msg_color, round_n, mode

    if mode == "builder":
        ok = bits_to_int(bits) == target
    elif mode == "decoder":
        try:
            ok = int(typed) == target
        except ValueError:
            ok = False
    elif mode == "ascii":
        ok = bits_to_int(bits) == target
    else:
        ok = False

    if ok:
        time_bonus = int(round_time * 5)
        streak_bonus = streak * 20
        gained = 100 + time_bonus + streak_bonus
        score += gained
        streak += 1
        msg = f"✓ +{gained}  (time bonus {time_bonus}, streak ×{streak})"
        msg_color = GREEN
    else:
        streak = 0
        msg = f"✗ Wrong — answer was {target}"
        msg_color = RED
    msg_timer = 120

    round_n += 1
    if round_n > ROUNDS:
        mode = "over"
    else:
        new_round()


def time_out():
    global msg, msg_color, msg_timer, streak, round_n, mode
    streak = 0
    msg = f"⌛ Time! answer was {target}"
    msg_color = RED
    msg_timer = 120
    round_n += 1
    if round_n > ROUNDS:
        mode = "over"
    else:
        new_round()


# --------------------------------------------------------------------- #
#  Buttons
# --------------------------------------------------------------------- #
btn_builder = Button(WIDTH//2 - 230, 280, 460, 60, "1. BIT BUILDER  (decimal → binary)", BLUE)
btn_decoder = Button(WIDTH//2 - 230, 360, 460, 60, "2. DECODER     (binary → decimal)", PURPLE)
btn_ascii   = Button(WIDTH//2 - 230, 440, 460, 60, "3. ASCII MODE  (letter → 8 bits)",  GREEN)

btn_back    = Button(20, 20, 110, 40, "← Menu", (90, 90, 110), F_SMALL)
btn_submit  = Button(WIDTH//2 - 110, 540, 220, 55, "SUBMIT", GOLD, F_MED)
btn_help    = Button(WIDTH - 160, 20, 140, 40, "ASCII Cheat", TEAL, F_SMALL)
btn_again   = Button(WIDTH//2 - 110, 470, 220, 55, "PLAY AGAIN", GREEN, F_MED)


# --------------------------------------------------------------------- #
#  Drawing
# --------------------------------------------------------------------- #
def draw_menu(mp):
    gradient_bg()
    # decorative falling 1s and 0s
    random.seed(int(pygame.time.get_ticks() / 150) % 1000)
    for _ in range(60):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT)
        ch = random.choice("01")
        c = NEON if ch == "1" else (60, 80, 110)
        draw_text(ch, F_MONO, c, x, y)

    draw_text("BINARY CODE BREAKER", F_TITLE, NEON,
              WIDTH//2, 110, center=True)
    draw_text("Speak fluent computer.  Convert numbers between bases.",
              F_MED, SOFT, WIDTH//2, 175, center=True)
    draw_text("CSITE Booth — How computers think",
              F_SMALL, DIM, WIDTH//2, 215, center=True)
    btn_builder.draw(mp)
    btn_decoder.draw(mp)
    btn_ascii.draw(mp)
    draw_text("ESC to quit", F_TINY, DIM,
              WIDTH//2, HEIGHT - 30, center=True)


def draw_top_bar(mp):
    # Round / score / time
    bar = pygame.Rect(60, 70, WIDTH - 120, 60)
    pygame.draw.rect(screen, (15, 22, 50), bar, border_radius=10)
    pygame.draw.rect(screen, BLUE, bar, 2, border_radius=10)
    draw_text(f"Round {round_n}/{ROUNDS}", F_MED, GOLD,
              bar.x + 16, bar.y + 16)
    draw_text(f"Score {score}", F_MED, GREEN,
              bar.x + 200, bar.y + 16)
    draw_text(f"Streak ×{streak}", F_MED, PURPLE,
              bar.x + 380, bar.y + 16)

    # Timer bar
    tw = bar.width - 540
    bg = pygame.Rect(bar.x + 520, bar.y + 22, tw - 14, 22)
    pygame.draw.rect(screen, (40, 50, 80), bg, border_radius=6)
    frac = max(0, round_time / ROUND_TIME)
    fg = pygame.Rect(bg.x, bg.y, int(bg.width * frac), bg.height)
    col = GREEN if frac > 0.5 else GOLD if frac > 0.25 else RED
    pygame.draw.rect(screen, col, fg, border_radius=6)
    draw_text(f"{round_time:4.1f}s", F_SMALL, WHITE,
              bg.right - 30, bg.y - 1)


def draw_builder(mp):
    gradient_bg()
    draw_top_bar(mp)
    btn_back.draw(mp)
    btn_help.draw(mp)

    # Target display
    box = pygame.Rect(WIDTH//2 - 220, 150, 440, 110)
    pygame.draw.rect(screen, (10, 16, 38), box, border_radius=12)
    pygame.draw.rect(screen, GOLD, box, 3, border_radius=12)
    draw_text("BUILD THIS NUMBER:", F_SMALL, SOFT,
              box.centerx, box.y + 14, center=True)
    draw_text(str(target), F_BIG_MONO, GOLD,
              box.centerx, box.y + 70, center=True)

    draw_bits(bits)

    # Live total
    cur = bits_to_int(bits)
    col = GREEN if cur == target else (RED if cur > target else WHITE)
    draw_text(f"Current sum: {cur}", F_MED, col,
              WIDTH//2, 450, center=True)

    btn_submit.draw(mp)
    draw_message()


def draw_decoder(mp):
    gradient_bg()
    draw_top_bar(mp)
    btn_back.draw(mp)
    btn_help.draw(mp)

    draw_text("READ THE BINARY:", F_MED, SOFT,
              WIDTH//2, 165, center=True)

    # bits non-interactive
    draw_bits(bits, interactive=False)

    # input box
    box = pygame.Rect(WIDTH//2 - 200, 430, 400, 80)
    pygame.draw.rect(screen, (10, 16, 38), box, border_radius=12)
    pygame.draw.rect(screen, GOLD, box, 3, border_radius=12)
    txt = typed if typed else "type the decimal…"
    col = WHITE if typed else DIM
    draw_text(txt, F_BIG_MONO, col,
              box.centerx, box.centery, center=True)

    draw_text("Press ENTER or click SUBMIT",
              F_TINY, DIM, WIDTH//2, 520, center=True)

    btn_submit.draw(mp)
    draw_message()


def draw_ascii(mp):
    gradient_bg()
    draw_top_bar(mp)
    btn_back.draw(mp)
    btn_help.draw(mp)

    box = pygame.Rect(WIDTH//2 - 220, 150, 440, 110)
    pygame.draw.rect(screen, (10, 16, 38), box, border_radius=12)
    pygame.draw.rect(screen, NEON, box, 3, border_radius=12)
    draw_text("ENCODE THIS LETTER (8-bit ASCII):",
              F_SMALL, SOFT, box.centerx, box.y + 14, center=True)
    draw_text(f"'{target_char}'", F_BIG_MONO, NEON,
              box.centerx - 70, box.y + 70, center=True)
    draw_text(f"= {target}", F_MED, GOLD,
              box.centerx + 50, box.y + 70, center=True)

    draw_bits(bits)
    cur = bits_to_int(bits)
    col = GREEN if cur == target else (RED if cur > target else WHITE)
    draw_text(f"Current value: {cur}", F_MED, col,
              WIDTH//2, 410, center=True)

    btn_submit.draw(mp)
    draw_message()


def draw_ascii_help():
    """Cheat-sheet popup."""
    box = pygame.Rect(140, 90, WIDTH - 280, HEIGHT - 200)
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    s.fill((0, 0, 0, 150))
    screen.blit(s, (0, 0))
    pygame.draw.rect(screen, (15, 22, 50), box, border_radius=12)
    pygame.draw.rect(screen, GOLD, box, 3, border_radius=12)
    draw_text("ASCII CHEAT-SHEET", F_BIG, GOLD,
              box.centerx, box.y + 24, center=True)
    draw_text("Click anywhere to close", F_SMALL, DIM,
              box.centerx, box.y + 60, center=True)

    # Three columns: A-Z, a-z, digits
    col_x = [box.x + 60, box.x + 280, box.x + 500]
    headers = ["A–Z", "a–z", "0–9"]
    for i, h in enumerate(headers):
        draw_text(h, F_MED, NEON, col_x[i], box.y + 90)

    # ranges
    rngA = list(range(ord('A'), ord('Z') + 1))   # 26
    rnga = list(range(ord('a'), ord('z') + 1))   # 26
    rng0 = list(range(ord('0'), ord('9') + 1))   # 10
    for i, n in enumerate(rngA):
        if i >= 13: y = box.y + 130 + (i-13) * 22; xoff = 100
        else:       y = box.y + 130 + i * 22;     xoff = 0
        draw_text(f"{chr(n)} = {n}",
                  F_TINY, WHITE, col_x[0] + xoff, y)
    for i, n in enumerate(rnga):
        if i >= 13: y = box.y + 130 + (i-13) * 22; xoff = 100
        else:       y = box.y + 130 + i * 22;     xoff = 0
        draw_text(f"{chr(n)} = {n}",
                  F_TINY, WHITE, col_x[1] + xoff, y)
    for i, n in enumerate(rng0):
        y = box.y + 130 + i * 22
        draw_text(f"{chr(n)} = {n}",
                  F_TINY, WHITE, col_x[2], y)


def draw_message():
    if msg_timer > 0 and msg:
        rect = pygame.Rect(60, HEIGHT - 110, WIDTH - 120, 60)
        pygame.draw.rect(screen, (15, 22, 50), rect, border_radius=10)
        pygame.draw.rect(screen, msg_color, rect, 3, border_radius=10)
        draw_text(msg, F_MED, msg_color,
                  rect.centerx, rect.centery, center=True)


def rank_for(score):
    if score >= 6000:  return "★★★ ELITE  HACKER"
    if score >= 4000:  return "★★  CODE BREAKER"
    if score >= 2000:  return "★   APPRENTICE"
    return "TRAINEE"


def draw_over(mp):
    gradient_bg()
    draw_text("GAME OVER", F_TITLE, GOLD,
              WIDTH//2, 150, center=True)
    box = pygame.Rect(WIDTH//2 - 240, 230, 480, 200)
    pygame.draw.rect(screen, (15, 22, 50), box, border_radius=12)
    pygame.draw.rect(screen, GOLD, box, 3, border_radius=12)
    draw_text(f"Final Score:  {score}", F_BIG, GREEN,
              box.centerx, box.y + 60, center=True)
    draw_text(rank_for(score), F_MED, NEON,
              box.centerx, box.y + 130, center=True)
    btn_again.draw(mp)
    btn_back.draw(mp)


# --------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------- #
def main():
    global mode, bits, typed, round_time, msg_timer
    global show_ascii_help, round_n, score, streak

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mp = pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False

            # ASCII help overlay closes on any click
            if show_ascii_help:
                if ev.type == pygame.MOUSEBUTTONDOWN:
                    show_ascii_help = False
                continue

            if mode == "menu":
                if btn_builder.clicked(ev): start_game("builder")
                if btn_decoder.clicked(ev): start_game("decoder")
                if btn_ascii.clicked(ev):   start_game("ascii")

            elif mode in ("builder", "decoder", "ascii"):
                if btn_back.clicked(ev): mode = "menu"
                if btn_help.clicked(ev): show_ascii_help = True

                # Toggle bits in builder/ascii
                if mode in ("builder", "ascii"):
                    if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                        for i in range(8):
                            if bit_rect(i).collidepoint(ev.pos):
                                bits[i] ^= 1

                if mode == "decoder":
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_RETURN and typed:
                            submit_answer()
                        elif ev.key == pygame.K_BACKSPACE:
                            typed = typed[:-1]
                        elif ev.unicode.isdigit() and len(typed) < 4:
                            typed += ev.unicode

                if btn_submit.clicked(ev):
                    submit_answer()

            elif mode == "over":
                if btn_again.clicked(ev): start_game("builder")
                if btn_back.clicked(ev):  mode = "menu"

        # Tick the round timer
        if mode in ("builder", "decoder", "ascii"):
            round_time -= dt
            if round_time <= 0:
                time_out()

        if msg_timer > 0:
            msg_timer -= 1

        # ---- draw ---- #
        if mode == "menu":      draw_menu(mp)
        elif mode == "builder": draw_builder(mp)
        elif mode == "decoder": draw_decoder(mp)
        elif mode == "ascii":   draw_ascii(mp)
        elif mode == "over":    draw_over(mp)

        if show_ascii_help:
            draw_ascii_help()

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()