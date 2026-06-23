"""
Space Invaders — single-file Mac-friendly build.

To run on a Mac:
  1. Install Python 3 (comes with recent macOS, or download from python.org).
  2. Open Terminal and install pygame:
         pip3 install pygame
  3. Save this file somewhere (e.g. Desktop) and run:
         python3 space_invaders.py

Controls:
  Left / Right arrows ... move
  Spacebar ............. shoot
  P .................... pause
  R .................... restart (on game over / victory)
  Q or Esc ............. quit
  (There is an easter egg hidden on the title and game-over screens.)
"""

import array
import math
import os
import random
import sys

import pygame

# ---------- Display & fonts ----------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
CYAN = (120, 220, 255)

# ---------- Audio (optional) ----------
AUDIO_OK = True
try:
    pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.init()
    pygame.mixer.init()
except pygame.error:
    AUDIO_OK = False
    pygame.init()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Invaders")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)
large_font = pygame.font.Font(None, 72)

# ---------- Persistent high score ----------
HIGH_SCORE_PATH = os.path.join(os.path.expanduser("~"), ".space_invaders_highscore")


def load_high_score():
    try:
        with open(HIGH_SCORE_PATH, "r") as f:
            return int(f.read().strip() or "0")
    except Exception:
        return 0


def save_high_score(score):
    try:
        with open(HIGH_SCORE_PATH, "w") as f:
            f.write(str(int(score)))
    except Exception:
        pass


# ---------- Tone synthesis (for the easter egg) ----------
def make_tone(freq, duration_ms, volume=0.35, fade_ms=60):
    """Build a short stereo sine tone with a soft envelope."""
    if not AUDIO_OK:
        return None
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000)
    fade_samples = max(1, int(sample_rate * fade_ms / 1000))
    buf = array.array("h")
    for i in range(n_samples):
        t = i / sample_rate
        amp = volume
        if i < fade_samples:
            amp *= i / fade_samples
        elif i > n_samples - fade_samples:
            amp *= max(0.0, (n_samples - i) / fade_samples)
        val = amp * (
            math.sin(2 * math.pi * freq * t)
            + 0.25 * math.sin(4 * math.pi * freq * t)
        )
        s = int(max(-1.0, min(1.0, val)) * 32767)
        buf.append(s)
        buf.append(s)
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return None


# ---------- Game objects ----------
class Player:
    def __init__(self):
        self.width = 50
        self.height = 30
        self.x = SCREEN_WIDTH // 2 - self.width // 2
        self.y = SCREEN_HEIGHT - 60
        self.speed = 5
        self.color = GREEN

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y + 10, self.width, 20))
        pygame.draw.polygon(
            screen,
            self.color,
            [
                (self.x + self.width // 2, self.y),
                (self.x + 10, self.y + 10),
                (self.x + self.width - 10, self.y + 10),
            ],
        )

    def move(self, direction):
        if direction == "left" and self.x > 0:
            self.x -= self.speed
        if direction == "right" and self.x < SCREEN_WIDTH - self.width:
            self.x += self.speed


class Bullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 4
        self.height = 15
        self.speed = 7
        self.color = YELLOW

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

    def move(self):
        self.y -= self.speed


class Invader:
    def __init__(self, x, y):
        self.width = 40
        self.height = 30
        self.x = x
        self.y = y
        self.color = RED

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x + 5, self.y + 10, self.width - 10, 15))
        pygame.draw.rect(screen, self.color, (self.x, self.y + 5, self.width, 10))
        pygame.draw.rect(screen, WHITE, (self.x + 8, self.y + 8, 6, 6))
        pygame.draw.rect(screen, WHITE, (self.x + self.width - 14, self.y + 8, 6, 6))
        pygame.draw.line(screen, self.color, (self.x + 10, self.y + 5), (self.x + 5, self.y), 2)
        pygame.draw.line(
            screen,
            self.color,
            (self.x + self.width - 10, self.y + 5),
            (self.x + self.width - 5, self.y),
            2,
        )


class EnemyBullet:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 4
        self.height = 15
        self.speed = 4
        self.color = RED

    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

    def move(self):
        self.y += self.speed


def create_invaders():
    invaders = []
    for row in range(4):
        for col in range(10):
            x = 80 + col * 60
            y = 50 + row * 50
            invaders.append(Invader(x, y))
    return invaders


def rects_overlap(a, b):
    return (
        a.x < b.x + b.width
        and a.x + a.width > b.x
        and a.y < b.y + b.height
        and a.y + a.height > b.y
    )


# ---------- Easter egg: 15-second Close Encounters homage ----------
def play_close_encounters():
    """A 15-second cinematic tribute to the 1977 UFO classic.

    Elements: starfield, a Devils-Tower silhouette, a distant approaching
    light, the five-tone motif, the great mothership descending with a
    halo of blinking lights, a beam of white light, small silhouetted
    figures, and a final title card.
    """
    if AUDIO_OK:
        pygame.mixer.stop()

    # The five-note motif: re, mi, do, do (octave lower), sol
    # D4, E4, C4, C3, G4
    freqs = [293.66, 329.63, 261.63, 130.81, 392.00]
    tones = [make_tone(f, 650, volume=0.35) for f in freqs]
    # A lower, warmer "reply" set for the mothership
    reply = [make_tone(f * 0.75, 800, volume=0.4) for f in freqs]

    # Starfield (x, y, twinkle phase, brightness)
    stars = []
    for _ in range(180):
        stars.append(
            (
                random.randint(0, SCREEN_WIDTH),
                random.randint(0, int(SCREEN_HEIGHT * 0.65)),
                random.random() * 6.283,
                random.randint(90, 200),
            )
        )

    # Mountain silhouette with a central Devils-Tower shape
    base_y = int(SCREEN_HEIGHT * 0.78)
    tower_cx = SCREEN_WIDTH // 2
    tower_w = 200
    tower_h = 230
    tower_poly = [
        (tower_cx - tower_w // 2, base_y),
        (tower_cx - tower_w // 2 + 22, base_y - tower_h + 40),
        (tower_cx - tower_w // 2 + 40, base_y - tower_h + 10),
        (tower_cx - tower_w // 2 + 60, base_y - tower_h),
        (tower_cx + tower_w // 2 - 60, base_y - tower_h),
        (tower_cx + tower_w // 2 - 40, base_y - tower_h + 10),
        (tower_cx + tower_w // 2 - 22, base_y - tower_h + 40),
        (tower_cx + tower_w // 2, base_y),
    ]
    # Surrounding hills
    hills = [(0, base_y + 50)]
    for x in range(0, SCREEN_WIDTH + 20, 24):
        y = base_y + int(26 * math.sin(x / 110.0) + 18 * math.cos(x / 47.0))
        hills.append((x, y))
    hills.append((SCREEN_WIDTH, base_y + 50))
    hills.append((SCREEN_WIDTH, SCREEN_HEIGHT))
    hills.append((0, SCREEN_HEIGHT))

    # Note schedule (seconds from start)
    note_schedule = [
        (5.5, tones[0]),
        (6.2, tones[1]),
        (6.9, tones[2]),
        (7.8, tones[3]),
        (8.7, tones[4]),
        # mothership answers
        (10.6, reply[4]),
        (11.1, reply[3]),
        (11.6, reply[2]),
        (12.1, reply[1]),
        (12.6, reply[0]),
    ]
    note_i = 0

    start_ms = pygame.time.get_ticks()
    local_clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                if AUDIO_OK:
                    pygame.mixer.stop()
                return

        elapsed = (pygame.time.get_ticks() - start_ms) / 1000.0
        if elapsed >= 15.0:
            break

        # Trigger notes on schedule
        while note_i < len(note_schedule) and elapsed >= note_schedule[note_i][0]:
            s = note_schedule[note_i][1]
            if s is not None:
                try:
                    s.play()
                except Exception:
                    pass
            note_i += 1

        # ---- background: deep twilight blue with a soft horizon glow ----
        screen.fill((3, 5, 14))

        horizon_glow = min(1.0, elapsed / 7.0)
        # Layered horizon band
        for i in range(90):
            k = 1 - i / 90
            r = int(12 + 40 * horizon_glow * k)
            g = int(18 + 55 * horizon_glow * k)
            b = int(40 + 90 * horizon_glow * k)
            pygame.draw.line(screen, (r, g, b), (0, base_y - tower_h - 50 + i), (SCREEN_WIDTH, base_y - tower_h - 50 + i))

        # ---- stars twinkle ----
        for sx, sy, phase, br in stars:
            tw = 0.5 + 0.5 * math.sin(elapsed * 2.4 + phase)
            c = int(br * (0.6 + 0.4 * tw))
            screen.set_at((sx, sy), (c, c, min(255, c + 25)))

        # ---- an approaching light (2s–9s): small, shimmering, growing ----
        if 1.8 <= elapsed < 9.0:
            t = (elapsed - 1.8) / 7.2
            lx = tower_cx + int(math.sin(elapsed * 1.3) * 60 * (1 - t))
            ly = int(60 + t * (base_y - tower_h - 120))
            radius = int(2 + t * 10)
            for r in range(radius + 16, 0, -1):
                alpha = max(0, 200 - r * 9)
                pygame.draw.circle(
                    screen,
                    (min(255, alpha + 20), min(255, alpha + 10), min(255, alpha + 50)),
                    (lx, ly),
                    r,
                )

        # ---- mothership descends (8.5s onward) ----
        if elapsed >= 8.5:
            t = min(1.0, (elapsed - 8.5) / 3.2)
            ship_x = tower_cx
            ship_y = int(90 + t * (base_y - tower_h - 200))
            ship_w = int(60 + t * 300)
            ship_h = int(10 + t * 46)

            # Glowing halo behind the ship
            halo = pygame.Surface((ship_w + 120, ship_h + 80), pygame.SRCALPHA)
            for r in range(40, 0, -2):
                a = int(4 * r * t)
                pygame.draw.ellipse(
                    halo,
                    (180, 180, 255, min(255, a)),
                    (
                        60 - r,
                        40 - r,
                        ship_w + 2 * r,
                        ship_h + 2 * r,
                    ),
                )
            screen.blit(halo, (ship_x - ship_w // 2 - 60, ship_y - ship_h // 2 - 40))

            # Hull (dark, metallic)
            pygame.draw.ellipse(
                screen,
                (45, 52, 72),
                (ship_x - ship_w // 2, ship_y - ship_h // 2, ship_w, ship_h),
            )
            pygame.draw.ellipse(
                screen,
                (28, 34, 50),
                (ship_x - ship_w // 2, ship_y - 2, ship_w, ship_h // 2),
            )

            # Rim lights (blinking amber / white / cyan)
            num_lights = 18
            for i in range(num_lights):
                frac = i / (num_lights - 1)
                angle = math.pi * frac
                lx = ship_x + int(math.cos(angle) * (ship_w / 2 - 12))
                ly = ship_y + int(math.sin(angle) * (ship_h / 2 + 2))
                blink = 0.5 + 0.5 * math.sin(elapsed * 7 + i * 1.3)
                palette = [
                    (255, 230, 140),
                    (180, 220, 255),
                    (255, 180, 130),
                    (240, 255, 220),
                ]
                base = palette[i % len(palette)]
                c = tuple(int(40 + (v - 40) * blink) for v in base)
                pygame.draw.circle(screen, c, (lx, ly), 3)

            # Central beacon pulses
            pulse = 0.5 + 0.5 * math.sin(elapsed * 5)
            pygame.draw.circle(
                screen,
                (255, int(210 + 40 * pulse), int(150 + 80 * pulse)),
                (ship_x, ship_y + 4),
                int(6 + 3 * pulse),
            )

            # Beam of light down to the plain (from 10.5s)
            if elapsed >= 10.5:
                beam_t = min(1.0, (elapsed - 10.5) / 1.8)
                beam_top = ship_y + ship_h // 2
                beam_bot = base_y
                beam_h = max(1, beam_bot - beam_top)
                beam_surf = pygame.Surface((220, beam_h), pygame.SRCALPHA)
                for by in range(beam_h):
                    spread = 20 + int((by / beam_h) * 90)
                    a = int(140 * beam_t * (1 - by / beam_h))
                    pygame.draw.line(
                        beam_surf,
                        (255, 250, 210, a),
                        (110 - spread, by),
                        (110 + spread, by),
                    )
                screen.blit(beam_surf, (ship_x - 110, beam_top))

        # ---- mountains on top ----
        pygame.draw.polygon(screen, (10, 12, 22), hills)
        pygame.draw.polygon(screen, (7, 9, 18), tower_poly)

        # ---- small silhouetted figures at the base (11.8s onward) ----
        if elapsed >= 11.8:
            positions = [tower_cx - 140, tower_cx - 100, tower_cx + 100, tower_cx + 140]
            for fx in positions:
                fy = base_y - 8
                pygame.draw.ellipse(screen, BLACK, (fx - 5, fy - 22, 10, 22))
                pygame.draw.circle(screen, BLACK, (fx, fy - 26), 5)
                # long shadows cast by the ship beam
                pygame.draw.line(screen, (0, 0, 0), (fx, fy), (fx, fy + 14), 2)

        # ---- final title card fade-in ----
        if elapsed >= 13.3:
            a = int(255 * min(1.0, (elapsed - 13.3) / 1.2))
            msg = large_font.render("WE COME IN PEACE.", True, WHITE)
            sub = small_font.render("— an encounter of the third kind —", True, CYAN)
            msg.set_alpha(a)
            sub.set_alpha(a)
            screen.blit(
                msg,
                (SCREEN_WIDTH // 2 - msg.get_width() // 2, SCREEN_HEIGHT // 2 - 50),
            )
            screen.blit(
                sub,
                (SCREEN_WIDTH // 2 - sub.get_width() // 2, SCREEN_HEIGHT // 2 + 20),
            )

        pygame.display.flip()
        local_clock.tick(60)

    if AUDIO_OK:
        pygame.mixer.stop()


# ---------- Screens ----------
def draw_center_text(text, y, fnt, color):
    surf = fnt.render(text, True, color)
    screen.blit(surf, (SCREEN_WIDTH // 2 - surf.get_width() // 2, y))


def draw_title(high_score, hint_pulse):
    screen.fill(BLACK)
    # subtle starfield on title
    for i in range(80):
        random.seed(i)
        sx = random.randint(0, SCREEN_WIDTH)
        sy = random.randint(0, SCREEN_HEIGHT)
        screen.set_at((sx, sy), (120, 120, 160))
    random.seed()
    draw_center_text("SPACE INVADERS", 140, large_font, GREEN)
    draw_center_text("Arrow keys move   ·   Space shoots   ·   P pauses", 260, small_font, WHITE)
    draw_center_text(f"High score: {high_score}", 310, font, YELLOW)
    draw_center_text("Press ENTER to start", 400, font, WHITE)
    draw_center_text("Press Q or Esc to quit", 440, small_font, WHITE)
    # An easter-egg hint (subtle, pulsing)
    alpha = int(90 + 70 * (0.5 + 0.5 * math.sin(hint_pulse)))
    hint = small_font.render("...try F3 if you look up at the sky...", True, (alpha, alpha, alpha))
    screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 520))
    pygame.display.flip()


# ---------- Game state ----------
def new_state():
    return {
        "player": Player(),
        "invaders": create_invaders(),
        "bullets": [],
        "enemy_bullets": [],
        "score": 0,
        "lives": 3,
        "direction": 1,
        "speed": 1.0,
        "shoot_cd": 0,
        "enemy_cd": 0,
    }


def draw_playing(state, high_score, paused):
    screen.fill(BLACK)
    state["player"].draw()
    for inv in state["invaders"]:
        inv.draw()
    for b in state["bullets"]:
        b.draw()
    for b in state["enemy_bullets"]:
        b.draw()
    screen.blit(font.render(f"Score: {state['score']}", True, WHITE), (10, 10))
    screen.blit(
        small_font.render(f"High: {high_score}", True, YELLOW),
        (10, 42),
    )
    screen.blit(
        font.render(f"Lives: {state['lives']}", True, WHITE),
        (SCREEN_WIDTH - 120, 10),
    )
    if paused:
        draw_center_text("PAUSED", SCREEN_HEIGHT // 2 - 30, large_font, CYAN)
        draw_center_text("Press P to resume", SCREEN_HEIGHT // 2 + 40, font, WHITE)
    pygame.display.flip()


def draw_end_screen(state, high_score, won):
    screen.fill(BLACK)
    if won:
        draw_center_text("YOU WIN!", 160, large_font, GREEN)
    else:
        draw_center_text("GAME OVER", 160, large_font, RED)
    draw_center_text(f"Final Score: {state['score']}", 260, font, WHITE)
    draw_center_text(f"High Score: {high_score}", 300, font, YELLOW)
    draw_center_text("Press R to play again", 380, font, WHITE)
    draw_center_text("Press Q or Esc to quit", 420, small_font, WHITE)
    draw_center_text("(F3 for a little something else)", 480, small_font, (110, 110, 140))
    pygame.display.flip()


# ---------- Main loop ----------
def main():
    high_score = load_high_score()
    state = new_state()
    mode = "title"  # title | playing | game_over | victory
    paused = False
    title_pulse = 0.0

    while True:
        # ---- events ----
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_high_score(high_score)
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    save_high_score(high_score)
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_F3:
                    # Easter egg available from title / game over / victory
                    if mode in ("title", "game_over", "victory"):
                        play_close_encounters()
                        continue

                if mode == "title":
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        state = new_state()
                        mode = "playing"

                elif mode == "playing":
                    if event.key == pygame.K_p:
                        paused = not paused
                    if event.key == pygame.K_SPACE and state["shoot_cd"] == 0 and not paused:
                        p = state["player"]
                        state["bullets"].append(Bullet(p.x + p.width // 2 - 2, p.y))
                        state["shoot_cd"] = 15

                elif mode in ("game_over", "victory"):
                    if event.key == pygame.K_r:
                        state = new_state()
                        mode = "playing"
                        paused = False

        # ---- per-mode update & draw ----
        if mode == "title":
            title_pulse += 0.05
            draw_title(high_score, title_pulse)

        elif mode == "playing":
            if not paused:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_LEFT]:
                    state["player"].move("left")
                if keys[pygame.K_RIGHT]:
                    state["player"].move("right")
                if keys[pygame.K_SPACE] and state["shoot_cd"] == 0:
                    p = state["player"]
                    state["bullets"].append(Bullet(p.x + p.width // 2 - 2, p.y))
                    state["shoot_cd"] = 15

                if state["shoot_cd"] > 0:
                    state["shoot_cd"] -= 1

                # Move bullets
                for b in state["bullets"][:]:
                    b.move()
                    if b.y < 0:
                        state["bullets"].remove(b)
                for b in state["enemy_bullets"][:]:
                    b.move()
                    if b.y > SCREEN_HEIGHT:
                        state["enemy_bullets"].remove(b)

                # Move invaders
                move_down = False
                for inv in state["invaders"]:
                    if inv.x + inv.width >= SCREEN_WIDTH - 10 and state["direction"] == 1:
                        state["direction"] = -1
                        move_down = True
                        break
                    if inv.x <= 10 and state["direction"] == -1:
                        state["direction"] = 1
                        move_down = True
                        break
                for inv in state["invaders"]:
                    inv.x += state["speed"] * state["direction"]
                    if move_down:
                        inv.y += 20

                # Enemy shoots
                state["enemy_cd"] += 1
                if state["enemy_cd"] >= 60 and state["invaders"]:
                    shooter = random.choice(state["invaders"])
                    state["enemy_bullets"].append(
                        EnemyBullet(
                            shooter.x + shooter.width // 2 - 2,
                            shooter.y + shooter.height,
                        )
                    )
                    state["enemy_cd"] = 0

                # Player bullets hit invaders
                for b in state["bullets"][:]:
                    for inv in state["invaders"][:]:
                        if rects_overlap(b, inv):
                            if b in state["bullets"]:
                                state["bullets"].remove(b)
                            state["invaders"].remove(inv)
                            state["score"] += 10
                            if state["score"] > high_score:
                                high_score = state["score"]
                            state["speed"] = 1.0 + (40 - len(state["invaders"])) * 0.05
                            break

                # Enemy bullets hit player
                for b in state["enemy_bullets"][:]:
                    if rects_overlap(b, state["player"]):
                        state["enemy_bullets"].remove(b)
                        state["lives"] -= 1
                        if state["lives"] <= 0:
                            save_high_score(high_score)
                            mode = "game_over"

                # Invaders reach the bottom
                for inv in state["invaders"]:
                    if inv.y + inv.height >= state["player"].y:
                        save_high_score(high_score)
                        mode = "game_over"
                        break

                # Victory
                if not state["invaders"]:
                    save_high_score(high_score)
                    mode = "victory"

            draw_playing(state, high_score, paused)

        elif mode in ("game_over", "victory"):
            draw_end_screen(state, high_score, mode == "victory")

        clock.tick(60)


if __name__ == "__main__":
    main()
