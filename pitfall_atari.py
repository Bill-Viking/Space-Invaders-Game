"""
Pitfall! - Atari 2600 Authentic Recreation
With period-appropriate CRT effects

Controls:
- Arrow keys to move (left/right to run, up to jump, down to climb)
- Spacebar to jump
- R to restart
- Q to quit
"""

import pygame
import random
import math
import sys

# Initialize pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Atari 2600 authentic resolution
NATIVE_WIDTH = 160
NATIVE_HEIGHT = 192
SCALE = 4
SCREEN_WIDTH = NATIVE_WIDTH * SCALE
SCREEN_HEIGHT = NATIVE_HEIGHT * SCALE

# Create surfaces
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
game_surface = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
pygame.display.set_caption("Pitfall! - Atari 2600")

clock = pygame.time.Clock()

# Atari 2600 color palette (authentic Pitfall colors)
BLACK = (0, 0, 0)
DARK_GREEN = (0, 100, 0)        # Background jungle
GREEN = (34, 139, 34)           # Trees/vines
BROWN = (139, 90, 43)           # Ground/logs
TAN = (210, 180, 140)           # Pitfall Harry skin
RED = (200, 50, 50)             # Harry's shirt
BLUE = (100, 149, 237)          # Water/underground
YELLOW = (255, 215, 0)          # Treasures
GRAY = (128, 128, 128)          # Walls
DARK_BROWN = (80, 50, 20)       # Pits
VINE_GREEN = (0, 128, 0)        # Vines
CROC_GREEN = (50, 120, 50)      # Crocodiles
SKY_BLUE = (135, 180, 220)      # Sky

# Game constants
GROUND_Y = 140
UNDERGROUND_Y = 170
GRAVITY = 0.5
JUMP_STRENGTH = -8
SWING_SPEED = 0.08

# Sound generation
def generate_sound(frequency, duration_ms, volume=0.3):
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytes([128 + int(127 * volume * (1 if (i * frequency // sample_rate) % 2 == 0 else -1))
                 for i in range(n_samples)])
    return pygame.mixer.Sound(buffer=buf)

# Create sounds
try:
    jump_sound = generate_sound(440, 100, 0.2)
    treasure_sound = generate_sound(880, 200, 0.25)
    death_sound = generate_sound(100, 400, 0.3)
    swing_sound = generate_sound(330, 150, 0.2)
    step_sounds = [generate_sound(80 + i*10, 50, 0.1) for i in range(4)]
except:
    jump_sound = None
    treasure_sound = None
    death_sound = None
    swing_sound = None
    step_sounds = [None] * 4

def play_sound(sound):
    if sound:
        try:
            sound.play()
        except:
            pass


class PitfallHarry:
    """The player character"""
    def __init__(self):
        self.x = 40
        self.y = GROUND_Y - 16
        self.width = 8
        self.height = 16
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.facing_right = True
        self.running = False
        self.frame = 0
        self.frame_timer = 0
        self.swinging = False
        self.swing_angle = 0
        self.vine_x = 0
        self.underground = False
        self.on_ladder = False
        self.alive = True
        self.step_timer = 0

    def update(self, keys, current_screen):
        if not self.alive:
            return

        if self.swinging:
            # Swinging on vine
            self.swing_angle += SWING_SPEED
            self.x = self.vine_x + math.sin(self.swing_angle) * 30
            self.y = 50 + abs(math.cos(self.swing_angle)) * 20

            # Let go of vine
            if keys[pygame.K_SPACE] or keys[pygame.K_DOWN]:
                self.swinging = False
                self.vy = -3
                self.vx = math.cos(self.swing_angle) * 4

            return

        if self.on_ladder:
            # Climbing ladder
            if keys[pygame.K_UP]:
                self.y -= 2
                if self.y < GROUND_Y - 16:
                    self.y = GROUND_Y - 16
                    self.underground = False
                    self.on_ladder = False
            elif keys[pygame.K_DOWN]:
                self.y += 2
                if self.y > UNDERGROUND_Y - 16:
                    self.y = UNDERGROUND_Y - 16
                    self.on_ladder = False

            if keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]:
                self.on_ladder = False
            return

        # Horizontal movement
        self.running = False
        if keys[pygame.K_LEFT]:
            self.vx = -2
            self.facing_right = False
            self.running = True
        elif keys[pygame.K_RIGHT]:
            self.vx = 2
            self.facing_right = True
            self.running = True
        else:
            self.vx = 0

        # Jumping
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP]) and self.on_ground:
            self.vy = JUMP_STRENGTH
            self.on_ground = False
            play_sound(jump_sound)

        # Apply gravity
        if not self.on_ground:
            self.vy += GRAVITY

        # Update position
        self.x += self.vx
        self.y += self.vy

        # Screen bounds
        if self.x < 5:
            self.x = 5
        if self.x > NATIVE_WIDTH - self.width - 5:
            self.x = NATIVE_WIDTH - self.width - 5

        # Ground collision
        ground = UNDERGROUND_Y - 16 if self.underground else GROUND_Y - 16
        if self.y >= ground:
            self.y = ground
            self.vy = 0
            self.on_ground = True

        # Animation
        if self.running and self.on_ground:
            self.frame_timer += 1
            if self.frame_timer >= 5:
                self.frame_timer = 0
                self.frame = (self.frame + 1) % 4
                self.step_timer += 1
                if self.step_timer >= 2:
                    self.step_timer = 0
                    play_sound(step_sounds[self.frame])
        elif not self.on_ground:
            self.frame = 2  # Jump frame
        else:
            self.frame = 0

    def draw(self, surface):
        if not self.alive:
            return

        x, y = int(self.x), int(self.y)

        # Flip sprite if facing left
        dx = 1 if self.facing_right else -1
        ox = 0 if self.facing_right else 7

        # Draw Pitfall Harry (simplified sprite)
        # Head (tan)
        pygame.draw.rect(surface, TAN, (x + 2, y, 4, 4))

        # Body (red shirt)
        pygame.draw.rect(surface, RED, (x + 1, y + 4, 6, 5))

        # Legs (tan) - animated
        if self.frame == 0 or self.frame == 2:
            pygame.draw.rect(surface, TAN, (x + 2, y + 9, 2, 4))
            pygame.draw.rect(surface, TAN, (x + 4, y + 9, 2, 4))
        elif self.frame == 1:
            pygame.draw.rect(surface, TAN, (x + 1, y + 9, 2, 4))
            pygame.draw.rect(surface, TAN, (x + 5, y + 9, 2, 4))
        else:
            pygame.draw.rect(surface, TAN, (x + 3, y + 9, 2, 4))
            pygame.draw.rect(surface, TAN, (x + 3, y + 11, 2, 2))

        # Arms
        if self.swinging:
            pygame.draw.rect(surface, TAN, (x + 3, y + 2, 2, 3))
        else:
            pygame.draw.rect(surface, TAN, (x, y + 5, 2, 3))
            pygame.draw.rect(surface, TAN, (x + 6, y + 5, 2, 3))

    def grab_vine(self, vine_x):
        self.swinging = True
        self.vine_x = vine_x
        self.swing_angle = -math.pi / 2
        play_sound(swing_sound)


class Screen:
    """One screen of the game"""
    def __init__(self, screen_num):
        self.screen_num = screen_num
        random.seed(screen_num)  # Deterministic screens

        # Screen features
        self.has_pit = random.random() < 0.3
        self.has_water = random.random() < 0.25 and not self.has_pit
        self.has_logs = random.random() < 0.4
        self.has_vine = random.random() < 0.35
        self.has_crocs = self.has_water and random.random() < 0.5
        self.has_ladder = random.random() < 0.3

        # Pit position
        self.pit_x = random.randint(50, 100)
        self.pit_width = random.randint(20, 35)

        # Water/croc position
        self.water_x = 40
        self.water_width = 80

        # Log positions (for rolling logs)
        self.logs = []
        if self.has_logs:
            for i in range(random.randint(1, 2)):
                self.logs.append({
                    'x': random.randint(20, 140),
                    'y': GROUND_Y - 8,
                    'vx': random.choice([-1.5, 1.5]),
                    'width': 12,
                    'height': 6
                })

        # Vine position
        self.vine_x = random.randint(60, 100)

        # Ladder position
        self.ladder_x = random.randint(30, 120)

        # Treasures
        self.treasures = []
        if random.random() < 0.4:
            tx = random.randint(20, 130)
            self.treasures.append({
                'x': tx,
                'y': GROUND_Y - 12,
                'collected': False,
                'type': random.choice(['gold', 'silver', 'ring', 'money'])
            })

        # Scorpions/obstacles underground
        self.scorpion_x = random.randint(30, 120)
        self.scorpion_dir = 1

        random.seed()  # Reset random

    def update(self):
        # Update rolling logs
        for log in self.logs:
            log['x'] += log['vx']
            if log['x'] < 10 or log['x'] > NATIVE_WIDTH - 20:
                log['vx'] *= -1

        # Update scorpion
        self.scorpion_x += self.scorpion_dir * 0.5
        if self.scorpion_x < 20 or self.scorpion_x > 130:
            self.scorpion_dir *= -1

    def draw(self, surface, harry):
        # Sky
        pygame.draw.rect(surface, SKY_BLUE, (0, 0, NATIVE_WIDTH, 60))

        # Jungle canopy
        for i in range(0, NATIVE_WIDTH, 20):
            pygame.draw.ellipse(surface, DARK_GREEN, (i - 5, 10, 30, 25))
        for i in range(10, NATIVE_WIDTH, 20):
            pygame.draw.ellipse(surface, GREEN, (i - 5, 15, 25, 20))

        # Tree trunks
        pygame.draw.rect(surface, BROWN, (10, 35, 8, 105))
        pygame.draw.rect(surface, BROWN, (NATIVE_WIDTH - 18, 35, 8, 105))

        # Vine
        if self.has_vine:
            vine_bottom = 90 if not harry.swinging else int(harry.y)
            pygame.draw.line(surface, VINE_GREEN, (self.vine_x, 20), (self.vine_x, vine_bottom), 2)
            # Vine handle
            pygame.draw.rect(surface, VINE_GREEN, (self.vine_x - 3, vine_bottom - 5, 6, 5))

        # Ground
        ground_color = DARK_GREEN
        pygame.draw.rect(surface, ground_color, (0, GROUND_Y, NATIVE_WIDTH, 20))
        pygame.draw.rect(surface, BROWN, (0, GROUND_Y, NATIVE_WIDTH, 3))

        # Pit
        if self.has_pit:
            pygame.draw.rect(surface, BLACK, (self.pit_x, GROUND_Y, self.pit_width, 20))
            pygame.draw.rect(surface, DARK_BROWN, (self.pit_x, GROUND_Y + 15, self.pit_width, 5))

        # Water with crocodiles
        if self.has_water:
            pygame.draw.rect(surface, BLUE, (self.water_x, GROUND_Y + 3, self.water_width, 14))
            # Croc heads
            if self.has_crocs:
                for i in range(3):
                    cx = self.water_x + 15 + i * 25
                    # Croc head (can jump on when mouth closed)
                    pygame.draw.rect(surface, CROC_GREEN, (cx, GROUND_Y + 2, 12, 6))
                    pygame.draw.rect(surface, CROC_GREEN, (cx + 8, GROUND_Y + 5, 6, 4))
                    # Eyes
                    pygame.draw.rect(surface, YELLOW, (cx + 2, GROUND_Y + 3, 2, 2))
                    pygame.draw.rect(surface, YELLOW, (cx + 6, GROUND_Y + 3, 2, 2))

        # Rolling logs
        for log in self.logs:
            pygame.draw.ellipse(surface, BROWN, (int(log['x']), int(log['y']), log['width'], log['height']))
            pygame.draw.ellipse(surface, TAN, (int(log['x']) + 2, int(log['y']) + 1, log['width'] - 4, log['height'] - 2))

        # Ladder
        if self.has_ladder:
            pygame.draw.rect(surface, BROWN, (self.ladder_x, GROUND_Y, 3, 35))
            pygame.draw.rect(surface, BROWN, (self.ladder_x + 9, GROUND_Y, 3, 35))
            for i in range(5):
                pygame.draw.rect(surface, BROWN, (self.ladder_x, GROUND_Y + 5 + i * 7, 12, 2))

        # Underground passage
        pygame.draw.rect(surface, DARK_BROWN, (0, GROUND_Y + 20, NATIVE_WIDTH, 40))
        pygame.draw.rect(surface, BLACK, (0, GROUND_Y + 22, NATIVE_WIDTH, 36))
        pygame.draw.rect(surface, GRAY, (0, UNDERGROUND_Y, NATIVE_WIDTH, 3))

        # Underground walls
        pygame.draw.rect(surface, GRAY, (0, GROUND_Y + 20, 5, 40))
        pygame.draw.rect(surface, GRAY, (NATIVE_WIDTH - 5, GROUND_Y + 20, 5, 40))

        # Scorpion in underground
        if harry.underground:
            sx = int(self.scorpion_x)
            pygame.draw.rect(surface, RED, (sx, UNDERGROUND_Y - 6, 8, 4))
            pygame.draw.rect(surface, RED, (sx + 6, UNDERGROUND_Y - 10, 2, 6))  # Tail

        # Treasures
        for t in self.treasures:
            if not t['collected']:
                if t['type'] == 'gold':
                    pygame.draw.rect(surface, YELLOW, (t['x'], t['y'], 8, 8))
                elif t['type'] == 'silver':
                    pygame.draw.rect(surface, GRAY, (t['x'], t['y'], 8, 8))
                elif t['type'] == 'ring':
                    pygame.draw.ellipse(surface, YELLOW, (t['x'], t['y'], 8, 8))
                else:
                    pygame.draw.rect(surface, GREEN, (t['x'], t['y'], 10, 6))

    def check_collisions(self, harry):
        """Check for collisions with hazards and treasures"""
        if not harry.alive:
            return 0

        score = 0
        hx, hy = harry.x, harry.y
        hw, hh = harry.width, harry.height

        # Pit collision
        if self.has_pit and not harry.swinging:
            if (hx + hw > self.pit_x and hx < self.pit_x + self.pit_width and
                hy + hh >= GROUND_Y and not harry.underground):
                harry.alive = False
                play_sound(death_sound)
                return -100

        # Water collision (if no crocs to jump on)
        if self.has_water and not self.has_crocs and not harry.swinging:
            if (hx + hw > self.water_x and hx < self.water_x + self.water_width and
                hy + hh >= GROUND_Y and not harry.underground):
                harry.alive = False
                play_sound(death_sound)
                return -100

        # Log collision
        for log in self.logs:
            if (hx < log['x'] + log['width'] and hx + hw > log['x'] and
                hy + hh > log['y'] and hy < log['y'] + log['height']):
                harry.alive = False
                play_sound(death_sound)
                return -100

        # Scorpion collision (underground)
        if harry.underground:
            if (hx < self.scorpion_x + 8 and hx + hw > self.scorpion_x and
                hy + hh > UNDERGROUND_Y - 6):
                harry.alive = False
                play_sound(death_sound)
                return -100

        # Vine grab
        if self.has_vine and not harry.swinging and not harry.on_ground:
            if abs(hx - self.vine_x) < 10 and hy < 80:
                harry.grab_vine(self.vine_x)

        # Ladder
        if self.has_ladder:
            if (hx + hw > self.ladder_x and hx < self.ladder_x + 12):
                if pygame.key.get_pressed()[pygame.K_DOWN] and harry.on_ground and not harry.underground:
                    harry.on_ladder = True
                    harry.underground = True
                    harry.x = self.ladder_x + 2
                elif pygame.key.get_pressed()[pygame.K_UP] and harry.underground:
                    harry.on_ladder = True

        # Treasure collection
        for t in self.treasures:
            if not t['collected']:
                if (hx < t['x'] + 8 and hx + hw > t['x'] and
                    hy < t['y'] + 8 and hy + hh > t['y']):
                    t['collected'] = True
                    play_sound(treasure_sound)
                    if t['type'] == 'gold':
                        score = 5000
                    elif t['type'] == 'silver':
                        score = 3000
                    elif t['type'] == 'ring':
                        score = 4000
                    else:
                        score = 2000

        return score


def apply_crt_effects(surface, target_surface, frame_count):
    """Apply CRT effects"""
    scaled = pygame.transform.scale(surface, (SCREEN_WIDTH, SCREEN_HEIGHT))

    final = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    final.blit(scaled, (0, 0))

    # Scanlines
    for y in range(0, SCREEN_HEIGHT, 2):
        pygame.draw.line(final, (0, 0, 0), (0, y), (SCREEN_WIDTH, y))

    # Slight wobble
    wobble = int(math.sin(frame_count * 0.03) * 1)

    # Vignette
    vignette = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    for i in range(25):
        alpha = int(3 * (25 - i) / 25)
        pygame.draw.rect(vignette, (0, 0, 0, alpha),
                        (i*2, i*2, SCREEN_WIDTH - i*4, SCREEN_HEIGHT - i*4), 2)
    final.blit(vignette, (0, 0))

    target_surface.blit(final, (wobble, 0))


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


def draw_hud(surface, score, time_left, lives):
    # Score
    score_str = str(score).zfill(6)
    for i, digit in enumerate(score_str):
        draw_digit(int(digit), 5 + i * 5, 3, YELLOW, surface)

    # Timer
    minutes = time_left // 60
    seconds = time_left % 60
    time_str = f"{minutes:02d}{seconds:02d}"
    for i, digit in enumerate(time_str):
        draw_digit(int(digit), NATIVE_WIDTH - 25 + i * 5, 3, YELLOW, surface)

    # Colon for time
    surface.set_at((NATIVE_WIDTH - 13, 4), YELLOW)
    surface.set_at((NATIVE_WIDTH - 13, 6), YELLOW)

    # Lives
    for i in range(lives):
        pygame.draw.rect(surface, RED, (70 + i * 10, 3, 6, 6))


def main():
    harry = PitfallHarry()
    current_screen_num = 0
    current_screen = Screen(current_screen_num)

    score = 2000  # Start with 2000 like original
    lives = 3
    time_left = 20 * 60  # 20 minutes in seconds

    frame_count = 0
    time_ticker = 0

    game_state = "playing"
    death_timer = 0

    running = True
    while running:
        frame_count += 1

        # Timer countdown
        time_ticker += 1
        if time_ticker >= 60 and game_state == "playing":
            time_ticker = 0
            time_left -= 1
            if time_left <= 0:
                game_state = "game_over"

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                if event.key == pygame.K_r:
                    # Restart
                    harry = PitfallHarry()
                    current_screen_num = 0
                    current_screen = Screen(current_screen_num)
                    score = 2000
                    lives = 3
                    time_left = 20 * 60
                    game_state = "playing"
                    death_timer = 0

        keys = pygame.key.get_pressed()

        if game_state == "playing":
            # Update
            harry.update(keys, current_screen)
            current_screen.update()

            # Check collisions
            points = current_screen.check_collisions(harry)
            if points < 0:
                # Death
                lives -= 1
                if lives <= 0:
                    game_state = "game_over"
                else:
                    game_state = "dying"
                    death_timer = 60
            else:
                score += points

            # Screen transitions
            if harry.x <= 5 and harry.vx < 0:
                current_screen_num -= 1
                current_screen = Screen(current_screen_num)
                harry.x = NATIVE_WIDTH - harry.width - 10
                harry.underground = False
            elif harry.x >= NATIVE_WIDTH - harry.width - 5 and harry.vx > 0:
                current_screen_num += 1
                current_screen = Screen(current_screen_num)
                harry.x = 10
                harry.underground = False

            # Bonus for moving forward
            if harry.vx > 0 and harry.on_ground:
                score += 1

        elif game_state == "dying":
            death_timer -= 1
            if death_timer <= 0:
                harry = PitfallHarry()
                harry.x = 40
                game_state = "playing"

        # === RENDERING ===
        game_surface.fill(BLACK)

        current_screen.draw(game_surface, harry)

        if game_state != "dying" or (death_timer // 5) % 2 == 0:
            harry.draw(game_surface)

        draw_hud(game_surface, score, time_left, lives)

        # Game over text
        if game_state == "game_over":
            if (frame_count // 15) % 2 == 0:
                cx = NATIVE_WIDTH // 2
                pygame.draw.rect(game_surface, BLACK, (cx - 35, 85, 70, 25))
                pygame.draw.rect(game_surface, RED, (cx - 33, 87, 66, 21))
                # Simple "GAME OVER"
                for i, px in enumerate(range(cx - 28, cx + 28, 5)):
                    pygame.draw.rect(game_surface, BLACK, (px, 93, 3, 5))

        # Apply CRT effects
        screen.fill(BLACK)
        apply_crt_effects(game_surface, screen, frame_count)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
