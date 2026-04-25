import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame


# ---------- Configuration ----------
WIDTH, HEIGHT = 1280, 720
FPS = 60
GRAVITY = 0.55
LEADERBOARD_FILE = Path(__file__).with_name("leaderboardMP.json")


# ---------- Utility ----------
def clamp(value, lo, hi):
	return max(lo, min(hi, value))


def draw_text(surface, text, font, color, x, y, center=False):
	img = font.render(text, True, color)
	rect = img.get_rect()
	if center:
		rect.center = (x, y)
	else:
		rect.topleft = (x, y)
	surface.blit(img, rect)
	return rect


def circle_rect_collision(cx, cy, radius, rect):
	nearest_x = clamp(cx, rect.left, rect.right)
	nearest_y = clamp(cy, rect.top, rect.bottom)
	dx = cx - nearest_x
	dy = cy - nearest_y
	return dx * dx + dy * dy <= radius * radius


def safe_load_leaderboard(path):
	if not path.exists():
		return []
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
		if isinstance(data, list):
			cleaned = []
			for row in data:
				if isinstance(row, dict) and "name" in row and "score" in row:
					cleaned.append({"name": str(row["name"]), "score": int(row["score"])})
			return cleaned
	except (json.JSONDecodeError, OSError, ValueError):
		return []
	return []


def save_leaderboard(path, rows):
	rows = sorted(rows, key=lambda r: r["score"], reverse=True)[:10]
	path.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def generate_problem(level_index):
	"""Return a question dict with text, correct answer, and 4 options."""
	if level_index == 0:
		# Addition / subtraction up to 2-digit numbers.
		a = random.randint(5, 99)
		b = random.randint(1, 99)
		op = random.choice(["+", "-"])
		if op == "-" and b > a:
			a, b = b, a
		correct = a + b if op == "+" else a - b
		text = f"{a} {op} {b} = ?"
	elif level_index == 1:
		# Multiplication / division.
		if random.random() < 0.55:
			a = random.randint(2, 12)
			b = random.randint(2, 12)
			correct = a * b
			text = f"{a} x {b} = ?"
		else:
			b = random.randint(2, 12)
			correct = random.randint(2, 12)
			a = b * correct
			text = f"{a} / {b} = ?"
	else:
		# Mixed ops + simple algebra.
		mode = random.randint(0, 2)
		if mode == 0:
			a = random.randint(2, 20)
			b = random.randint(2, 20)
			c = random.randint(2, 10)
			if random.random() < 0.5:
				correct = (a + b) * c
				text = f"({a} + {b}) x {c} = ?"
			else:
				correct = a * b - c
				text = f"{a} x {b} - {c} = ?"
		elif mode == 1:
			k = random.randint(2, 6)
			x = random.randint(2, 12)
			b = random.randint(1, 12)
			c = k * x + b
			correct = x
			text = f"{k}x + {b} = {c}, x = ?"
		else:
			p = random.randint(2, 15)
			q = random.randint(2, 15)
			r = random.randint(2, 9)
			correct = p + q * r
			text = f"{p} + {q} x {r} = ?"

	options = {correct}
	while len(options) < 4:
		wiggle = random.randint(-12, 12)
		candidate = correct + wiggle
		if candidate == correct:
			candidate += random.choice([-3, 3])
		if level_index == 0:
			candidate = max(0, candidate)
		options.add(candidate)

	options = list(options)
	random.shuffle(options)
	return {
		"text": text,
		"correct": correct,
		"options": options,
		"correct_index": options.index(correct),
	}


# ---------- Data Classes ----------
@dataclass
class Theme:
	name: str
	sky: tuple
	mid: tuple
	far: tuple
	ground: tuple
	accent: tuple


THEMES = [
	Theme("Forest", (145, 225, 255), (117, 205, 150), (92, 173, 120), (82, 70, 52), (255, 218, 113)),
	Theme("Crystal Caves", (124, 156, 255), (128, 118, 222), (94, 88, 168), (63, 56, 98), (142, 255, 239)),
	Theme("Sky Temple", (185, 235, 255), (255, 245, 195), (235, 215, 155), (158, 132, 96), (255, 246, 168)),
]


LEVEL_NAMES = ["Forest", "Crystal Caves", "Sky Temple"]


class Platform:
	def __init__(self, x, y, w, h, color):
		self.rect = pygame.Rect(x, y, w, h)
		self.color = color
		self.top_color = tuple(min(255, c + 38) for c in color)
		self.brick_color = tuple(max(0, c - 28) for c in color)

	def draw(self, surface, cam_x):
		r = self.rect.move(-cam_x, 0)
		pygame.draw.rect(surface, self.color, r, border_radius=6)
		top = pygame.Rect(r.x, r.y, r.w, max(6, r.h // 4))
		pygame.draw.rect(surface, self.top_color, top, border_top_left_radius=6, border_top_right_radius=6)

		# Brick-like pattern to evoke a classic platformer aesthetic.
		brick_w = 26
		for x in range(r.x + 4, r.right - 4, brick_w):
			pygame.draw.line(surface, self.brick_color, (x, r.y + 8), (x, r.bottom - 4), 1)
		for y in range(r.y + 10, r.bottom - 2, 11):
			pygame.draw.line(surface, self.brick_color, (r.x + 4, y), (r.right - 4, y), 1)

		pygame.draw.rect(surface, (255, 255, 255), r, 2, border_radius=6)


class Gate:
	def __init__(self, x, y, w, h):
		self.rect = pygame.Rect(x, y, w, h)
		self.opened = False

	def draw(self, surface, cam_x):
		if self.opened:
			return
		r = self.rect.move(-cam_x, 0)
		pygame.draw.rect(surface, (240, 90, 90), r, border_radius=8)
		pygame.draw.rect(surface, (255, 220, 220), r, 2, border_radius=8)


class Coin:
	def __init__(self, x, y):
		self.rect = pygame.Rect(x, y, 18, 18)
		self.collected = False
		self.phase = random.random() * 6.28

	def update(self):
		self.phase += 0.08

	def draw(self, surface, cam_x):
		if self.collected:
			return
		x = self.rect.centerx - cam_x
		y = self.rect.centery + math.sin(self.phase) * 5
		pygame.draw.circle(surface, (255, 226, 84), (int(x), int(y)), 9)
		pygame.draw.circle(surface, (255, 248, 186), (int(x), int(y)), 4)


class Particle:
	def __init__(self, pos, vel, color, life=30, size=4, gravity=0.22):
		self.x, self.y = pos
		self.vx, self.vy = vel
		self.color = color
		self.life = life
		self.max_life = life
		self.size = size
		self.gravity = gravity

	def update(self):
		self.vy += self.gravity
		self.x += self.vx
		self.y += self.vy
		self.life -= 1

	def draw(self, surface, cam_x):
		if self.life <= 0:
			return
		alpha_ratio = self.life / self.max_life
		size = max(1, int(self.size * alpha_ratio))
		pygame.draw.circle(surface, self.color, (int(self.x - cam_x), int(self.y)), size)

	@property
	def dead(self):
		return self.life <= 0


class Projectile:
	def __init__(self, x, y, vx, vy, mega=False):
		self.x = x
		self.y = y
		self.vx = vx
		self.vy = vy
		self.radius = 11 if mega else 7
		self.life = 90
		self.mega = mega

	def update(self):
		self.x += self.vx
		self.y += self.vy
		self.life -= 1

	def draw(self, surface, cam_x):
		color = (255, 255, 170) if self.mega else (255, 238, 109)
		pygame.draw.circle(surface, color, (int(self.x - cam_x), int(self.y)), self.radius)
		pygame.draw.circle(surface, (255, 255, 255), (int(self.x - cam_x), int(self.y)), self.radius, 2)

	@property
	def dead(self):
		return self.life <= 0


class Enemy:
	def __init__(self, x, y, patrol_min, patrol_max):
		self.rect = pygame.Rect(x, y, 42, 34)
		self.vx = random.choice([-2.0, 2.0])
		self.vy = 0
		self.patrol_min = patrol_min
		self.patrol_max = patrol_max
		self.alive = True

	def update(self, platforms, freeze=False):
		if not self.alive or freeze:
			return

		self.vy += GRAVITY * 0.9
		self.rect.y += int(self.vy)
		for p in platforms:
			if self.rect.colliderect(p.rect) and self.vy > 0:
				self.rect.bottom = p.rect.top
				self.vy = 0

		self.rect.x += int(self.vx)
		if self.rect.left < self.patrol_min:
			self.rect.left = self.patrol_min
			self.vx = abs(self.vx)
		elif self.rect.right > self.patrol_max:
			self.rect.right = self.patrol_max
			self.vx = -abs(self.vx)

	def draw(self, surface, cam_x):
		if not self.alive:
			return
		r = self.rect.move(-cam_x, 0)
		pygame.draw.rect(surface, (213, 76, 76), r, border_radius=10)
		pygame.draw.circle(surface, (255, 255, 255), (r.x + 13, r.y + 12), 4)
		pygame.draw.circle(surface, (255, 255, 255), (r.x + 29, r.y + 12), 4)
		pygame.draw.circle(surface, (22, 22, 22), (r.x + 13, r.y + 12), 2)
		pygame.draw.circle(surface, (22, 22, 22), (r.x + 29, r.y + 12), 2)


class QuestionTarget:
	BUBBLE_OFFSETS = [(-52, -56), (52, -56), (-52, 56), (52, 56)]

	def __init__(self, x, y, level_index, gate_index=None):
		self.x = x
		self.y = y
		self.level_index = level_index
		self.problem = generate_problem(level_index)
		self.solved = False
		self.gate_index = gate_index
		self.bob = random.random() * 6.28

	def update(self):
		self.bob += 0.06

	def bubble_pos(self, idx):
		ox, oy = self.BUBBLE_OFFSETS[idx]
		return self.x + ox, self.y + oy + math.sin(self.bob) * 4

	def bubble_hit(self, px, py, radius):
		if self.solved:
			return None
		for i in range(4):
			bx, by = self.bubble_pos(i)
			dx, dy = px - bx, py - by
			if dx * dx + dy * dy <= (radius + 24) * (radius + 24):
				return i
		return None

	def answer(self, index):
		if self.solved:
			return False
		correct = index == self.problem["correct_index"]
		if correct:
			self.solved = True
		return correct

	def draw(self, surface, cam_x, font_small, font_tiny):
		base_y = self.y + math.sin(self.bob) * 4
		center = (int(self.x - cam_x), int(base_y))

		glow = 26 + int((math.sin(self.bob * 2.0) + 1) * 6)
		pygame.draw.circle(surface, (250, 255, 190), center, glow)
		pygame.draw.circle(surface, (87, 210, 255) if not self.solved else (100, 255, 145), center, 16)

		if self.solved:
			draw_text(surface, "OK", font_tiny, (25, 100, 30), center[0], center[1] - 9, center=True)
		else:
			draw_text(surface, "?", font_small, (25, 45, 90), center[0], center[1] - 12, center=True)

		if self.solved:
			return

		for i, option in enumerate(self.problem["options"]):
			bx, by = self.bubble_pos(i)
			sx, sy = int(bx - cam_x), int(by)
			color = (255, 255, 255)
			border = (90, 90, 130)
			pygame.draw.circle(surface, color, (sx, sy), 24)
			pygame.draw.circle(surface, border, (sx, sy), 24, 3)
			draw_text(surface, str(option), font_tiny, (30, 30, 40), sx, sy - 9, center=True)
			draw_text(surface, str(i + 1), font_tiny, (105, 105, 130), sx, sy + 9, center=True)


class Player:
	def __init__(self, x, y):
		self.rect = pygame.Rect(x, y, 40, 54)
		self.vx = 0
		self.vy = 0
		self.speed = 4.9
		self.max_sprint_speed = 7.2
		self.accel_ground = 0.62
		self.accel_air = 0.32
		self.friction_ground = 0.72
		self.jump_power = 12.5
		self.facing = 1
		self.on_ground = False
		self.extra_jumps = 1
		self.max_extra_jumps = 1
		self.coyote_timer = 0
		self.jump_buffer = 0
		self.shoot_cooldown = 0
		self.hurt_timer = 0
		self.anim_timer = 0

	def queue_jump(self):
		self.jump_buffer = 8

	def shoot_ready(self):
		return self.shoot_cooldown <= 0

	def update(self, keys, platforms, gates, jump_boost=False):
		move = 0
		if keys[pygame.K_a] or keys[pygame.K_LEFT]:
			move -= 1
		if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
			move += 1
		run_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
		jump_held = keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]

		top_speed = self.max_sprint_speed if run_held else self.speed
		target_speed = move * top_speed
		accel = self.accel_ground if self.on_ground else self.accel_air
		self.vx += (target_speed - self.vx) * accel

		if move == 0 and self.on_ground:
			self.vx *= self.friction_ground
			if abs(self.vx) < 0.14:
				self.vx = 0

		if move != 0:
			self.facing = 1 if move > 0 else -1

		jump_strength = self.jump_power * (1.28 if jump_boost else 1.0)

		if self.jump_buffer > 0:
			can_jump = self.on_ground or self.coyote_timer > 0
			can_double = self.extra_jumps > 0
			if can_jump:
				self.vy = -jump_strength
				self.on_ground = False
				self.coyote_timer = 0
				self.jump_buffer = 0
				return "jump"
			if can_double:
				self.vy = -jump_strength * 0.92
				self.extra_jumps -= 1
				self.jump_buffer = 0
				return "double_jump"

		# Variable jump height: releasing jump early shortens upward travel.
		if not jump_held and self.vy < -4.2:
			self.vy += 0.85

		self.vy += GRAVITY
		self.vy = min(self.vy, 15)

		self.rect.x += int(self.vx)
		for block in [p.rect for p in platforms] + [g.rect for g in gates if not g.opened]:
			if self.rect.colliderect(block):
				if self.vx > 0:
					self.rect.right = block.left
				elif self.vx < 0:
					self.rect.left = block.right
				self.vx = 0

		self.rect.y += int(self.vy)
		self.on_ground = False
		for block in [p.rect for p in platforms] + [g.rect for g in gates if not g.opened]:
			if self.rect.colliderect(block):
				if self.vy > 0:
					self.rect.bottom = block.top
					self.vy = 0
					self.on_ground = True
					self.extra_jumps = self.max_extra_jumps
				elif self.vy < 0:
					self.rect.top = block.bottom
					self.vy = 0

		if self.on_ground:
			self.coyote_timer = 8
		else:
			self.coyote_timer = max(0, self.coyote_timer - 1)

		self.jump_buffer = max(0, self.jump_buffer - 1)
		self.shoot_cooldown = max(0, self.shoot_cooldown - 1)
		self.hurt_timer = max(0, self.hurt_timer - 1)
		self.anim_timer += 1
		return None

	def draw(self, surface, cam_x):
		r = self.rect.move(-cam_x, 0)

		# Cute blob body with simple animation.
		bob = int(math.sin(self.anim_timer * 0.18) * 2)
		body = pygame.Rect(r.x, r.y + bob, r.w, r.h)
		body_color = (255, 173, 117) if self.hurt_timer % 6 < 3 else (255, 195, 136)
		pygame.draw.rect(surface, body_color, body, border_radius=14)
		pygame.draw.rect(surface, (255, 250, 240), body, 2, border_radius=14)

		# Eyes
		eyey = body.y + 17
		ex1 = body.x + 12
		ex2 = body.x + 28
		if self.facing < 0:
			ex1, ex2 = ex2, ex1
		pygame.draw.circle(surface, (255, 255, 255), (ex1, eyey), 5)
		pygame.draw.circle(surface, (255, 255, 255), (ex2, eyey), 5)
		pygame.draw.circle(surface, (25, 25, 25), (ex1 + self.facing, eyey), 2)
		pygame.draw.circle(surface, (25, 25, 25), (ex2 + self.facing, eyey), 2)

		# Tiny blaster arm.
		arm = (body.right + 6 * self.facing, body.y + 32)
		pygame.draw.line(surface, (235, 96, 72), (body.centerx, body.y + 30), arm, 4)


class Level:
	def __init__(self, index):
		self.index = index
		self.theme = THEMES[index]
		self.width = 3000 + index * 350
		self.height = HEIGHT

		self.platforms = []
		self.gates = []
		self.targets = []
		self.coins = []
		self.enemies = []
		self.door = pygame.Rect(self.width - 90, HEIGHT - 180, 46, 92)

		self._build_layout()

	def _build_layout(self):
		t = self.theme
		self.platforms.append(Platform(0, HEIGHT - 80, self.width, 80, t.ground))

		if self.index == 0:
			plat_data = [
				(260, 560, 180, 24),
				(520, 500, 210, 24),
				(840, 440, 210, 24),
				(1220, 520, 210, 24),
				(1550, 470, 230, 24),
				(1900, 410, 210, 24),
				(2260, 500, 210, 24),
			]
			target_positions = [(560, 438), (1280, 458), (1930, 350)]
			gate_positions = [(1020, HEIGHT - 220, 32, 140), (2140, HEIGHT - 240, 32, 160)]
		elif self.index == 1:
			plat_data = [
				(230, 560, 170, 24),
				(500, 500, 170, 24),
				(760, 430, 200, 24),
				(1090, 370, 170, 24),
				(1390, 460, 180, 24),
				(1730, 390, 220, 24),
				(2050, 330, 190, 24),
				(2400, 460, 190, 24),
			]
			target_positions = [(530, 442), (1120, 312), (1750, 330), (2420, 402)]
			gate_positions = [(1270, HEIGHT - 260, 36, 180), (2260, HEIGHT - 280, 36, 200)]
		else:
			plat_data = [
				(210, 560, 160, 24),
				(450, 500, 180, 24),
				(730, 430, 160, 24),
				(980, 360, 180, 24),
				(1250, 300, 200, 24),
				(1570, 380, 190, 24),
				(1840, 450, 170, 24),
				(2120, 520, 180, 24),
				(2410, 430, 190, 24),
				(2720, 340, 190, 24),
			]
			target_positions = [(485, 442), (1010, 302), (1600, 320), (2160, 462), (2760, 282)]
			gate_positions = [(1460, HEIGHT - 300, 40, 220), (2360, HEIGHT - 320, 40, 240)]

		for x, y, w, h in plat_data:
			self.platforms.append(Platform(x, y, w, h, t.ground))

		for gx, gy, gw, gh in gate_positions:
			self.gates.append(Gate(gx, gy, gw, gh))

		for i, pos in enumerate(target_positions):
			gate_index = i if i < len(self.gates) else None
			self.targets.append(QuestionTarget(pos[0], pos[1], self.index, gate_index))

		for x in range(180, self.width - 140, 165):
			y = random.choice([HEIGHT - 130, HEIGHT - 170, HEIGHT - 220, HEIGHT - 270])
			self.coins.append(Coin(x, y))

		# Patrol enemies anchored to selected platforms.
		enemy_spots = [self.platforms[min(2, len(self.platforms) - 1)], self.platforms[min(4, len(self.platforms) - 1)]]
		if self.index >= 1:
			enemy_spots.append(self.platforms[min(6, len(self.platforms) - 1)])
		if self.index == 2:
			enemy_spots.append(self.platforms[min(8, len(self.platforms) - 1)])

		for p in enemy_spots:
			self.enemies.append(Enemy(p.rect.x + 20, p.rect.y - 34, p.rect.x, p.rect.right))

	@property
	def solved_count(self):
		return sum(1 for t in self.targets if t.solved)

	@property
	def all_solved(self):
		return self.solved_count == len(self.targets)


class MathPlatformerGame:
	def __init__(self):
		pygame.init()
		pygame.display.set_caption("Math Kingdom Quest")
		self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
		self.clock = pygame.time.Clock()

		self.font_big = pygame.font.SysFont("arialrounded", 56)
		self.font_mid = pygame.font.SysFont("arialrounded", 34)
		self.font_small = pygame.font.SysFont("arialrounded", 24)
		self.font_tiny = pygame.font.SysFont("arialrounded", 18)

		self.running = True
		self.state = "menu"
		self.level_index = 0
		self.max_unlocked = 0

		self.level = None
		self.player = None
		self.projectiles = []
		self.particles = []
		self.camera_x = 0

		self.score = 0
		self.lives = 3
		self.combo = 0
		self.combo_timer = 0

		self.jump_boost_timer = 0
		self.freeze_timer = 0
		self.mega_timer = 0

		self.name_input = ""
		self.result_banner = ""
		self.leaderboard = safe_load_leaderboard(LEADERBOARD_FILE)

		self.confetti = []

	def stomp_enemy(self, enemy):
		enemy.alive = False
		self.player.vy = -9.5
		self.score += 70
		self.spawn_particles((enemy.rect.centerx, enemy.rect.centery), (255, 196, 98), count=18, spread=4.0)

	def reset_run(self, start_level=0):
		self.level_index = start_level
		self.score = 0
		self.lives = 3
		self.combo = 0
		self.combo_timer = 0
		self.jump_boost_timer = 0
		self.freeze_timer = 0
		self.mega_timer = 0
		self.load_level(self.level_index)

	def load_level(self, idx):
		self.level = Level(idx)
		self.player = Player(80, HEIGHT - 220)
		self.projectiles.clear()
		self.particles.clear()
		self.camera_x = 0

	def spawn_particles(self, pos, color, count=12, spread=3.8):
		for _ in range(count):
			ang = random.random() * math.pi * 2
			speed = random.random() * spread
			vel = (math.cos(ang) * speed, math.sin(ang) * speed - random.random() * 1.5)
			self.particles.append(Particle(pos, vel, color, life=random.randint(18, 40), size=random.randint(2, 6)))

	def nearest_unsolved_target(self):
		unsolved = [t for t in self.level.targets if not t.solved]
		if not unsolved:
			return None
		return min(unsolved, key=lambda t: abs(t.x - self.player.rect.centerx))

	def apply_correct_answer(self, target):
		now_combo = self.combo + 1 if self.combo_timer > 0 else 1
		self.combo = now_combo
		self.combo_timer = 260
		mult = 1 + min(4, self.combo - 1) * 0.2
		self.score += int(120 * mult)

		self.spawn_particles((target.x, target.y), (120, 255, 140), count=24, spread=4.5)

		if target.gate_index is not None and target.gate_index < len(self.level.gates):
			self.level.gates[target.gate_index].opened = True

		roll = random.random()
		if roll < 0.26:
			self.jump_boost_timer = 360
		elif roll < 0.52:
			self.freeze_timer = 260
		elif roll < 0.78:
			self.mega_timer = 320

	def apply_wrong_answer(self, target):
		self.combo = 0
		self.combo_timer = 0
		self.lives -= 1
		self.player.hurt_timer = 40
		self.spawn_particles((target.x, target.y), (255, 92, 92), count=20, spread=4.2)

		# Spawn a bonus enemy near the target as punishment.
		if len(self.level.enemies) < 8:
			ex = int(target.x + random.choice([-120, 120]))
			ex = clamp(ex, 60, self.level.width - 120)
			self.level.enemies.append(Enemy(ex, HEIGHT - 114, ex - 120, ex + 120))

		if self.lives <= 0:
			self.result_banner = "Game Over"
			self.state = "name_entry"

	def resolve_target_answer(self, target, option_index, from_projectile=False):
		if target.solved:
			return
		correct = option_index == target.problem["correct_index"]

		if (not correct) and self.mega_timer > 0 and from_projectile:
			# Mega Answer forgives projectile misses.
			correct = True

		if correct:
			target.solved = True
			self.apply_correct_answer(target)
		else:
			self.apply_wrong_answer(target)

	def shoot_projectile(self, target_x, target_y):
		if not self.player.shoot_ready():
			return
		px = self.player.rect.centerx + self.player.facing * 24
		py = self.player.rect.centery - 4
		dx = target_x - px
		dy = target_y - py
		dist = max(1.0, math.hypot(dx, dy))
		speed = 12.0
		vx, vy = dx / dist * speed, dy / dist * speed
		self.projectiles.append(Projectile(px, py, vx, vy, mega=self.mega_timer > 0))
		self.player.shoot_cooldown = 14

	def update_menu_input(self, event):
		if event.type != pygame.KEYDOWN:
			return
		if event.key in (pygame.K_RETURN, pygame.K_SPACE):
			self.reset_run(0)
			self.state = "playing"
		elif event.key == pygame.K_l:
			self.state = "level_select"
		elif event.key == pygame.K_q:
			self.running = False

	def update_level_select_input(self, event):
		if event.type != pygame.KEYDOWN:
			return
		if event.key == pygame.K_ESCAPE:
			self.state = "menu"
			return
		if pygame.K_1 <= event.key <= pygame.K_3:
			idx = event.key - pygame.K_1
			if idx <= self.max_unlocked:
				self.reset_run(idx)
				self.state = "playing"

	def update_name_entry_input(self, event):
		if event.type == pygame.KEYDOWN:
			if event.key == pygame.K_RETURN:
				name = self.name_input.strip() or "Player"
				self.leaderboard.append({"name": name[:12], "score": int(self.score)})
				save_leaderboard(LEADERBOARD_FILE, self.leaderboard)
				self.leaderboard = safe_load_leaderboard(LEADERBOARD_FILE)
				self.name_input = ""
				self.state = "menu"
			elif event.key == pygame.K_BACKSPACE:
				self.name_input = self.name_input[:-1]
			else:
				if len(self.name_input) < 12 and event.unicode.isprintable() and event.unicode not in "\r\n\t":
					self.name_input += event.unicode

	def update_playing_input(self, event):
		if event.type == pygame.KEYDOWN:
			if event.key in (pygame.K_w, pygame.K_UP, pygame.K_SPACE):
				self.player.queue_jump()
			elif pygame.K_1 <= event.key <= pygame.K_4:
				target = self.nearest_unsolved_target()
				if target:
					idx = event.key - pygame.K_1
					self.resolve_target_answer(target, idx)
			elif event.key == pygame.K_ESCAPE:
				self.state = "menu"

		if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
			mx, my = event.pos
			world_x = mx + self.camera_x
			# Clicking on an answer bubble selects that answer.
			for target in self.level.targets:
				if target.solved:
					continue
				for i in range(4):
					bx, by = target.bubble_pos(i)
					if (world_x - bx) ** 2 + (my - by) ** 2 <= 24 ** 2:
						self.resolve_target_answer(target, i)
						return
			# Otherwise, shoot toward cursor.
			self.shoot_projectile(world_x, my)

	def update_playing(self):
		keys = pygame.key.get_pressed()
		jump_state = self.player.update(keys, self.level.platforms, self.level.gates, jump_boost=self.jump_boost_timer > 0)

		if jump_state == "jump":
			self.spawn_particles((self.player.rect.centerx, self.player.rect.bottom), (255, 238, 126), count=10)
		elif jump_state == "double_jump":
			self.spawn_particles((self.player.rect.centerx, self.player.rect.bottom), (137, 231, 255), count=18)

		if self.player.rect.top > HEIGHT + 120:
			self.lives -= 1
			self.player.rect.topleft = (80, HEIGHT - 220)
			self.player.vx = 0
			self.player.vy = 0
			self.spawn_particles((self.player.rect.centerx, HEIGHT - 30), (255, 90, 90), count=20)
			if self.lives <= 0:
				self.result_banner = "Game Over"
				self.state = "name_entry"

		self.camera_x = clamp(self.player.rect.centerx - WIDTH // 2, 0, self.level.width - WIDTH)

		# Update targets.
		for target in self.level.targets:
			target.update()

		# Update coins.
		for coin in self.level.coins:
			coin.update()
			if not coin.collected and self.player.rect.colliderect(coin.rect):
				coin.collected = True
				self.score += 15
				self.spawn_particles((coin.rect.centerx, coin.rect.centery), (255, 240, 120), count=10)

		# Update enemies and damage handling.
		for enemy in self.level.enemies:
			enemy.update(self.level.platforms, freeze=self.freeze_timer > 0)
			if enemy.alive and self.player.rect.colliderect(enemy.rect):
				stomped = self.player.vy > 1 and self.player.rect.bottom - enemy.rect.top < 20
				if stomped:
					self.stomp_enemy(enemy)
				elif self.player.hurt_timer <= 0:
					self.lives -= 1
					self.player.hurt_timer = 90
					self.player.vx = -8 if self.player.rect.centerx < enemy.rect.centerx else 8
					self.player.vy = -6
					self.spawn_particles((self.player.rect.centerx, self.player.rect.centery), (255, 90, 90), count=20)
					if self.lives <= 0:
						self.result_banner = "Game Over"
						self.state = "name_entry"

		# Update projectiles.
		for proj in self.projectiles:
			proj.update()
			# Projectile vs terrain.
			if proj.y > HEIGHT + 60 or proj.x < -100 or proj.x > self.level.width + 100:
				proj.life = 0
				continue
			for p in self.level.platforms:
				if circle_rect_collision(proj.x, proj.y, proj.radius, p.rect):
					proj.life = 0
					break

			if proj.dead:
				continue

			# Projectile vs enemies.
			for enemy in self.level.enemies:
				if enemy.alive and circle_rect_collision(proj.x, proj.y, proj.radius, enemy.rect):
					enemy.alive = False
					proj.life = 0
					self.score += 50
					self.spawn_particles((enemy.rect.centerx, enemy.rect.centery), (255, 170, 110), count=16, spread=4.0)
					break

			if proj.dead:
				continue

			# Projectile vs target options.
			for target in self.level.targets:
				idx = target.bubble_hit(proj.x, proj.y, proj.radius)
				if idx is not None:
					self.resolve_target_answer(target, idx, from_projectile=True)
					proj.life = 0
					break

		self.projectiles = [p for p in self.projectiles if not p.dead]

		# Update particles.
		for p in self.particles:
			p.update()
		self.particles = [p for p in self.particles if not p.dead]

		self.jump_boost_timer = max(0, self.jump_boost_timer - 1)
		self.freeze_timer = max(0, self.freeze_timer - 1)
		self.mega_timer = max(0, self.mega_timer - 1)
		self.combo_timer = max(0, self.combo_timer - 1)
		if self.combo_timer == 0:
			self.combo = 0

		# Level completion at the door once all questions are solved.
		if self.level.all_solved and self.player.rect.colliderect(self.level.door):
			self.score += 450
			self.max_unlocked = max(self.max_unlocked, self.level_index + 1)
			if self.level_index >= 2:
				self.result_banner = "Victory"
				self.confetti = []
				for _ in range(220):
					self.confetti.append(
						Particle(
							(random.randint(0, WIDTH), random.randint(-220, -20)),
							(random.uniform(-1.2, 1.2), random.uniform(1.5, 4.2)),
							random.choice([(255, 120, 120), (120, 220, 255), (255, 240, 120), (150, 255, 170)]),
							life=random.randint(80, 140),
							size=random.randint(3, 6),
							gravity=0.06,
						)
					)
				self.state = "name_entry"
			else:
				self.level_index += 1
				self.load_level(self.level_index)

	def draw_parallax(self):
		t = self.level.theme
		self.screen.fill(t.sky)

		# Far hills/clouds.
		far_speed = self.camera_x * 0.2
		for i in range(8):
			x = int((i * 260 - far_speed) % (WIDTH + 320) - 160)
			y = 120 + (i % 3) * 28
			pygame.draw.ellipse(self.screen, t.far, (x, y, 280, 120))

		# Mid layer silhouettes.
		mid_speed = self.camera_x * 0.45
		for i in range(10):
			x = int((i * 190 - mid_speed) % (WIDTH + 260) - 130)
			base = HEIGHT - 220 + (i % 2) * 16
			pygame.draw.polygon(
				self.screen,
				t.mid,
				[(x, HEIGHT), (x + 90, base), (x + 170, HEIGHT)],
			)

	def draw_playing(self):
		self.draw_parallax()

		# Level door.
		door = self.level.door.move(-self.camera_x, 0)
		door_col = (106, 255, 146) if self.level.all_solved else (220, 120, 120)
		pygame.draw.rect(self.screen, door_col, door, border_radius=10)
		pygame.draw.rect(self.screen, (245, 245, 245), door, 2, border_radius=10)

		for platform in self.level.platforms:
			platform.draw(self.screen, self.camera_x)

		for gate in self.level.gates:
			gate.draw(self.screen, self.camera_x)

		for coin in self.level.coins:
			coin.draw(self.screen, self.camera_x)

		for target in self.level.targets:
			target.draw(self.screen, self.camera_x, self.font_small, self.font_tiny)

		for enemy in self.level.enemies:
			enemy.draw(self.screen, self.camera_x)

		for proj in self.projectiles:
			proj.draw(self.screen, self.camera_x)

		self.player.draw(self.screen, self.camera_x)

		for p in self.particles:
			p.draw(self.screen, self.camera_x)

		self.draw_hud()

	def draw_hud(self):
		panel = pygame.Rect(12, 12, WIDTH - 24, 102)
		pygame.draw.rect(self.screen, (20, 28, 42), panel, border_radius=12)
		pygame.draw.rect(self.screen, (95, 127, 175), panel, 2, border_radius=12)

		draw_text(self.screen, f"Level: {self.level_index + 1} - {LEVEL_NAMES[self.level_index]}", self.font_tiny, (212, 233, 255), 28, 22)
		draw_text(self.screen, f"Score: {self.score}", self.font_small, (255, 240, 155), 28, 44)
		draw_text(self.screen, f"Lives: {self.lives}", self.font_small, (255, 156, 156), 240, 44)
		draw_text(self.screen, f"Combo: x{self.combo}" if self.combo > 1 else "Combo: -", self.font_small, (162, 255, 186), 410, 44)

		target = self.nearest_unsolved_target()
		if target:
			q = target.problem
			draw_text(self.screen, f"Question: {q['text']}", self.font_small, (234, 245, 255), 620, 26)
			draw_text(
				self.screen,
				f"1:{q['options'][0]}  2:{q['options'][1]}  3:{q['options'][2]}  4:{q['options'][3]}",
				self.font_tiny,
				(200, 220, 255),
				620,
				58,
			)
		else:
			draw_text(self.screen, "All targets solved! Reach the glowing door.", self.font_small, (164, 255, 181), 620, 42)

		boosts = []
		if self.jump_boost_timer > 0:
			boosts.append("Multiply Jump")
		if self.freeze_timer > 0:
			boosts.append("Freeze Time")
		if self.mega_timer > 0:
			boosts.append("Mega Answer")
		draw_text(self.screen, "Power-Ups: " + (", ".join(boosts) if boosts else "None"), self.font_tiny, (255, 221, 171), 28, 78)
		draw_text(self.screen, "Hold Shift to sprint. Stomp enemies from above.", self.font_tiny, (194, 218, 255), 440, 78)

	def draw_menu(self):
		self.screen.fill((30, 43, 74))

		# Background blobs.
		for i in range(7):
			pygame.draw.circle(
				self.screen,
				random.choice([(76, 128, 220), (255, 153, 122), (114, 222, 169)]),
				(140 + i * 190, 130 + (i % 2) * 90),
				110,
				0,
			)

		draw_text(self.screen, "Math Kingdom Quest", self.font_big, (255, 247, 196), WIDTH // 2, 130, center=True)
		draw_text(self.screen, "Math Platformer", self.font_mid, (218, 235, 255), WIDTH // 2, 194, center=True)

		draw_text(self.screen, "ENTER / SPACE - Start Adventure", self.font_small, (255, 255, 255), WIDTH // 2, 310, center=True)
		draw_text(self.screen, "L - Level Select", self.font_small, (255, 255, 255), WIDTH // 2, 352, center=True)
		draw_text(self.screen, "WASD / Arrows: Move    SHIFT: Sprint    SPACE: Jump/Double Jump", self.font_tiny, (230, 230, 255), WIDTH // 2, 406, center=True)
		draw_text(self.screen, "Mouse click: Select answer or shoot orb    Keys 1-4: Quick answer", self.font_tiny, (230, 230, 255), WIDTH // 2, 432, center=True)
		draw_text(self.screen, "Q - Quit", self.font_tiny, (255, 205, 205), WIDTH // 2, 470, center=True)

		draw_text(self.screen, "Leaderboard", self.font_small, (255, 240, 155), 80, 540)
		if not self.leaderboard:
			draw_text(self.screen, "No scores yet.", self.font_tiny, (235, 235, 250), 82, 576)
		else:
			for i, row in enumerate(self.leaderboard[:5], start=1):
				draw_text(self.screen, f"{i}. {row['name']}  -  {row['score']}", self.font_tiny, (235, 235, 250), 82, 548 + i * 24)

	def draw_level_select(self):
		self.screen.fill((18, 20, 46))
		draw_text(self.screen, "Select Level", self.font_big, (245, 236, 180), WIDTH // 2, 110, center=True)
		draw_text(self.screen, "Press 1 / 2 / 3", self.font_small, (235, 245, 255), WIDTH // 2, 180, center=True)
		draw_text(self.screen, "ESC to return", self.font_tiny, (220, 220, 235), WIDTH // 2, 214, center=True)

		for i, name in enumerate(LEVEL_NAMES):
			y = 300 + i * 120
			unlocked = i <= self.max_unlocked
			color = (115, 220, 155) if unlocked else (90, 90, 120)
			label = f"{i + 1}. {name}" + ("" if unlocked else " (Locked)")
			pygame.draw.rect(self.screen, color, (WIDTH // 2 - 210, y, 420, 70), border_radius=12)
			draw_text(self.screen, label, self.font_mid, (20, 24, 45) if unlocked else (215, 215, 230), WIDTH // 2, y + 36, center=True)

	def draw_name_entry(self):
		self.screen.fill((26, 26, 36))

		if self.result_banner == "Victory":
			for p in self.confetti:
				p.update()
				p.draw(self.screen, 0)

		draw_text(self.screen, self.result_banner, self.font_big, (255, 240, 155), WIDTH // 2, 140, center=True)
		draw_text(self.screen, f"Final Score: {self.score}", self.font_mid, (223, 239, 255), WIDTH // 2, 220, center=True)
		draw_text(self.screen, "Enter your name and press ENTER", self.font_small, (235, 235, 250), WIDTH // 2, 292, center=True)

		box = pygame.Rect(WIDTH // 2 - 220, 344, 440, 72)
		pygame.draw.rect(self.screen, (42, 55, 82), box, border_radius=10)
		pygame.draw.rect(self.screen, (190, 212, 255), box, 2, border_radius=10)
		draw_text(self.screen, self.name_input + ("_" if (pygame.time.get_ticks() // 400) % 2 == 0 else ""), self.font_mid, (255, 255, 255), WIDTH // 2, 380, center=True)

	def handle_events(self):
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				self.running = False
				return

			if self.state == "menu":
				self.update_menu_input(event)
			elif self.state == "level_select":
				self.update_level_select_input(event)
			elif self.state == "playing":
				self.update_playing_input(event)
			elif self.state == "name_entry":
				self.update_name_entry_input(event)

	def run(self):
		while self.running:
			self.clock.tick(FPS)
			self.handle_events()

			if self.state == "playing":
				self.update_playing()

			if self.state == "menu":
				self.draw_menu()
			elif self.state == "level_select":
				self.draw_level_select()
			elif self.state == "playing":
				self.draw_playing()
			elif self.state == "name_entry":
				self.draw_name_entry()

			pygame.display.flip()

		pygame.quit()
		sys.exit()


if __name__ == "__main__":
	game = MathPlatformerGame()
	game.run()
