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
    ("Math Archer", "ArcherPlatformer"),
    ("Math Bomberman", "bomberman.py"),
    ("Math Jetpack", "JPJR.py"),
    ("Gravity Runner", "gravityGuy.py"),
    ("Pixel Racer", "pixelRacer.py"),
    ("Mountain Platformer", "platformerr.py"),
    ("Math Remover", "redremover.py"),
    ("Fibonacci Adventure", "breh.py"),
    ("Binary Code Breaker", "binary.py"),
    ("Logic Challenge", "brainTeaser.py"),
    ("Catapult Physics", "catapult.py"),
    ("Escape Room", "room.py"),
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

    width, height = 1120, 700
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()

    title_font = pygame.font.SysFont("rockwell", 62, bold=True)
    subtitle_font = pygame.font.SysFont("rockwell", 24, bold=True)
    card_font = pygame.font.SysFont("trebuchet ms", 24, bold=True)
    body_font = pygame.font.SysFont("trebuchet ms", 20)
    chip_font = pygame.font.SysFont("trebuchet ms", 18, bold=True)
    hint_font = pygame.font.SysFont("consolas", 17, bold=True)

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
    page_index = 0
    page_size = 6
    running = True
    frame = 0

    while running:
        frame += 1
        mouse_pos = pygame.mouse.get_pos()

        page_count = max(1, math.ceil(len(games) / page_size))
        page_index = max(0, min(page_index, page_count - 1))
        start = page_index * page_size
        page_games = games[start : start + page_size]
        if not page_games:
            page_games = games[:page_size]

        grid_left = 420
        grid_top = 170
        grid_right_margin = 48
        grid_bottom_margin = 86
        grid_gap = 16
        cols = 2
        rows = 3
        grid_width = width - grid_left - grid_right_margin
        grid_height = height - grid_top - grid_bottom_margin
        card_w = (grid_width - grid_gap * (cols - 1)) // cols
        card_h = (grid_height - grid_gap * (rows - 1)) // rows

        card_rects = []
        for i in range(len(page_games)):
            row = i // cols
            col = i % cols
            x = grid_left + col * (card_w + grid_gap)
            y = grid_top + row * (card_h + grid_gap)
            card_rects.append(pygame.Rect(x, y, card_w, card_h))

        prev_button = pygame.Rect(width - 280, height - 68, 108, 34)
        next_button = pygame.Rect(width - 156, height - 68, 108, 34)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - cols) % len(page_games)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + cols) % len(page_games)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    selected_index = (selected_index - 1) % len(page_games)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected_index = (selected_index + 1) % len(page_games)
                elif event.key in (pygame.K_PAGEUP, pygame.K_q):
                    page_index = (page_index - 1) % page_count
                    selected_index = 0
                elif event.key in (pygame.K_PAGEDOWN, pygame.K_e):
                    page_index = (page_index + 1) % page_count
                    selected_index = 0
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    launch_game(page_games[selected_index][1])
                    running = False
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if prev_button.collidepoint(event.pos):
                    page_index = (page_index - 1) % page_count
                    selected_index = 0
                    continue
                if next_button.collidepoint(event.pos):
                    page_index = (page_index + 1) % page_count
                    selected_index = 0
                    continue

                for i, rect in enumerate(card_rects):
                    if rect.collidepoint(event.pos):
                        selected_index = i
                        launch_game(page_games[i][1])
                        running = False
                        break

        draw_vertical_gradient(screen, (11, 30, 56), (19, 12, 30))

        # Animated aurora bands for a more distinctive background.
        for i in range(4):
            y = int(height * (0.25 + i * 0.18) + math.sin(frame * 0.012 + i * 1.9) * 24)
            col = (35 + i * 12, 70 + i * 18, 120 + i * 22)
            pygame.draw.ellipse(screen, (*col, 40), (-180, y - 70, width + 360, 140), width=0)

        for star in stars:
            star["x"] -= star["spd"]
            if star["x"] < -10:
                star["x"] = width + 10
                star["y"] = random.uniform(0, height)
            pulse = 0.6 + 0.4 * math.sin(frame * 0.03 + star["phase"])
            radius = int(star["r"] * (0.9 + 0.4 * pulse))
            glow_circle(screen, (int(star["x"]), int(star["y"])), radius + 3, (80, 210, 255), 48)
            pygame.draw.circle(screen, (220, 245, 255), (int(star["x"]), int(star["y"])), max(1, radius))

        # Left rail with title and launch details.
        rail = pygame.Rect(34, 34, 350, height - 68)
        pygame.draw.rect(screen, (14, 25, 48), rail, border_radius=24)
        pygame.draw.rect(screen, (82, 166, 233), rail, width=2, border_radius=24)

        title = title_font.render("CSITE", True, (254, 225, 122))
        screen.blit(title, title.get_rect(midtop=(rail.centerx, 58)))
        subtitle = subtitle_font.render("Games Launcher", True, (186, 223, 245))
        screen.blit(subtitle, subtitle.get_rect(midtop=(rail.centerx, 122)))

        count_chip = pygame.Rect(0, 0, 220, 38)
        count_chip.center = (rail.centerx, 176)
        pygame.draw.rect(screen, (24, 44, 78), count_chip, border_radius=12)
        pygame.draw.rect(screen, (115, 191, 250), count_chip, width=1, border_radius=12)
        count_text = chip_font.render(f"{len(games)} games across {page_count} pages", True, (235, 246, 255))
        screen.blit(count_text, count_text.get_rect(center=count_chip.center))

        selected_label, selected_path = page_games[selected_index]
        info_box = pygame.Rect(56, 228, 306, 342)
        pygame.draw.rect(screen, (20, 35, 65), info_box, border_radius=14)
        pygame.draw.rect(screen, (88, 152, 220), info_box, width=1, border_radius=14)
        sel_title = subtitle_font.render("Now Selected", True, (123, 221, 255))
        screen.blit(sel_title, (info_box.x + 16, info_box.y + 16))
        sel_name = card_font.render(selected_label, True, (255, 246, 208))
        screen.blit(sel_name, (info_box.x + 16, info_box.y + 58))

        path_label = body_font.render("File:", True, (180, 214, 240))
        screen.blit(path_label, (info_box.x + 16, info_box.y + 118))
        path_text = chip_font.render(str(selected_path.name), True, (255, 255, 255))
        screen.blit(path_text, (info_box.x + 16, info_box.y + 146))

        nav_title = subtitle_font.render("Controls", True, (123, 221, 255))
        screen.blit(nav_title, (info_box.x + 16, info_box.y + 188))

        tip_lines = [
            "Arrows / WASD: move selection",
            "Enter: launch selected game",
            "Q/E or Page Keys: switch pages",
            "Mouse click: open a game",
            "Esc: quit launcher",
        ]
        ty = info_box.y + 224
        for line in tip_lines:
            t = chip_font.render(f"- {line}", True, (197, 223, 245))
            screen.blit(t, (info_box.x + 16, ty))
            ty += 24

        for i, (label, _) in enumerate(page_games):
            rect = card_rects[i]

            is_hovered = rect.collidepoint(mouse_pos)
            is_selected = i == selected_index
            accent = accent_colors[i % len(accent_colors)]

            if is_selected:
                fill = (42, 88, 130)
                border = (245, 250, 255)
            elif is_hovered:
                fill = (34, 72, 112)
                border = (200, 234, 255)
            else:
                fill = (26, 54, 88)
                border = (97, 145, 205)

            shadow = rect.move(0, 5)
            pygame.draw.rect(screen, (4, 7, 20), shadow, border_radius=12)
            pygame.draw.rect(screen, fill, rect, border_radius=14)
            pygame.draw.rect(screen, border, rect, width=2, border_radius=14)
            pygame.draw.rect(screen, accent, (rect.x + 11, rect.y + 11, rect.width - 22, 7), border_radius=4)

            chip = pygame.Rect(rect.right - 54, rect.y + 13, 36, 28)
            pygame.draw.rect(screen, (14, 26, 60), chip, border_radius=8)
            pygame.draw.rect(screen, (160, 205, 255), chip, width=1, border_radius=8)

            idx_text = chip_font.render(str(i + 1), True, (255, 243, 170))
            screen.blit(idx_text, idx_text.get_rect(center=chip.center))

            txt = card_font.render(label, True, (245, 245, 245))
            txt_rect = txt.get_rect(midleft=(rect.left + 18, rect.centery + 4))
            screen.blit(txt, txt_rect)

        pygame.draw.rect(screen, (18, 32, 58), prev_button, border_radius=10)
        pygame.draw.rect(screen, (110, 170, 235), prev_button, width=2, border_radius=10)
        pygame.draw.rect(screen, (18, 32, 58), next_button, border_radius=10)
        pygame.draw.rect(screen, (110, 170, 235), next_button, width=2, border_radius=10)

        prev_text = chip_font.render("Prev Page", True, (235, 246, 255))
        next_text = chip_font.render("Next Page", True, (235, 246, 255))
        screen.blit(prev_text, prev_text.get_rect(center=prev_button.center))
        screen.blit(next_text, next_text.get_rect(center=next_button.center))

        page_text = chip_font.render(f"Page {page_index + 1}/{page_count}", True, (255, 243, 170))
        screen.blit(page_text, page_text.get_rect(midbottom=(width - 214, height - 76)))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
