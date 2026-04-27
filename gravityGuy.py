#!/usr/bin/env python3
"""
GRAVITY RUNNER REBORN
A full visual/mechanical refresh of the gravity-flip endless runner.

Controls:
- SPACE or Left Click: flip gravity
- R: restart after game over
- 0: return to start page
- ESC: quit
"""

import math
import os
import random
import subprocess
import sys

import pygame


# ---------------------------------------------------------------------------
# Core settings
# ---------------------------------------------------------------------------

SCREEN_W, SCREEN_H = 1000, 620
FPS = 60

TRACK_TOP = 90
TRACK_BOTTOM = SCREEN_H - 90

PLAYER_X = 220
PLAYER_W = 38
PLAYER_H = 44
GRAVITY = 2500.0
ROTATION_SPEED = 780.0

BASE_SPEED = 290.0
SPEED_GAIN = 12.0
RAMP_SECONDS = 14.0

OBSTACLE_MIN_GAP = 310
OBSTACLE_MAX_GAP = 560

HIGH_SCORE_FILE = "gravity_flip_highscore.txt"


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

BLACK = (8, 10, 18)
WHITE = (236, 242, 255)
STEEL = (70, 88, 120)
NEON_CYAN = (42, 230, 255)
NEON_ORANGE = (255, 170, 55)
NEON_PINK = (255, 88, 180)
NEON_LIME = (132, 255, 105)
DEEP_BLUE = (18, 26, 56)
MID_BLUE = (28, 42, 88)
TRACK_METAL = (40, 56, 95)
TRACK_EDGE = (110, 140, 200)
DANGER = (255, 80, 95)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def load_high_score() -> int:
    if not os.path.exists(HIGH_SCORE_FILE):
        return 0
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    except (ValueError, OSError):
        return 0


def save_high_score(score: int) -> None:
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(int(score)))
    except OSError:
        pass


def return_to_start_page() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    launcher = os.path.join(base_dir, "start_page.py")
    if os.path.exists(launcher):
        subprocess.Popen([sys.executable, launcher], cwd=base_dir)
    pygame.quit()
    sys.exit()


# ---------------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------------


class Particle:
    def __init__(self, x: float, y: float, color):
        angle = random.uniform(0.0, math.tau)
        speed = random.uniform(90.0, 300.0)
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.2, 0.6)
        self.max_life = self.life
        self.size = random.randint(2, 5)
        self.color = color

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 130.0 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf: pygame.Surface) -> None:
        fade = max(0.0, self.life / self.max_life)
        c = tuple(int(ch * fade) for ch in self.color)
        s = max(1, int(self.size * fade))
        pygame.draw.rect(surf, c, (int(self.x), int(self.y), s, s))


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


class Player:
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.x = float(PLAYER_X)
        self.y = float(TRACK_BOTTOM - PLAYER_H)
        self.vy = 0.0
        self.gravity_dir = 1
        self.angle = 0.0
        self.target_angle = 0.0
        self.alive = True

    def flip(self):
        if not self.alive:
            return []
        self.gravity_dir *= -1
        self.vy = 0.0
        self.target_angle += 180.0
        cx = self.x + PLAYER_W * 0.5
        cy = self.y + PLAYER_H * 0.5
        colors = [NEON_CYAN, NEON_PINK, NEON_LIME]
        return [Particle(cx, cy, random.choice(colors)) for _ in range(12)]

    def update(self, dt: float) -> None:
        if not self.alive:
            return

        self.vy += GRAVITY * self.gravity_dir * dt
        self.y += self.vy * dt

        if self.y < TRACK_TOP:
            self.y = TRACK_TOP
            self.vy = 0.0
        if self.y + PLAYER_H > TRACK_BOTTOM:
            self.y = TRACK_BOTTOM - PLAYER_H
            self.vy = 0.0

        diff = self.target_angle - self.angle
        if abs(diff) > 0.6:
            step = ROTATION_SPEED * dt
            self.angle += min(step, abs(diff)) * (1 if diff > 0 else -1)
        else:
            self.angle = self.target_angle

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x) + 5, int(self.y) + 5, PLAYER_W - 10, PLAYER_H - 10)

    def draw(self, surf: pygame.Surface) -> None:
        if not self.alive:
            return

        sprite = pygame.Surface((PLAYER_W, PLAYER_H), pygame.SRCALPHA)

        pygame.draw.rect(sprite, NEON_CYAN, (7, 6, 24, 30), border_radius=8)
        pygame.draw.rect(sprite, WHITE, (12, 10, 14, 8), border_radius=4)
        pygame.draw.rect(sprite, NEON_ORANGE, (12, 24, 14, 8), border_radius=4)

        # Thruster glow indicates velocity direction and movement intensity.
        thrust_len = 6 + min(12, int(abs(self.vy) * 0.015))
        pygame.draw.rect(sprite, NEON_PINK, (16, PLAYER_H - 6, 6, thrust_len), border_radius=3)

        rot = pygame.transform.rotate(sprite, -(self.angle % 360))
        r = rot.get_rect(center=(int(self.x + PLAYER_W * 0.5), int(self.y + PLAYER_H * 0.5)))
        surf.blit(rot, r.topleft)


class Obstacle:
    def __init__(self, world_x: float, side: str, width: int, height: int):
        self.world_x = world_x
        self.side = side  # "top" or "bottom"
        self.width = width
        self.height = height

    def screen_x(self, cam_x: float) -> float:
        return self.world_x - cam_x

    def rect(self, cam_x: float) -> pygame.Rect:
        sx = int(self.screen_x(cam_x))
        if self.side == "top":
            return pygame.Rect(sx, TRACK_TOP, self.width, self.height)
        return pygame.Rect(sx, TRACK_BOTTOM - self.height, self.width, self.height)

    def draw(self, surf: pygame.Surface, cam_x: float, pulse: float) -> None:
        r = self.rect(cam_x)
        if r.right < -80 or r.left > SCREEN_W + 80:
            return

        body = (int(80 + 60 * pulse), int(90 + 90 * pulse), int(160 + 60 * pulse))
        pygame.draw.rect(surf, body, r, border_radius=6)
        pygame.draw.rect(surf, WHITE, r, width=2, border_radius=6)

        stripe_h = 8
        for y in range(r.top + 4, r.bottom - 4, stripe_h * 2):
            pygame.draw.rect(surf, DANGER, (r.left + 4, y, r.width - 8, stripe_h))


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------


class Game:
    MENU = 0
    PLAY = 1
    GAME_OVER = 2

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Gravity Runner Reborn")
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont("consolas", 56, bold=True)
        self.font_med = pygame.font.SysFont("consolas", 28, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 18)

        self.player = Player()
        self.obstacles = []
        self.particles = []

        self.high_score = load_high_score()

        self.state = self.MENU
        self.camera_x = 0.0
        self.speed = BASE_SPEED
        self.elapsed = 0.0
        self.score = 0
        self.next_obstacle_x = SCREEN_W + 280

        self.stars = self._make_stars(72)

    def _make_stars(self, count: int):
        stars = []
        for _ in range(count):
            stars.append({
                "x": random.uniform(0, SCREEN_W),
                "y": random.uniform(0, SCREEN_H),
                "s": random.uniform(8, 36),
                "v": random.uniform(0.08, 0.55),
            })
        return stars

    def new_game(self) -> None:
        self.player.reset()
        self.obstacles.clear()
        self.particles.clear()
        self.state = self.PLAY
        self.camera_x = 0.0
        self.speed = BASE_SPEED
        self.elapsed = 0.0
        self.score = 0
        self.next_obstacle_x = SCREEN_W + 280

    def _spawn_obstacles(self) -> None:
        view_right = self.camera_x + SCREEN_W + 300
        while self.next_obstacle_x < view_right:
            pattern = random.choices(
                ["single", "single", "pair", "stair"],
                weights=[45, 25, 20, 10],
            )[0]

            if pattern == "single":
                side = random.choice(["top", "bottom"])
                width = random.randint(34, 52)
                height = random.randint(90, 155)
                self.obstacles.append(Obstacle(self.next_obstacle_x, side, width, height))
                gap = random.randint(OBSTACLE_MIN_GAP, OBSTACLE_MAX_GAP)

            elif pattern == "pair":
                side_a = random.choice(["top", "bottom"])
                side_b = "bottom" if side_a == "top" else "top"
                self.obstacles.append(Obstacle(self.next_obstacle_x, side_a, 38, random.randint(95, 140)))
                self.obstacles.append(Obstacle(self.next_obstacle_x + 110, side_b, 38, random.randint(95, 140)))
                gap = random.randint(OBSTACLE_MIN_GAP + 30, OBSTACLE_MAX_GAP + 60)

            else:  # stair
                start_side = random.choice(["top", "bottom"])
                for i in range(3):
                    side = start_side if i % 2 == 0 else ("bottom" if start_side == "top" else "top")
                    self.obstacles.append(Obstacle(self.next_obstacle_x + i * 72, side, 34, random.randint(80, 130)))
                gap = random.randint(OBSTACLE_MIN_GAP + 90, OBSTACLE_MAX_GAP + 130)

            self.next_obstacle_x += gap

    def _cull_obstacles(self) -> None:
        left_cut = self.camera_x - 240
        self.obstacles = [o for o in self.obstacles if o.world_x + o.width > left_cut]

    def _die(self) -> None:
        self.player.alive = False
        self.state = self.GAME_OVER

        cx = self.player.x + PLAYER_W * 0.5
        cy = self.player.y + PLAYER_H * 0.5
        for _ in range(46):
            self.particles.append(Particle(cx, cy, random.choice([NEON_CYAN, NEON_PINK, NEON_ORANGE, WHITE])))

        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)

    def update(self, dt: float) -> None:
        if self.state != self.PLAY:
            self.particles = [p for p in self.particles if p.update(dt)]
            return

        self.elapsed += dt
        self.speed = BASE_SPEED + (self.elapsed / RAMP_SECONDS) * SPEED_GAIN
        self.camera_x += self.speed * dt
        self.score = int(self.camera_x / 10)

        self.player.update(dt)
        self._spawn_obstacles()
        self._cull_obstacles()

        p_rect = self.player.rect()
        for obs in self.obstacles:
            if p_rect.colliderect(obs.rect(self.camera_x)):
                self._die()
                break

        self.particles = [p for p in self.particles if p.update(dt)]

        for star in self.stars:
            star["x"] -= self.speed * star["v"] * dt
            if star["x"] < -8:
                star["x"] = SCREEN_W + random.uniform(8, 60)
                star["y"] = random.uniform(0, SCREEN_H)

    def _draw_background(self) -> None:
        # Vertical gradient sky.
        for y in range(SCREEN_H):
            t = y / max(1, SCREEN_H - 1)
            r = int(DEEP_BLUE[0] * (1.0 - t) + MID_BLUE[0] * t)
            g = int(DEEP_BLUE[1] * (1.0 - t) + MID_BLUE[1] * t)
            b = int(DEEP_BLUE[2] * (1.0 - t) + MID_BLUE[2] * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_W, y))

        # Stylized sun.
        sun_x, sun_y = SCREEN_W - 180, 120
        for i in range(5, 0, -1):
            rr = 24 + i * 14
            alpha_col = (255, 130 + i * 10, 90)
            pygame.draw.circle(self.screen, alpha_col, (sun_x, sun_y), rr, width=2)

        for s in self.stars:
            c = (120, 170, 255) if s["s"] < 20 else (200, 230, 255)
            pygame.draw.rect(self.screen, c, (int(s["x"]), int(s["y"]), 2, 2))

    def _draw_track(self) -> None:
        pygame.draw.rect(self.screen, TRACK_METAL, (0, 0, SCREEN_W, TRACK_TOP))
        pygame.draw.rect(self.screen, TRACK_METAL, (0, TRACK_BOTTOM, SCREEN_W, SCREEN_H - TRACK_BOTTOM))
        pygame.draw.line(self.screen, TRACK_EDGE, (0, TRACK_TOP), (SCREEN_W, TRACK_TOP), 3)
        pygame.draw.line(self.screen, TRACK_EDGE, (0, TRACK_BOTTOM), (SCREEN_W, TRACK_BOTTOM), 3)

        spacing = 82
        x_offset = int(self.camera_x) % spacing
        for x in range(-x_offset, SCREEN_W + spacing, spacing):
            pygame.draw.line(self.screen, (45, 62, 106), (x, TRACK_TOP + 2), (x, TRACK_BOTTOM - 2), 1)

    def draw(self) -> None:
        self._draw_background()
        self._draw_track()

        pulse = (math.sin(self.elapsed * 5.5) + 1.0) * 0.5

        for obs in self.obstacles:
            obs.draw(self.screen, self.camera_x, pulse)

        for p in self.particles:
            p.draw(self.screen)

        self.player.draw(self.screen)

        score_t = self.font_med.render(f"SCORE {self.score}", True, NEON_LIME)
        hi_t = self.font_small.render(f"BEST {self.high_score}", True, NEON_CYAN)
        speed_t = self.font_small.render(f"SPD {self.speed:.0f}", True, NEON_ORANGE)

        self.screen.blit(score_t, (SCREEN_W - score_t.get_width() - 20, 16))
        self.screen.blit(hi_t, (SCREEN_W - hi_t.get_width() - 20, 52))
        self.screen.blit(speed_t, (20, SCREEN_H - 28))

        if self.state == self.MENU:
            self._draw_menu()
        elif self.state == self.GAME_OVER:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_menu(self) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        title = self.font_big.render("GRAVITY RUNNER", True, WHITE)
        sub = self.font_med.render("Flip between floor and ceiling to survive", True, NEON_CYAN)
        hint = self.font_small.render("SPACE/CLICK: Flip  |  ESC: Quit", True, NEON_ORANGE)
        start = self.font_med.render("Press SPACE to start", True, NEON_LIME)

        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 170))
        self.screen.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, 258))
        self.screen.blit(start, (SCREEN_W // 2 - start.get_width() // 2, 318))
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 360))

    def _draw_game_over(self) -> None:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))

        title = self.font_big.render("SYSTEM FAILURE", True, DANGER)
        score = self.font_med.render(f"Score: {self.score}", True, WHITE)
        best = self.font_med.render(f"Best: {self.high_score}", True, NEON_LIME)
        hint = self.font_small.render("R to restart  |  ESC to quit", True, NEON_CYAN)

        self.screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 165))
        self.screen.blit(score, (SCREEN_W // 2 - score.get_width() // 2, 270))
        self.screen.blit(best, (SCREEN_W // 2 - best.get_width() // 2, 308))
        self.screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, 370))

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_0:
                        return_to_start_page()
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        if self.state == self.MENU:
                            self.new_game()
                        elif self.state == self.PLAY:
                            self.particles.extend(self.player.flip())
                        elif self.state == self.GAME_OVER:
                            self.new_game()
                    elif event.key == pygame.K_r and self.state == self.GAME_OVER:
                        self.new_game()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == self.MENU:
                        self.new_game()
                    elif self.state == self.PLAY:
                        self.particles.extend(self.player.flip())
                    elif self.state == self.GAME_OVER:
                        self.new_game()

            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
