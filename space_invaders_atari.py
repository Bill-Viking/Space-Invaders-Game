"""
Space Invaders - Atari 2600 Authentic Recreation
With period-appropriate CRT effects (phosphor glow, color bleed, sync wobble)

Controls:
- Arrow keys to move
- Spacebar to shoot
- R to restart
- Q or Esc to quit
- F3 on title or game-over screen for a hidden little something
"""

import pygame
import random
import math
import os
import sys

# Initialize pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Atari 2600 authentic resolution (scaled up)
NATIVE_WIDTH = 160
NATIVE_HEIGHT = 210
SCALE = 4
SCREEN_WIDTH = NATIVE_WIDTH * SCALE
SCREEN_HEIGHT = NATIVE_HEIGHT * SCALE

# Create surfaces
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
game_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
glow_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT), pygame.SRCALPHA)
pygame.display.set_caption("Space Invaders - Atari 2600")

clock = pygame.time.Clock()

# Atari 2600 authentic NTSC color palette
BLACK = (0, 0, 0)
ATARI_GREEN = (0, 200, 0)
ATARI_YELLOW = (200, 200, 0)
ATARI_WHITE = (200, 200, 200)
ATARI_RED = (200, 60, 60)
ATARI_ORANGE = (200, 120, 40)
ATARI_BLUE = (60, 120, 200)

# CRT effect variables
crt_wobble = 0
crt_noise = []
phosphor_persist = []

# Game effect variables
screen_shake = 0
screen_shake_intensity = 0
particles = []
flash_screen = 0

# High score persistence
HIGH_SCORE_PATH = os.path.join(os.path.expanduser("~"), ".space_invaders_atari_highscore")

def load_high_score():
    try:
        with open(HIGH_SCORE_PATH) as f:
            return int(f.read().strip() or "0")
    except Exception:
        return 0

def save_high_score(s):
    try:
        with open(HIGH_SCORE_PATH, "w") as f:
            f.write(str(int(s)))
    except Exception:
        pass


# Sound generation (authentic Atari TIA-style)
def generate_sound(frequency, duration_ms, volume=0.3):
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytes([128 + int(127 * volume * (1 if (i * frequency // sample_rate) % 2 == 0 else -1))
                 for i in range(n_samples)])
    sound = pygame.mixer.Sound(buffer=buf)
    return sound

# Create sounds
try:
    shoot_sound = generate_sound(880, 50, 0.2)
    explosion_sound = generate_sound(110, 150, 0.3)
    invader_move_sounds = [
        generate_sound(55, 60, 0.2),
        generate_sound(49, 60, 0.2),
        generate_sound(44, 60, 0.2),
        generate_sound(41, 60, 0.2),
    ]
    player_death_sound = generate_sound(80, 300, 0.4)
    ufo_sound = generate_sound(300, 100, 0.15)
except:
    shoot_sound = None
    explosion_sound = None
    invader_move_sounds = [None] * 4
    player_death_sound = None
    ufo_sound = None

def play_sound(sound):
    if sound:
        try:
            sound.play()
        except:
            pass


# Chunky 3x5 pixel letters for title / end screens (Atari-style)
LETTERS = {
    'A': ["010","101","111","101","101"],
    'B': ["110","101","110","101","110"],
    'C': ["011","100","100","100","011"],
    'D': ["110","101","101","101","110"],
    'E': ["111","100","110","100","111"],
    'F': ["111","100","110","100","100"],
    'G': ["011","100","101","101","011"],
    'H': ["101","101","111","101","101"],
    'I': ["111","010","010","010","111"],
    'J': ["001","001","001","101","010"],
    'K': ["101","110","100","110","101"],
    'L': ["100","100","100","100","111"],
    'M': ["101","111","111","101","101"],
    'N': ["101","111","111","111","101"],
    'O': ["010","101","101","101","010"],
    'P': ["110","101","110","100","100"],
    'Q': ["010","101","101","110","011"],
    'R': ["110","101","110","101","101"],
    'S': ["011","100","010","001","110"],
    'T': ["111","010","010","010","010"],
    'U': ["101","101","101","101","011"],
    'V': ["101","101","101","101","010"],
    'W': ["101","101","111","111","101"],
    'X': ["101","101","010","101","101"],
    'Y': ["101","101","010","010","010"],
    'Z': ["111","001","010","100","111"],
    '0': ["111","101","101","101","111"],
    '1': ["010","110","010","010","111"],
    '2': ["110","001","010","100","111"],
    '3': ["110","001","010","001","110"],
    '4': ["101","101","111","001","001"],
    '5': ["111","100","110","001","110"],
    '6': ["011","100","110","101","010"],
    '7': ["111","001","010","010","010"],
    '8': ["010","101","010","101","010"],
    '9': ["010","101","011","001","110"],
    ' ': ["000","000","000","000","000"],
    '.': ["000","000","000","000","010"],
    '-': ["000","000","111","000","000"],
    ':': ["000","010","000","010","000"],
    '!': ["010","010","010","000","010"],
}

def draw_text(surface, text, x, y, color):
    text = text.upper()
    cx = x
    for ch in text:
        pat = LETTERS.get(ch, LETTERS[' '])
        for row_i, row in enumerate(pat):
            for col_i, c in enumerate(row):
                if c == '1':
                    px, py = cx + col_i, y + row_i
                    if 0 <= px < NATIVE_WIDTH and 0 <= py < NATIVE_HEIGHT:
                        surface.set_at((px, py), color)
        cx += 4

def draw_text_centered(surface, text, y, color):
    w = len(text) * 4 - 1
    draw_text(surface, text, NATIVE_WIDTH // 2 - w // 2, y, color)


class Particle:
    """Explosion particle - chunky pixels like Atari"""
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(0.3, 1.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(10, 30)
        self.max_life = self.life
        self.size = random.randint(1, 2)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.03
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            # Flicker like old CRT
            if random.random() > 0.1:
                brightness = self.life / self.max_life
                color = tuple(int(c * brightness) for c in self.color)
                x, y = int(self.x), int(self.y)
                if 0 <= x < NATIVE_WIDTH - 1 and 0 <= y < NATIVE_HEIGHT - 1:
                    pygame.draw.rect(surface, color, (x, y, self.size, self.size))


class Player:
    def __init__(self):
        self.width = 9
        self.height = 8
        self.x = NATIVE_WIDTH // 2 - self.width // 2
        self.y = NATIVE_HEIGHT - 24
        self.speed = 2
        self.color = ATARI_GREEN
        self.respawn_timer = 0
        self.alive = True

    def draw(self, surface):
        if not self.alive:
            return
        if self.respawn_timer > 0:
            if (self.respawn_timer // 4) % 2 == 0:
                return

        x, y = int(self.x), int(self.y)
        color = self.color

        # Authentic Atari 2600 cannon
        pygame.draw.rect(surface, color, (x + 4, y, 1, 2))
        pygame.draw.rect(surface, color, (x + 3, y + 2, 3, 1))
        pygame.draw.rect(surface, color, (x + 2, y + 3, 5, 1))
        pygame.draw.rect(surface, color, (x + 1, y + 4, 7, 1))
        pygame.draw.rect(surface, color, (x, y + 5, 9, 3))

    def move(self, direction):
        if self.respawn_timer > 0 or not self.alive:
            return
        if direction == "left" and self.x > 8:
            self.x -= self.speed
        if direction == "right" and self.x < NATIVE_WIDTH - self.width - 8:
            self.x += self.speed

    def update(self):
        if self.respawn_timer > 0:
            self.respawn_timer -= 1


class Bullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 4
        self.color = ATARI_YELLOW

    def draw(self, surface):
        # Slightly glowy bullet
        pygame.draw.rect(surface, self.color, (int(self.x), int(self.y), 1, 6))

    def move(self):
        self.y -= self.speed


class Invader:
    def __init__(self, x, y, row):
        self.width = 8
        self.height = 8
        self.x = x
        self.y = y
        self.row = row
        self.color = ATARI_WHITE
        self.frame = 0

    def draw(self, surface):
        x, y = int(self.x), int(self.y)
        c = self.color

        if self.row < 2:
            # Squid
            if self.frame == 0:
                pygame.draw.rect(surface, c, (x + 3, y, 2, 1))
                pygame.draw.rect(surface, c, (x + 2, y + 1, 4, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 2, 6, 1))
                pygame.draw.rect(surface, c, (x, y + 3, 8, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 4, 2, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 4, 2, 1))
                pygame.draw.rect(surface, c, (x + 2, y + 5, 1, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 5, 1, 1))
            else:
                pygame.draw.rect(surface, c, (x + 3, y, 2, 1))
                pygame.draw.rect(surface, c, (x + 2, y + 1, 4, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 2, 6, 1))
                pygame.draw.rect(surface, c, (x, y + 3, 8, 1))
                pygame.draw.rect(surface, c, (x, y + 4, 2, 1))
                pygame.draw.rect(surface, c, (x + 6, y + 4, 2, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 5, 1, 1))
                pygame.draw.rect(surface, c, (x + 6, y + 5, 1, 1))
        elif self.row < 4:
            # Crab
            if self.frame == 0:
                pygame.draw.rect(surface, c, (x + 2, y, 1, 1))
                pygame.draw.rect(surface, c, (x + 5, y, 1, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 1, 6, 1))
                pygame.draw.rect(surface, c, (x, y + 2, 8, 1))
                pygame.draw.rect(surface, c, (x, y + 3, 3, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 3, 3, 1))
                pygame.draw.rect(surface, c, (x, y + 4, 8, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 5, 2, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 5, 2, 1))
            else:
                pygame.draw.rect(surface, c, (x + 2, y, 1, 1))
                pygame.draw.rect(surface, c, (x + 5, y, 1, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 1, 6, 1))
                pygame.draw.rect(surface, c, (x, y + 2, 8, 1))
                pygame.draw.rect(surface, c, (x, y + 3, 3, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 3, 3, 1))
                pygame.draw.rect(surface, c, (x, y + 4, 8, 1))
                pygame.draw.rect(surface, c, (x, y + 5, 1, 1))
                pygame.draw.rect(surface, c, (x + 2, y + 5, 1, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 5, 1, 1))
                pygame.draw.rect(surface, c, (x + 7, y + 5, 1, 1))
        else:
            # Octopus
            if self.frame == 0:
                pygame.draw.rect(surface, c, (x + 2, y, 4, 1))
                pygame.draw.rect(surface, c, (x, y + 1, 8, 2))
                pygame.draw.rect(surface, c, (x + 1, y + 3, 2, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 3, 2, 1))
                pygame.draw.rect(surface, c, (x, y + 4, 8, 1))
                pygame.draw.rect(surface, c, (x + 1, y + 5, 2, 1))
                pygame.draw.rect(surface, c, (x + 4, y + 5, 3, 1))
            else:
                pygame.draw.rect(surface, c, (x + 2, y, 4, 1))
                pygame.draw.rect(surface, c, (x, y + 1, 8, 2))
                pygame.draw.rect(surface, c, (x + 1, y + 3, 2, 1))
                pygame.draw.rect(surface, c, (x + 5, y + 3, 2, 1))
                pygame.draw.rect(surface, c, (x, y + 4, 8, 1))
                pygame.draw.rect(surface, c, (x, y + 5, 2, 1))
                pygame.draw.rect(surface, c, (x + 3, y + 5, 2, 1))
                pygame.draw.rect(surface, c, (x + 6, y + 5, 2, 1))


class EnemyBullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.speed = 2
        self.color = ATARI_RED
        self.frame = 0

    def draw(self, surface):
        x, y = int(self.x), int(self.y)
        pattern = self.frame % 3
        for i in range(4):
            px = x + ((i + pattern) % 2)
            if 0 <= px < NATIVE_WIDTH and 0 <= y + i < NATIVE_HEIGHT:
                surface.set_at((px, y + i), self.color)
        self.frame += 1

    def move(self):
        self.y += self.speed


class Shield:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.color = ATARI_GREEN
        self.pixels = [
            [0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0],
            [0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0],
            [0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0],
            [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1],
            [1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1],
            [1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1],
        ]
        self.width = len(self.pixels[0])
        self.height = len(self.pixels)

    def draw(self, surface):
        for row_idx, row in enumerate(self.pixels):
            for col_idx, pixel in enumerate(row):
                if pixel:
                    surface.set_at((int(self.x) + col_idx, int(self.y) + row_idx), self.color)

    def damage(self, hit_x, hit_y):
        local_x = int(hit_x - self.x)
        local_y = int(hit_y - self.y)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                px, py = local_x + dx, local_y + dy
                if 0 <= py < self.height and 0 <= px < self.width:
                    self.pixels[py][px] = 0

    def check_collision(self, x, y):
        local_x = int(x - self.x)
        local_y = int(y - self.y)
        if 0 <= local_x < self.width and 0 <= local_y < self.height:
            return self.pixels[local_y][local_x] == 1
        return False


class UFO:
    def __init__(self):
        self.width = 10
        self.height = 4
        self.active = False
        self.x = 0
        self.y = 24
        self.direction = 1
        self.speed = 1
        self.color = ATARI_ORANGE
        self.points = [100, 50, 50, 100, 150, 100, 100, 50, 300, 100]
        self.shot_count = 0
        self.sound_timer = 0

    def spawn(self):
        if not self.active and random.random() < 0.001:
            self.active = True
            self.direction = random.choice([-1, 1])
            self.x = -self.width if self.direction == 1 else NATIVE_WIDTH

    def update(self):
        if self.active:
            self.x += self.speed * self.direction
            self.sound_timer += 1
            if self.sound_timer >= 10:
                play_sound(ufo_sound)
                self.sound_timer = 0
            if self.x < -self.width or self.x > NATIVE_WIDTH:
                self.active = False

    def draw(self, surface):
        if self.active:
            x, y = int(self.x), int(self.y)
            pygame.draw.rect(surface, self.color, (x + 3, y, 4, 1))
            pygame.draw.rect(surface, self.color, (x + 1, y + 1, 8, 1))
            pygame.draw.rect(surface, self.color, (x, y + 2, 10, 1))
            pygame.draw.rect(surface, self.color, (x + 2, y + 3, 2, 1))
            pygame.draw.rect(surface, self.color, (x + 6, y + 3, 2, 1))

    def get_score(self):
        score = self.points[self.shot_count % len(self.points)]
        self.shot_count += 1
        return score


def create_invaders():
    invaders = []
    for row in range(6):
        for col in range(6):
            x = 16 + col * 16
            y = 40 + row * 12
            invaders.append(Invader(x, y, row))
    return invaders


def create_shields():
    shields = []
    for pos in [16, 50, 84, 118]:
        shields.append(Shield(pos, NATIVE_HEIGHT - 55))
    return shields


def spawn_particles(x, y, color, count=12):
    for _ in range(count):
        particles.append(Particle(x, y, color))


def apply_crt_effects(surface, target_surface, frame_count):
    """Apply period-appropriate CRT effects"""
    global crt_wobble

    # Scale up first
    scaled = pygame.transform.scale(surface, (SCREEN_WIDTH, SCREEN_HEIGHT))

    # Horizontal sync wobble (subtle, like a slightly mistuned TV)
    crt_wobble = math.sin(frame_count * 0.02) * 1.5
    wobble_offset = int(crt_wobble)

    # Create final surface
    final = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    final.fill(BLACK)

    # Apply slight horizontal offset per scanline group (RF interference look)
    for y in range(0, SCREEN_HEIGHT, 8):
        offset = wobble_offset + random.randint(-1, 1) if random.random() < 0.05 else wobble_offset
        chunk_height = min(8, SCREEN_HEIGHT - y)
        final.blit(scaled, (offset, y), (0, y, SCREEN_WIDTH, chunk_height))

    # Phosphor glow / color bleeding (period appropriate)
    glow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    # Simulate phosphor persistence - slight blur/glow
    for y in range(0, SCREEN_HEIGHT, SCALE):
        for x in range(0, SCREEN_WIDTH, SCALE):
            pixel = final.get_at((min(x, SCREEN_WIDTH-1), min(y, SCREEN_HEIGHT-1)))
            if pixel[0] > 50 or pixel[1] > 50 or pixel[2] > 50:
                # Add subtle glow around bright pixels
                glow_color = (pixel[0]//4, pixel[1]//4, pixel[2]//4, 30)
                pygame.draw.rect(glow, glow_color, (x-2, y-2, SCALE+4, SCALE+4))

    final.blit(glow, (0, 0), special_flags=pygame.BLEND_ADD)

    # Scanlines (authentic CRT look)
    scanline_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for y in range(0, SCREEN_HEIGHT, 2):
        # Alternating dark lines
        alpha = 60 + random.randint(-10, 10)  # Slight flicker
        pygame.draw.line(scanline_surface, (0, 0, 0, alpha), (0, y), (SCREEN_WIDTH, y))

    final.blit(scanline_surface, (0, 0))

    # Occasional vertical roll artifact (like bad tracking)
    if random.random() < 0.002:
        roll_y = random.randint(0, SCREEN_HEIGHT - 20)
        pygame.draw.rect(final, (40, 40, 40), (0, roll_y, SCREEN_WIDTH, 3))

    # Screen curvature vignette (darker at edges like old CRTs)
    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for i in range(30):
        alpha = int(3 * (30 - i) / 30)
        pygame.draw.rect(vignette, (0, 0, 0, alpha),
                        (i*2, i*2, SCREEN_WIDTH - i*4, SCREEN_HEIGHT - i*4), 2)
    final.blit(vignette, (0, 0))

    target_surface.blit(final, (0, 0))


def draw_digit(digit, x, y, color, surface):
    patterns = {
        0: [(0,0),(1,0),(2,0),(0,1),(2,1),(0,2),(2,2),(0,3),(2,3),(0,4),(1,4),(2,4)],
        1: [(1,0),(1,1),(1,2),(1,3),(1,4)],
        2: [(0,0),(1,0),(2,0),(2,1),(0,2),(1,2),(2,2),(0,3),(0,4),(1,4),(2,4)],
        3: [(0,0),(1,0),(2,0),(2,1),(0,2),(1,2),(2,2),(2,3),(0,4),(1,4),(2,4)],
        4: [(0,0),(2,0),(0,1),(2,1),(0,2),(1,2),(2,2),(2,3),(2,4)],
        5: [(0,0),(1,0),(2,0),(0,1),(0,2),(1,2),(2,2),(2,3),(0,4),(1,4),(2,4)],
        6: [(0,0),(1,0),(2,0),(0,1),(0,2),(1,2),(2,2),(0,3),(2,3),(0,4),(1,4),(2,4)],
        7: [(0,0),(1,0),(2,0),(2,1),(2,2),(2,3),(2,4)],
        8: [(0,0),(1,0),(2,0),(0,1),(2,1),(0,2),(1,2),(2,2),(0,3),(2,3),(0,4),(1,4),(2,4)],
        9: [(0,0),(1,0),(2,0),(0,1),(2,1),(0,2),(1,2),(2,2),(2,3),(0,4),(1,4),(2,4)],
    }
    for px, py in patterns.get(digit, []):
        if 0 <= x + px < NATIVE_WIDTH and 0 <= y + py < NATIVE_HEIGHT:
            surface.set_at((x + px, y + py), color)


def draw_score(surface, score, lives, high_score):
    score_str = str(score).zfill(4)
    for i, digit in enumerate(score_str):
        draw_digit(int(digit), 8 + i * 5, 8, ATARI_YELLOW, surface)

    # HI label + high score in upper middle
    hi_str = str(high_score).zfill(4)
    hi_x = NATIVE_WIDTH // 2 - 12
    draw_text(surface, "HI", hi_x, 8, ATARI_ORANGE)
    for i, digit in enumerate(hi_str):
        draw_digit(int(digit), hi_x + 10 + i * 4, 8, ATARI_ORANGE, surface)

    lives_str = str(max(0, lives))
    for i, digit in enumerate(lives_str):
        draw_digit(int(digit), NATIVE_WIDTH - 16 + i * 5, 8, ATARI_GREEN, surface)


def draw_game_over(surface, frame):
    """Draw flashing GAME OVER text"""
    if (frame // 12) % 2 == 0:
        draw_text_centered(surface, "GAME OVER", 88, ATARI_RED)
        draw_text_centered(surface, "PRESS R", 104, ATARI_WHITE)


# === Easter egg: Close Encounters of the Third Kind, Atari-styled ===
def play_close_encounters():
    """15-second tribute, rendered through the same CRT pipeline for period feel."""
    pygame.mixer.stop()

    # TIA-style square-wave five-note motif (D, E, C, C lower, G)
    try:
        tones = [
            generate_sound(294, 500, 0.3),
            generate_sound(330, 500, 0.3),
            generate_sound(262, 500, 0.3),
            generate_sound(131, 600, 0.35),
            generate_sound(392, 600, 0.3),
        ]
        reply = [
            generate_sound(220, 550, 0.35),
            generate_sound(247, 550, 0.35),
            generate_sound(196, 550, 0.35),
            generate_sound(98,  650, 0.4),
            generate_sound(294, 650, 0.35),
        ]
    except Exception:
        tones = [None] * 5
        reply = [None] * 5

    schedule = [
        (5.5, tones[0]), (6.2, tones[1]), (6.9, tones[2]),
        (7.8, tones[3]), (8.7, tones[4]),
        (10.6, reply[4]), (11.1, reply[3]), (11.6, reply[2]),
        (12.1, reply[1]), (12.6, reply[0]),
    ]
    note_i = 0

    # Stars in native coords (sparse, twinkly)
    stars = [(random.randint(0, NATIVE_WIDTH - 1),
              random.randint(0, NATIVE_HEIGHT * 2 // 3),
              random.random() * 6.283) for _ in range(45)]

    base_y = int(NATIVE_HEIGHT * 0.78)
    tower_cx = NATIVE_WIDTH // 2
    tower_w = 36
    tower_h = 60
    tower_poly = [
        (tower_cx - tower_w // 2, base_y),
        (tower_cx - tower_w // 2 + 4, base_y - tower_h + 10),
        (tower_cx - tower_w // 2 + 9, base_y - tower_h + 3),
        (tower_cx - tower_w // 2 + 13, base_y - tower_h),
        (tower_cx + tower_w // 2 - 13, base_y - tower_h),
        (tower_cx + tower_w // 2 - 9, base_y - tower_h + 3),
        (tower_cx + tower_w // 2 - 4, base_y - tower_h + 10),
        (tower_cx + tower_w // 2, base_y),
    ]
    hills = [(0, base_y + 8)]
    for x in range(0, NATIVE_WIDTH + 4, 5):
        y = base_y + int(5 * math.sin(x / 13.0) + 3 * math.cos(x / 8.0))
        hills.append((x, y))
    hills.append((NATIVE_WIDTH, base_y + 8))
    hills.append((NATIVE_WIDTH, NATIVE_HEIGHT))
    hills.append((0, NATIVE_HEIGHT))

    start_ms = pygame.time.get_ticks()
    frame_count = 0

    while True:
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_q, pygame.K_RETURN, pygame.K_SPACE
            ):
                pygame.mixer.stop()
                return

        elapsed = (pygame.time.get_ticks() - start_ms) / 1000.0
        if elapsed >= 15.0:
            break

        while note_i < len(schedule) and elapsed >= schedule[note_i][0]:
            play_sound(schedule[note_i][1])
            note_i += 1

        game_surface.fill(BLACK)

        # Stars
        for sx, sy, phase in stars:
            tw = 0.5 + 0.5 * math.sin(elapsed * 2.6 + phase)
            if tw > 0.25:
                br = int(180 * tw)
                game_surface.set_at((sx, sy), (br, br, min(255, br + 30)))

        # Horizon glow
        glow_int = min(1.0, elapsed / 7.0)
        for i in range(6):
            c = int(40 * glow_int * (1 - i / 6))
            if c > 0:
                pygame.draw.line(
                    game_surface,
                    (c // 3, c // 2, c),
                    (0, base_y - tower_h - 4 - i),
                    (NATIVE_WIDTH, base_y - tower_h - 4 - i),
                )

        # Approaching light (chunky pixel blob that grows)
        if 1.8 <= elapsed < 9.0:
            t = (elapsed - 1.8) / 7.2
            lx = tower_cx + int(math.sin(elapsed * 1.3) * 12 * (1 - t))
            ly = int(18 + t * (base_y - tower_h - 26))
            r = 1 + int(t * 3)
            for dy in range(-r - 1, r + 2):
                for dx in range(-r - 1, r + 2):
                    d = math.hypot(dx, dy)
                    if d <= r + 1:
                        br = max(0, int(220 * (1 - d / (r + 1))))
                        px, py = lx + dx, ly + dy
                        if 0 <= px < NATIVE_WIDTH and 0 <= py < NATIVE_HEIGHT:
                            game_surface.set_at((px, py), (br, br, min(255, br + 30)))

        # Mothership
        if elapsed >= 8.5:
            t = min(1.0, (elapsed - 8.5) / 3.2)
            ship_x = tower_cx
            ship_y = int(22 + t * (base_y - tower_h - 36))
            ship_w = int(14 + t * 56)
            ship_h = int(3 + t * 8)

            pygame.draw.ellipse(
                game_surface, ATARI_BLUE,
                (ship_x - ship_w // 2, ship_y - ship_h // 2, ship_w, ship_h),
            )
            pygame.draw.ellipse(
                game_surface, (30, 60, 130),
                (ship_x - ship_w // 2, ship_y, ship_w, max(1, ship_h // 2)),
            )

            # Rim lights (blinking through Atari palette)
            n = max(3, ship_w // 5)
            pal = [ATARI_YELLOW, ATARI_WHITE, ATARI_ORANGE, ATARI_RED]
            for i in range(n):
                frac = i / max(1, n - 1)
                ang = math.pi * frac
                lx = ship_x + int(math.cos(ang) * (ship_w // 2 - 1))
                ly = ship_y + int(math.sin(ang) * (ship_h // 2)) - 1
                c = pal[(frame_count // 4 + i) % 4]
                if 0 <= lx < NATIVE_WIDTH and 0 <= ly < NATIVE_HEIGHT:
                    game_surface.set_at((lx, ly), c)

            # Central beacon
            if (frame_count // 6) % 2 == 0:
                game_surface.set_at((ship_x, ship_y), ATARI_YELLOW)
                if ship_w > 30:
                    game_surface.set_at((ship_x - 1, ship_y), ATARI_ORANGE)
                    game_surface.set_at((ship_x + 1, ship_y), ATARI_ORANGE)

            # Beam down (flickery white)
            if elapsed >= 10.5:
                beam_t = min(1.0, (elapsed - 10.5) / 1.5)
                beam_top = ship_y + ship_h // 2
                for by in range(beam_top, base_y):
                    prog = (by - beam_top) / max(1, base_y - beam_top)
                    half = int(1 + prog * 12 * beam_t)
                    for bx in range(ship_x - half, ship_x + half + 1):
                        if 0 <= bx < NATIVE_WIDTH and 0 <= by < NATIVE_HEIGHT:
                            if random.random() > 0.15:
                                br = int(220 * beam_t * (1 - prog * 0.6))
                                game_surface.set_at((bx, by), (br, br, max(60, br // 2)))

        # Mountains + tower silhouette (ON TOP of ship/beam to look like it's behind)
        pygame.draw.polygon(game_surface, (12, 14, 24), hills)
        pygame.draw.polygon(game_surface, (8, 10, 16), tower_poly)

        # Tiny silhouetted figures at base of tower
        if elapsed >= 11.8:
            for fx in [tower_cx - 26, tower_cx - 17, tower_cx + 17, tower_cx + 26]:
                fy = base_y - 2
                for dy in range(-5, 1):
                    for dx in range(-1, 2):
                        px, py = fx + dx, fy + dy
                        if 0 <= px < NATIVE_WIDTH and 0 <= py < NATIVE_HEIGHT:
                            game_surface.set_at((px, py), BLACK)
                if 0 <= fx < NATIVE_WIDTH and 0 <= fy - 7 < NATIVE_HEIGHT:
                    game_surface.set_at((fx, fy - 7), BLACK)

        # Final title card
        if elapsed >= 13.3:
            if (frame_count // 8) % 2 == 0 or elapsed >= 13.6:
                draw_text_centered(game_surface, "WE COME IN PEACE", 96, ATARI_WHITE)
                draw_text_centered(game_surface, "THIRD KIND", 110, ATARI_ORANGE)

        # Pipe through CRT effects so it keeps the 1977 TV look
        screen.fill(BLACK)
        apply_crt_effects(game_surface, screen, frame_count)
        pygame.display.flip()
        clock.tick(60)

    pygame.mixer.stop()


# === Title screen ===
def show_title(high_score):
    """Title screen. ENTER / SPACE to start, F3 for easter egg, Q to quit."""
    frame_count = 0
    # Pre-pick stable star positions so they don't dance every frame
    random.seed(1977)
    stars = [(random.randint(0, NATIVE_WIDTH - 1),
              random.randint(0, NATIVE_HEIGHT - 40)) for _ in range(35)]
    random.seed()

    while True:
        frame_count += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_F3:
                    play_close_encounters()
                    frame_count = 0
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    return

        game_surface.fill(BLACK)

        # Twinkly stars
        for sx, sy in stars:
            if (frame_count // 8 + sx + sy) % 11 != 0:
                game_surface.set_at((sx, sy), ATARI_WHITE)

        draw_text_centered(game_surface, "SPACE INVADERS", 40, ATARI_GREEN)
        draw_text_centered(game_surface, "ATARI 2600", 56, ATARI_ORANGE)

        hi_str = f"HI {high_score:04d}"
        draw_text_centered(game_surface, hi_str, 85, ATARI_YELLOW)

        if (frame_count // 20) % 2 == 0:
            draw_text_centered(game_surface, "PRESS ENTER", 120, ATARI_WHITE)

        draw_text_centered(game_surface, "ARROWS  SPACE FIRE", 148, ATARI_WHITE)
        draw_text_centered(game_surface, "R RESTART  Q QUIT", 158, ATARI_WHITE)

        # Subtle easter-egg hint
        if (frame_count // 45) % 3 != 0:
            draw_text_centered(game_surface, "LOOK UP.  F3", 185, (90, 90, 110))

        screen.fill(BLACK)
        apply_crt_effects(game_surface, screen, frame_count)
        pygame.display.flip()
        clock.tick(60)


# === Core game loop (previously main()) ===
def run_game(high_score):
    global screen_shake, screen_shake_intensity, particles, flash_screen

    player = Player()
    invaders = create_invaders()
    shields = create_shields()
    bullets = []
    enemy_bullets = []
    ufo = UFO()

    score = 0
    lives = 3
    level = 1

    invader_direction = 1
    invader_move_timer = 0
    invader_move_delay = 45
    invader_anim_frame = 0
    invader_sound_index = 0

    shoot_cooldown = 0
    enemy_shoot_timer = 0

    game_state = "playing"
    state_timer = 0
    frame_count = 0

    particles = []
    flash_screen = 0
    screen_shake = 0

    while True:
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_high_score(max(high_score, score))
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    # Return to title
                    return max(high_score, score)
                if event.key == pygame.K_F3 and game_state == "game_over":
                    play_close_encounters()
                if event.key == pygame.K_r:
                    # In-place reset, keep high score
                    high_score = max(high_score, score)
                    player = Player()
                    invaders = create_invaders()
                    shields = create_shields()
                    bullets = []
                    enemy_bullets = []
                    ufo = UFO()
                    score = 0
                    lives = 3
                    level = 1
                    invader_direction = 1
                    invader_move_timer = 0
                    invader_move_delay = 45
                    game_state = "playing"
                    state_timer = 0
                    particles = []
                    flash_screen = 0

        # ---- Update ----
        if game_state == "playing":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player.move("left")
            if keys[pygame.K_RIGHT]:
                player.move("right")
            if keys[pygame.K_SPACE] and shoot_cooldown == 0 and len(bullets) < 1:
                if player.respawn_timer == 0:
                    bullets.append(Bullet(player.x + player.width // 2, player.y))
                    shoot_cooldown = 30
                    play_sound(shoot_sound)

            if shoot_cooldown > 0:
                shoot_cooldown -= 1

            player.update()

            for bullet in bullets[:]:
                bullet.move()
                if bullet.y < 20:
                    bullets.remove(bullet)

            for bullet in enemy_bullets[:]:
                bullet.move()
                if bullet.y > NATIVE_HEIGHT:
                    enemy_bullets.remove(bullet)

            invader_move_timer += 1
            if invader_move_timer >= invader_move_delay and invaders:
                invader_move_timer = 0
                invader_anim_frame = 1 - invader_anim_frame

                for inv in invaders:
                    inv.frame = invader_anim_frame

                move_down = False
                for invader in invaders:
                    if invader.x + invader.width >= NATIVE_WIDTH - 8 and invader_direction == 1:
                        invader_direction = -1
                        move_down = True
                        break
                    if invader.x <= 8 and invader_direction == -1:
                        invader_direction = 1
                        move_down = True
                        break

                for invader in invaders:
                    if move_down:
                        invader.y += 8
                    else:
                        invader.x += 2 * invader_direction

                play_sound(invader_move_sounds[invader_sound_index])
                invader_sound_index = (invader_sound_index + 1) % 4

            ufo.spawn()
            ufo.update()

            enemy_shoot_timer += 1
            if enemy_shoot_timer >= 90 and invaders and len(enemy_bullets) < 1:
                columns = {}
                for inv in invaders:
                    col = int(inv.x // 16)
                    if col not in columns or inv.y > columns[col].y:
                        columns[col] = inv
                if columns:
                    shooter = random.choice(list(columns.values()))
                    enemy_bullets.append(EnemyBullet(shooter.x + 4, shooter.y + 6))
                    enemy_shoot_timer = 0

            # Collisions
            for bullet in bullets[:]:
                for invader in invaders[:]:
                    if (bullet.x >= invader.x and bullet.x <= invader.x + invader.width and
                        bullet.y >= invader.y and bullet.y <= invader.y + invader.height):
                        if bullet in bullets:
                            bullets.remove(bullet)
                        invaders.remove(invader)
                        score += 30 if invader.row < 2 else (20 if invader.row < 4 else 10)
                        if score > high_score:
                            high_score = score
                        spawn_particles(invader.x + 4, invader.y + 3, ATARI_WHITE, 15)
                        screen_shake = 4
                        screen_shake_intensity = 2
                        flash_screen = 3
                        play_sound(explosion_sound)
                        invader_move_delay = max(5, 45 - (36 - len(invaders)))
                        break

                if ufo.active and bullet in bullets:
                    if (bullet.x >= ufo.x and bullet.x <= ufo.x + ufo.width and
                        bullet.y >= ufo.y and bullet.y <= ufo.y + ufo.height):
                        bullets.remove(bullet)
                        score += ufo.get_score()
                        if score > high_score:
                            high_score = score
                        spawn_particles(ufo.x + 5, ufo.y + 2, ATARI_ORANGE, 25)
                        screen_shake = 6
                        screen_shake_intensity = 3
                        flash_screen = 5
                        play_sound(explosion_sound)
                        ufo.active = False

                if bullet in bullets:
                    for shield in shields:
                        if shield.check_collision(bullet.x, bullet.y):
                            shield.damage(bullet.x, bullet.y)
                            bullets.remove(bullet)
                            break

            for bullet in enemy_bullets[:]:
                for shield in shields:
                    if shield.check_collision(bullet.x, bullet.y + 4):
                        shield.damage(bullet.x, bullet.y + 4)
                        if bullet in enemy_bullets:
                            enemy_bullets.remove(bullet)
                        break

                if bullet in enemy_bullets and player.respawn_timer == 0:
                    if (bullet.x >= player.x and bullet.x <= player.x + player.width and
                        bullet.y + 4 >= player.y and bullet.y <= player.y + player.height):
                        enemy_bullets.remove(bullet)
                        lives -= 1
                        spawn_particles(player.x + 4, player.y + 4, ATARI_GREEN, 30)
                        screen_shake = 10
                        screen_shake_intensity = 4
                        flash_screen = 8
                        play_sound(player_death_sound)

                        if lives <= 0:
                            player.alive = False
                            game_state = "dying"
                            state_timer = 90
                        else:
                            player.respawn_timer = 60
                            player.x = NATIVE_WIDTH // 2 - player.width // 2

            for invader in invaders:
                if invader.y + invader.height >= player.y - 5:
                    player.alive = False
                    game_state = "dying"
                    state_timer = 90
                    spawn_particles(player.x + 4, player.y + 4, ATARI_GREEN, 30)
                    break

            if len(invaders) == 0:
                level += 1
                invaders = create_invaders()
                invader_move_delay = max(5, 45 - level * 5)
                invader_direction = 1
                enemy_bullets.clear()
                bullets.clear()
                flash_screen = 15

        elif game_state == "dying":
            state_timer -= 1
            if state_timer <= 0:
                game_state = "game_over"
                state_timer = 0
                save_high_score(high_score)

        elif game_state == "game_over":
            state_timer += 1

        # Particles always update
        for particle in particles[:]:
            particle.update()
            if particle.life <= 0:
                particles.remove(particle)

        if screen_shake > 0:
            screen_shake -= 1
        if flash_screen > 0:
            flash_screen -= 1

        # ---- Render ----
        game_surface.fill(BLACK)

        pygame.draw.line(game_surface, ATARI_GREEN,
                         (0, NATIVE_HEIGHT - 12), (NATIVE_WIDTH, NATIVE_HEIGHT - 12))

        for shield in shields:
            shield.draw(game_surface)

        for invader in invaders:
            invader.draw(game_surface)

        ufo.draw(game_surface)

        if game_state != "dying" or (state_timer // 5) % 2 == 0:
            player.draw(game_surface)

        for bullet in bullets:
            bullet.draw(game_surface)

        for bullet in enemy_bullets:
            bullet.draw(game_surface)

        for particle in particles:
            particle.draw(game_surface)

        draw_score(game_surface, score, lives, high_score)

        if game_state == "game_over":
            draw_game_over(game_surface, state_timer)

        if flash_screen > 0:
            flash_intensity = min(100, flash_screen * 15)
            flash_surf = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
            flash_surf.fill((flash_intensity, flash_intensity, flash_intensity))
            game_surface.blit(flash_surf, (0, 0), special_flags=pygame.BLEND_ADD)

        if screen_shake > 0:
            shake_x = random.randint(-screen_shake_intensity, screen_shake_intensity)
            shake_y = random.randint(-screen_shake_intensity, screen_shake_intensity)
            temp = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
            temp.blit(game_surface, (shake_x, shake_y))
            game_surface.blit(temp, (0, 0))

        screen.fill(BLACK)
        apply_crt_effects(game_surface, screen, frame_count)

        pygame.display.flip()
        clock.tick(60)


def main():
    high_score = load_high_score()
    while True:
        show_title(high_score)
        high_score = run_game(high_score)
        save_high_score(high_score)


if __name__ == "__main__":
    main()
