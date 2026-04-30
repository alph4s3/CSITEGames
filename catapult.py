"""
CSITE Career Booth — Game 4: CATAPULT PHYSICS
==============================================
A hands-on demo of the projectile-motion equations engineering
students see in their first physics course:

    x(t) = v · cos(θ) · t
    y(t) = v · sin(θ) · t  −  ½ g t²

The visitor aims a medieval catapult at three movable targets.
Drag from the catapult to set angle and power.  Release to launch.
Watch the parabolic trajectory and read live values of θ, v, range
and flight-time on the side panel.

Educational hooks
-----------------
• Live read-out of θ, v₀, v_x, v_y, range, time-of-flight.
• Optional trajectory ghost line shows the predicted path
  before launch — exactly what an engineer would compute.
• A small wind component (changeable) shows how a real engineer
  has to account for environment.

Controls : Click & drag from the catapult to aim and set power.
           Release to fire.  Use buttons to toggle wind / preview.
           ESC quits.
Resolution: 1024×768
"""

import pygame
import math
import random
import sys

pygame.init()
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("CSITE — Catapult Physics")
clock = pygame.time.Clock()

# ---- colours ---- #
SKY_TOP   = (90, 160, 220)
SKY_BOT   = (200, 230, 250)
GROUND    = (90, 130, 60)
GROUND_D  = (60, 90, 35)
WHITE     = (245, 245, 250)
SOFT      = (220, 230, 245)
DARK      = (10, 18, 30)
GOLD      = (255, 200, 60)
RED       = (220, 70, 70)
GREEN     = (60, 200, 100)
BLUE      = (60, 120, 220)
PURPLE    = (180, 100, 220)
WOOD      = (140, 90, 50)
WOOD_D    = (90, 55, 25)
STONE     = (130, 130, 130)
PANEL     = (15, 22, 40)

# ---- fonts ---- #
F_TITLE = pygame.font.SysFont("arial", 44, bold=True)
F_BIG   = pygame.font.SysFont("arial", 28, bold=True)
F_MED   = pygame.font.SysFont("arial", 22)
F_SMALL = pygame.font.SysFont("arial", 18)
F_TINY  = pygame.font.SysFont("arial", 14)
F_MONO  = pygame.font.SysFont("couriernew", 18, bold=True)

# Ground level
GROUND_Y = HEIGHT - 100

# Catapult position
CAT_X, CAT_Y = 110, GROUND_Y - 40  # tip of catapult arm

# Physics
GRAVITY = 600.0    # px / s² — tuned for booth scale

# ---- helpers ---- #
def draw_text(text, font, color, x, y, center=False):
    s = font.render(text, True, color)
    r = s.get_rect()
    if center: r.center = (x, y)
    else:      r.topleft = (x, y)
    screen.blit(s, r)


def draw_sky():
    for y in range(HEIGHT):
        t = y / HEIGHT
        col = tuple(int(SKY_TOP[i] + (SKY_BOT[i] - SKY_TOP[i]) * t)
                    for i in range(3))
        pygame.draw.line(screen, col, (0, y), (WIDTH, y))
    # clouds (procedural)
    for cx, cy, sc in [(180, 120, 1.0), (520, 80, 1.4),
                       (820, 150, 1.0), (350, 200, 0.8)]:
        for dx, dy, r in [(0,0,32), (24,-8,28), (50,0,32), (24,16,26)]:
            pygame.draw.circle(screen, (250, 250, 255),
                               (int(cx+dx*sc), int(cy+dy*sc)), int(r*sc))


def draw_ground():
    pygame.draw.rect(screen, GROUND,
                     (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.rect(screen, GROUND_D,
                     (0, GROUND_Y, WIDTH, 6))
    # tufts of grass
    random.seed(42)
    for _ in range(40):
        x = random.randint(10, WIDTH-10)
        h = random.randint(6, 12)
        pygame.draw.line(screen, GROUND_D, (x, GROUND_Y),
                         (x-2, GROUND_Y - h), 2)
        pygame.draw.line(screen, GROUND_D, (x, GROUND_Y),
                         (x+2, GROUND_Y - h), 2)


def draw_catapult(angle):
    """Draw a stylised wooden catapult.  Angle in radians (above x-axis)."""
    bx = CAT_X - 20
    by = GROUND_Y
    # base
    pygame.draw.rect(screen, WOOD, (bx - 40, by - 22, 90, 22),
                     border_radius=4)
    pygame.draw.rect(screen, WOOD_D, (bx - 40, by - 22, 90, 22),
                     2, border_radius=4)
    # wheels
    pygame.draw.circle(screen, WOOD_D, (bx - 30, by), 14)
    pygame.draw.circle(screen, WOOD_D, (bx + 40, by), 14)
    pygame.draw.circle(screen, (40, 25, 10), (bx - 30, by), 14, 2)
    pygame.draw.circle(screen, (40, 25, 10), (bx + 40, by), 14, 2)
    pygame.draw.circle(screen, (40, 25, 10), (bx - 30, by), 4)
    pygame.draw.circle(screen, (40, 25, 10), (bx + 40, by), 4)
    # arm pivot
    pivot = (bx + 5, by - 22)
    # arm
    arm_len = 90
    arm_end = (pivot[0] + arm_len * math.cos(-angle),
               pivot[1] + arm_len * math.sin(-angle))
    pygame.draw.line(screen, WOOD, pivot, arm_end, 8)
    pygame.draw.line(screen, WOOD_D, pivot, arm_end, 2)
    # bucket
    pygame.draw.circle(screen, STONE, (int(arm_end[0]), int(arm_end[1])), 9)
    pygame.draw.circle(screen, DARK,  (int(arm_end[0]), int(arm_end[1])), 9, 2)
    # supports
    pygame.draw.line(screen, WOOD, (bx - 25, by - 22),
                     pivot, 6)
    pygame.draw.line(screen, WOOD, (bx + 35, by - 22),
                     pivot, 6)
    return arm_end


# --------------------------------------------------------------------- #
#  Targets
# --------------------------------------------------------------------- #
class Target:
    def __init__(self, x):
        self.x = x
        self.y = GROUND_Y - 40
        self.r = 28
        self.alive = True
        self.fall = 0           # animation when hit

    def draw(self):
        if not self.alive:
            # falling target
            self.fall += 1
            self.y += self.fall * 0.5
            if self.y > GROUND_Y + 60:
                return
        cx, cy = int(self.x), int(self.y)
        # post
        pygame.draw.rect(screen, WOOD,
                         (cx - 4, cy + 28, 8, 60))
        # rings
        pygame.draw.circle(screen, WHITE, (cx, cy), self.r)
        pygame.draw.circle(screen, RED,   (cx, cy), self.r - 6)
        pygame.draw.circle(screen, WHITE, (cx, cy), self.r - 12)
        pygame.draw.circle(screen, RED,   (cx, cy), self.r - 18)
        pygame.draw.circle(screen, GOLD,  (cx, cy), 4)

    def hit(self, px, py):
        return (self.alive and
                math.hypot(px - self.x, py - self.y) < self.r + 6)


targets = []
def reset_targets():
    global targets
    targets = [
        Target(random.randint(420, 520)),
        Target(random.randint(620, 720)),
        Target(random.randint(820, 940)),
    ]


# --------------------------------------------------------------------- #
#  Projectile state
# --------------------------------------------------------------------- #
proj   = None             # dict with x,y,vx,vy or None
trail  = []               # list of past positions for trajectory
score  = 0
shots  = 0
hits   = 0
wind   = 0.0              # px/s² horizontal acceleration
show_preview = True
last_v = 0
last_a = 45.0  # angle in degrees
flight_time = 0.0

# ---- aiming ---- #
aiming = False
aim_start = None          # we anchor at catapult
aim_current = None
MAX_POWER = 900.0          # max |v| px/s


def angle_power_from_drag(start, current):
    """Player drags FROM catapult TO some point.  Power is the
    distance, angle is the line direction (mirrored so that pulling
    DOWN-RIGHT launches UP-RIGHT — like a sling-shot)."""
    # vector from start to current
    dx = current[0] - start[0]
    dy = current[1] - start[1]
    # Mirror: launch direction is opposite of pull
    lx, ly = -dx, -dy
    if lx < 0: lx = 0    # don't allow backward
    angle = math.atan2(-ly, lx)   # above-x axis
    angle = max(0.05, min(math.pi/2 - 0.05, angle))
    distance = math.hypot(dx, dy)
    power = min(MAX_POWER, distance * 4.0)
    return angle, power


# --------------------------------------------------------------------- #
#  Buttons
# --------------------------------------------------------------------- #
class Button:
    def __init__(self, x, y, w, h, label, color=BLUE, font=F_SMALL):
        self.rect, self.label, self.color, self.font = (
            pygame.Rect(x, y, w, h), label, color, font)
    def draw(self, mp):
        hover = self.rect.collidepoint(mp)
        c = self.color if not hover else tuple(min(255, v+35) for v in self.color)
        pygame.draw.rect(screen, c, self.rect, border_radius=8)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=8)
        draw_text(self.label, self.font, WHITE,
                  self.rect.centerx, self.rect.centery, center=True)
    def clicked(self, ev):
        return (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                and self.rect.collidepoint(ev.pos))


btn_reset   = Button(WIDTH - 180, 20, 160, 40, "↺ New Targets")
btn_preview = Button(WIDTH - 180, 70, 160, 40, "Toggle Preview")
btn_wind    = Button(WIDTH - 180, 120, 160, 40, "Random Wind")


# --------------------------------------------------------------------- #
#  Drawing the side panel & equations
# --------------------------------------------------------------------- #
def draw_panel(angle_deg, power):
    panel = pygame.Rect(WIDTH - 200, 180, 180, 380)
    pygame.draw.rect(screen, PANEL, panel, border_radius=10)
    pygame.draw.rect(screen, GOLD, panel, 2, border_radius=10)
    draw_text("PHYSICS LIVE", F_BIG, GOLD,
              panel.centerx, panel.y + 20, center=True)

    angle_rad = math.radians(angle_deg)
    vx = power * math.cos(angle_rad)
    vy = power * math.sin(angle_rad)
    # Predicted range over flat ground (ignoring wind)
    if power > 0:
        flight = 2 * vy / GRAVITY
        rng = vx * flight
    else:
        flight, rng = 0, 0

    rows = [
        ("θ",       f"{angle_deg:6.1f}°"),
        ("v₀",      f"{power:6.0f} px/s"),
        ("vₓ",      f"{vx:6.0f}"),
        ("vy",      f"{vy:6.0f}"),
        ("g",       f"{GRAVITY:6.0f}"),
        ("wind",    f"{wind:+6.0f}"),
        ("range",   f"{rng:6.0f} px"),
        ("flight",  f"{flight:5.2f} s"),
    ]
    for i, (k, v) in enumerate(rows):
        y = panel.y + 60 + i * 32
        draw_text(k, F_MONO, SOFT, panel.x + 14, y)
        draw_text(v, F_MONO, WHITE, panel.x + 70, y)

    # Score readout
    y = panel.y + 60 + len(rows) * 32 + 12
    pygame.draw.line(screen, GOLD,
                     (panel.x + 14, y), (panel.right - 14, y), 1)
    draw_text(f"Hits   {hits}/{shots}", F_MED, GOLD,
              panel.centerx, y + 22, center=True)
    draw_text(f"Score  {score}", F_MED, GREEN,
              panel.centerx, y + 50, center=True)


def draw_equations():
    eq = pygame.Rect(20, 580, 760, 80)
    pygame.draw.rect(screen, PANEL, eq, border_radius=10)
    pygame.draw.rect(screen, BLUE, eq, 2, border_radius=10)
    draw_text("PROJECTILE MOTION:", F_SMALL, GOLD,
              eq.x + 14, eq.y + 8)
    draw_text("x(t) = v₀ · cos(θ) · t",
              F_MONO, WHITE, eq.x + 14, eq.y + 32)
    draw_text("y(t) = v₀ · sin(θ) · t  −  ½ g t²",
              F_MONO, WHITE, eq.x + 14, eq.y + 54)
    draw_text("Range:  R = v₀² · sin(2θ) / g",
              F_MONO, GOLD, eq.x + 380, eq.y + 32)
    draw_text("Maximum range when θ = 45°  (no wind)",
              F_SMALL, SOFT, eq.x + 380, eq.y + 56)


def draw_preview(start_pos, angle, power):
    """Dotted ghost line — first 2 seconds of trajectory."""
    if not show_preview or power < 5:
        return
    vx = power * math.cos(angle)
    vy = -power * math.sin(angle)
    x, y = start_pos
    for i in range(60):
        t = i / 30.0
        px = x + vx * t + 0.5 * wind * t * t
        py = y + vy * t + 0.5 * GRAVITY * t * t
        if py > GROUND_Y or px > WIDTH or px < 0:
            break
        if i % 2 == 0:
            pygame.draw.circle(screen, (255, 255, 255, 200),
                               (int(px), int(py)), 2)


def draw_aim_line(arm_end):
    if aiming and aim_current:
        # show pull-back vector and arrow showing intended launch
        pygame.draw.line(screen, (255, 255, 255), arm_end, aim_current, 2)
        # mirrored direction
        dx = aim_current[0] - arm_end[0]
        dy = aim_current[1] - arm_end[1]
        end = (arm_end[0] - dx, arm_end[1] - dy)
        pygame.draw.line(screen, GOLD, arm_end, end, 3)


# --------------------------------------------------------------------- #
#  Main
# --------------------------------------------------------------------- #
def main():
    global proj, trail, score, shots, hits, last_v, last_a, flight_time
    global aiming, aim_current, wind, show_preview

    reset_targets()
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        mp = pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: running = False
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False

            if btn_reset.clicked(ev):
                reset_targets(); proj = None; trail = []
            if btn_preview.clicked(ev): show_preview = not show_preview
            if btn_wind.clicked(ev):
                wind = random.uniform(-200, 200)

            # Drag-to-aim, only if no projectile in flight
            if proj is None:
                if (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1
                        and ev.pos[0] < WIDTH - 220):
                    aiming = True
                    aim_current = ev.pos
                if ev.type == pygame.MOUSEMOTION and aiming:
                    aim_current = ev.pos
                if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and aiming:
                    aiming = False
                    angle, power = angle_power_from_drag((CAT_X, CAT_Y),
                                                        aim_current)
                    if power > 30:
                        # launch
                        proj = {
                            "x": CAT_X, "y": CAT_Y,
                            "vx": power * math.cos(angle),
                            "vy": -power * math.sin(angle),
                        }
                        trail = [(CAT_X, CAT_Y)]
                        last_v = power
                        last_a = math.degrees(angle)
                        shots += 1
                        flight_time = 0.0

        # Aim preview values
        if aiming and aim_current:
            angle_aim, power_aim = angle_power_from_drag((CAT_X, CAT_Y),
                                                        aim_current)
            display_angle = math.degrees(angle_aim)
            display_power = power_aim
        elif proj:
            display_angle = last_a
            display_power = last_v
        else:
            display_angle = last_a
            display_power = last_v

        # ---- physics ---- #
        if proj is not None:
            proj["x"]  += proj["vx"] * dt
            proj["y"]  += proj["vy"] * dt
            proj["vy"] += GRAVITY * dt
            proj["vx"] += wind   * dt
            flight_time += dt
            trail.append((proj["x"], proj["y"]))

            # collisions
            for t in targets:
                if t.hit(proj["x"], proj["y"]):
                    t.alive = False
                    hits  += 1
                    score += 100
                    proj   = None
                    break

            # off-screen / hit ground
            if proj is not None:
                if (proj["y"] > GROUND_Y or proj["x"] > WIDTH or
                    proj["x"] < -50 or proj["y"] < -200):
                    proj = None

        # ---- draw ---- #
        draw_sky()
        draw_ground()

        # Targets
        for t in targets:
            t.draw()
            # distance label below post
            if t.alive:
                d = int(t.x - CAT_X)
                draw_text(f"{d}px", F_TINY, DARK,
                          int(t.x), GROUND_Y + 70, center=True)

        # Catapult — shown with current aim or nominal angle
        cur_angle_rad = math.radians(display_angle if not proj else last_a)
        arm_end = draw_catapult(cur_angle_rad)

        # Trajectory
        if len(trail) >= 2:
            pygame.draw.lines(screen, (255, 100, 100), False,
                              [(int(p[0]), int(p[1])) for p in trail], 2)
        if proj:
            pygame.draw.circle(screen, STONE,
                               (int(proj["x"]), int(proj["y"])), 8)
            pygame.draw.circle(screen, DARK,
                               (int(proj["x"]), int(proj["y"])), 8, 2)

        # Aim guide & preview
        if aiming and aim_current:
            draw_aim_line(arm_end)
            angle_aim, power_aim = angle_power_from_drag((CAT_X, CAT_Y),
                                                        aim_current)
            draw_preview((CAT_X, CAT_Y), angle_aim, power_aim)

        # Wind indicator
        if wind != 0:
            wx, wy = WIDTH//2, 80
            draw_text(f"WIND {wind:+.0f}", F_SMALL,
                      GOLD if wind > 0 else BLUE,
                      wx, wy, center=True)
            # arrows
            sign = 1 if wind > 0 else -1
            for k in range(3):
                pygame.draw.line(screen, GOLD if wind > 0 else BLUE,
                                 (wx - 50 + k*40 - sign*20,
                                  wy + 20),
                                 (wx - 50 + k*40 + sign*20, wy + 20), 2)
                pygame.draw.polygon(screen, GOLD if wind > 0 else BLUE,
                                    [(wx - 50 + k*40 + sign*20, wy + 20),
                                     (wx - 50 + k*40 + sign*12, wy + 14),
                                     (wx - 50 + k*40 + sign*12, wy + 26)])

        # UI ------------------------------------------------------------ #
        draw_text("CATAPULT PHYSICS — drag from catapult to aim, release to fire",
                  F_MED, DARK, 20, 18)
        btn_reset.draw(mp)
        btn_preview.draw(mp)
        btn_wind.draw(mp)
        draw_panel(display_angle, display_power)
        draw_equations()

        # Win message
        if all(not t.alive for t in targets):
            box = pygame.Rect(WIDTH//2 - 220, 250, 440, 120)
            pygame.draw.rect(screen, PANEL, box, border_radius=12)
            pygame.draw.rect(screen, GOLD, box, 3, border_radius=12)
            draw_text("ALL TARGETS DOWN!", F_TITLE, GOLD,
                      box.centerx, box.y + 35, center=True)
            draw_text(f"Score: {score}   Accuracy: {hits}/{shots}",
                      F_MED, WHITE,
                      box.centerx, box.y + 80, center=True)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()