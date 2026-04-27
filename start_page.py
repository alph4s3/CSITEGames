#!/usr/bin/env python3
import math
import random
import subprocess
import sys
from pathlib import Path

import pygame

BASE_DIR = Path(__file__).resolve().parent

# Label, file path (relative to BASE_DIR)
GAME_OPTIONS = [
    ("Archer Platformer", "ArcherPlatformer"),
    ("Archer Platformer v2", "APv2.py"),
    ("Bomberman", "bomberman.py"),
    ("Jetpack", "JPJR.py"),
    ("Gravity Runner", "gravityGuy.py"),
    ("Pixel Racer", "pixelRacer.py"),
    ("Mountain Platformer", "platformerr.py"),
    ("Red Remover", "redremover.py"),
    ("Fibonacci Adventure", "breh.py"),
]


def existing_games():
    games = []
    for label, rel_path in GAME_OPTIONS:
        full_path = BASE_DIR / rel_path
        if full_path.exists():
            games.append((label, full_path))
    return games


def launch_game(game_path: Path):
    subprocess.Popen([sys.executable, str(game_path)], cwd=str(BASE_DIR))


def draw_vertical_gradient(screen, top_color, bottom_color):
    width, height = screen.get_size()
    for y in range(height):
        t = y / max(height - 1, 1)
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        pygame.draw.line(screen, (r, g, b), (0, y), (width, y))


def glow_circle(surface, pos, radius, color, alpha):
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*color, alpha), (radius, radius), radius)
    surface.blit(glow, (pos[0] - radius, pos[1] - radius))


def make_stars(width, height, count=40):
    stars = []
    for _ in range(count):
        stars.append(
            {
                "x": random.uniform(0, width),
                "y": random.uniform(0, height),
                "r": random.randint(2, 5),
                "spd": random.uniform(0.15, 0.65),
                "phase": random.uniform(0, math.tau),
            }
        )
    return stars


def main():
    pygame.init()
    pygame.display.set_caption("CSITE Games - Select a Game")

    width, height = 980, 620
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("trebuchet ms", 64, bold=True)
    button_font = pygame.font.SysFont("trebuchet ms", 28, bold=True)
    chip_font = pygame.font.SysFont("trebuchet ms", 19, bold=True)

    games = existing_games()
    if not games:
        print("No game files found to launch.")
        return

    accent_colors = [
        (255, 185, 80),
        (90, 230, 255),
        (110, 255, 170),
        (255, 130, 170),
        (180, 150, 255),
        (255, 220, 90),
    ]
    stars = make_stars(width, height)

    selected_index = 0
    running = True
    frame = 0

    while running:
        frame += 1
        mouse_pos = pygame.mouse.get_pos()

        button_top = 170
        button_gap = 10
        max_button_area = height - 28 - button_top
        button_h = max(34, min(58, (max_button_area - (len(games) - 1) * button_gap) // len(games)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % len(games)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % len(games)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    launch_game(games[selected_index][1])
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, _ in enumerate(games):
                    rect = pygame.Rect(0, 0, 600, button_h)
                    rect.centerx = width // 2
                    rect.y = button_top + i * (button_h + button_gap)
                    if rect.collidepoint(event.pos):
                        launch_game(games[i][1])
                        running = False
                        break

        draw_vertical_gradient(screen, (9, 20, 46), (13, 10, 32))

        for star in stars:
            star["x"] -= star["spd"]
            if star["x"] < -10:
                star["x"] = width + 10
                star["y"] = random.uniform(0, height)
            pulse = 0.6 + 0.4 * math.sin(frame * 0.03 + star["phase"])
            radius = int(star["r"] * (0.9 + 0.4 * pulse))
            glow_circle(screen, (int(star["x"]), int(star["y"])), radius + 3, (100, 170, 255), 50)
            pygame.draw.circle(screen, (220, 245, 255), (int(star["x"]), int(star["y"])), max(1, radius))

        hero_rect = pygame.Rect(0, 0, 760, 120)
        hero_rect.centerx = width // 2
        hero_rect.y = 34
        pygame.draw.rect(screen, (20, 36, 88), hero_rect, border_radius=18)
        pygame.draw.rect(screen, (105, 190, 255), hero_rect, width=2, border_radius=18)

        title = title_font.render("CSITE Games", True, (255, 238, 120))
        screen.blit(title, title.get_rect(center=(width // 2, 85)))

        count_text = chip_font.render(f"{len(games)} games available", True, (189, 218, 255))
        screen.blit(count_text, count_text.get_rect(center=(width // 2, 126)))

        for i, (label, _) in enumerate(games):
            rect = pygame.Rect(0, 0, 600, button_h)
            rect.centerx = width // 2
            rect.y = button_top + i * (button_h + button_gap)

            is_hovered = rect.collidepoint(mouse_pos)
            is_selected = i == selected_index
            accent = accent_colors[i % len(accent_colors)]

            if is_selected:
                fill = (34, 84, 170)
                border = (240, 248, 255)
            elif is_hovered:
                fill = (28, 68, 145)
                border = (188, 229, 255)
            else:
                fill = (22, 47, 108)
                border = (79, 129, 204)

            shadow = rect.move(0, 4)
            pygame.draw.rect(screen, (4, 7, 20), shadow, border_radius=12)
            pygame.draw.rect(screen, fill, rect, border_radius=10)
            pygame.draw.rect(screen, border, rect, width=2, border_radius=10)
            pygame.draw.rect(screen, accent, (rect.x + 10, rect.y + 9, 10, rect.height - 18), border_radius=4)

            chip = pygame.Rect(rect.right - 62, rect.y + 11, 46, rect.height - 22)
            pygame.draw.rect(screen, (14, 26, 60), chip, border_radius=8)
            pygame.draw.rect(screen, (160, 205, 255), chip, width=1, border_radius=8)

            idx_text = chip_font.render(str(i + 1), True, (255, 243, 170))
            screen.blit(idx_text, idx_text.get_rect(center=chip.center))

            txt = button_font.render(label, True, (245, 245, 245))
            txt_rect = txt.get_rect(midleft=(rect.left + 34, rect.centery))
            screen.blit(txt, txt_rect)


        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
