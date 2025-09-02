import sys
import math
import random
import json
import pygame
import array

# -------------------------
# Config
# -------------------------
SCREEN_WIDTH  = 1280
SCREEN_HEIGHT = 720
FPS = 60

AXOLOTL_SIZE      = (80, 80)
STARFRUIT_SIZE    = (40, 40)
TURTLE_SIZE       = (54, 54)
JELLYFISH_SIZE    = (72, 72)

MOVE_SPEED = 6

JELLYFISH_SPEED_MIN = 1.2
JELLYFISH_SPEED_MAX = 2.8

STARFRUIT_SPAWN_INTERVAL = 1500  # ms
JELLYFISH_SPAWN_INTERVAL = 900   # ms

WOBBLE_AMPLITUDE = 6             # px
WOBBLE_SPEED     = 0.006         # radians per ms

TURTLE_SPAWN_EVERY = 4

SCORE_POPUP_DURATION = 700       # ms
SCORE_POPUP_RISE_SPEED = 0.05    # px per ms
SCORE_POPUP_COLOR   = (200, 80, 255)  # bright purple for score popups

HIGH_SCORES_FILE = "high_scores.json"
MAX_HIGH_SCORES  = 10

# Growth settings
AXOLOTL_GROWTH   = 2              # pixels per fruit (width & height)
AXOLOTL_MAX_SIZE = (200, 200)     # max axolotl size clamp

# Font & color settings
FONT_PATH = "assets/DejaVuSans.ttf"
HUD_TEXT_COLOR = (255, 240, 200)  # warm sand tone to match palette
HUD_STATS_COLOR = (30, 130, 110)  # dark seafoam green for lives/score
SHADOW_OFFSET  = (2, 2)

# -------------------------
# Init pygame
# -------------------------
pygame.init()
pygame.display.set_caption("Axolotl")
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(FONT_PATH, 24)
small_font = pygame.font.Font(FONT_PATH, 20)


def blit_text_with_shadow(text, font, color, pos, center=False):
    """Render text with a shadow for improved readability."""
    shadow_color = tuple(max(0, c - 80) for c in color)
    text_surf = font.render(text, True, color)
    shadow_surf = font.render(text, True, shadow_color)
    if center:
        text_rect = text_surf.get_rect(center=pos)
        shadow_rect = shadow_surf.get_rect(
            center=(pos[0] + SHADOW_OFFSET[0], pos[1] + SHADOW_OFFSET[1])
        )
    else:
        text_rect = text_surf.get_rect(topleft=pos)
        shadow_rect = shadow_surf.get_rect(
            topleft=(pos[0] + SHADOW_OFFSET[0], pos[1] + SHADOW_OFFSET[1])
        )
    screen.blit(shadow_surf, shadow_rect)
    screen.blit(text_surf, text_rect)
    return text_rect

def create_pickup_sound():
    sample_rate = 44100
    duration_ms = 180
    frequencies = [660, 880]
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = array.array("h")
    for i in range(n_samples):
        t = i / sample_rate
        amplitude = 8000 * (1 - i / n_samples)  # fade out for softer sound
        sample = sum(math.sin(2 * math.pi * f * t) for f in frequencies) / len(frequencies)
        buf.append(int(amplitude * sample))
    return pygame.mixer.Sound(buffer=buf)
try:
    pickup_sound = create_pickup_sound()
except pygame.error:
    pickup_sound = None
# -------------------------
# Load and scale assets
# -------------------------
def load_scaled_axolotl(size):
    idle  = pygame.transform.scale(pygame.image.load("Axel.png").convert_alpha(),       size)
    down  = pygame.transform.scale(pygame.image.load("diver.png").convert_alpha(),      size)
    left  = pygame.transform.scale(pygame.image.load("diverleft.png").convert_alpha(),  size)
    up    = pygame.transform.scale(pygame.image.load("diverup.png").convert_alpha(),    size)
    right = pygame.transform.scale(pygame.image.load("diverRight.png").convert_alpha(), size)
    return idle, down, left, up, right

# Initial axolotl sprites
ax_img_idle, ax_img_down, ax_img_left, ax_img_up, ax_img_right = load_scaled_axolotl(AXOLOTL_SIZE)
ax_mask_idle  = pygame.mask.from_surface(ax_img_idle)
ax_mask_down  = pygame.mask.from_surface(ax_img_down)
ax_mask_left  = pygame.mask.from_surface(ax_img_left)
ax_mask_up    = pygame.mask.from_surface(ax_img_up)
ax_mask_right = pygame.mask.from_surface(ax_img_right)

# Background
background_img = pygame.transform.scale(
    pygame.image.load("Background.png").convert(), (SCREEN_WIDTH, SCREEN_HEIGHT)
)

# Pickups
starfruit_img = pygame.transform.scale(pygame.image.load("Starfruit.png").convert_alpha(),     STARFRUIT_SIZE)
turtle_img    = pygame.transform.scale(pygame.image.load("turtle_shield.png").convert_alpha(), TURTLE_SIZE)
starfruit_mask = pygame.mask.from_surface(starfruit_img)
turtle_mask    = pygame.mask.from_surface(turtle_img)

# Jellyfish: static images, choose one per spawn
jelly_images = [
    pygame.transform.scale(pygame.image.load("Jelly1.png").convert_alpha(), JELLYFISH_SIZE),
    pygame.transform.scale(pygame.image.load("Jelly2.png").convert_alpha(), JELLYFISH_SIZE),
    pygame.transform.scale(pygame.image.load("Jelly3.png").convert_alpha(), JELLYFISH_SIZE),
    pygame.transform.scale(pygame.image.load("Jelly4.png").convert_alpha(), JELLYFISH_SIZE),
]
jelly_masks = [pygame.mask.from_surface(img) for img in jelly_images]

# -------------------------
# Helpers
# -------------------------
def clamp_rect_to_screen(rect):
    rect.left = max(0, rect.left)
    rect.top = max(0, rect.top)
    rect.right = min(SCREEN_WIDTH, rect.right)
    rect.bottom = min(SCREEN_HEIGHT, rect.bottom)

def new_axolotl_rect():
    return ax_img_idle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

def spawn_starfruit(now_ms):
    x = random.randint(30, SCREEN_WIDTH - 30)
    y = random.randint(30, SCREEN_HEIGHT - 30)
    rect = starfruit_img.get_rect(center=(x, y))
    phase = random.uniform(0, 2 * math.pi)  # desync wobble
    return {"rect": rect, "spawn": now_ms, "phase": phase}

def spawn_turtle(now_ms):
    x = random.randint(30, SCREEN_WIDTH - 30)
    y = random.randint(30, SCREEN_HEIGHT - 30)
    rect = turtle_img.get_rect(center=(x, y))
    phase = random.uniform(0, 2 * math.pi)
    return {"rect": rect, "spawn": now_ms, "phase": phase}

def spawn_jelly():
    # Spawn from top at random x, drifting down with slight sideways drift
    idx = random.randrange(len(jelly_images))
    img = jelly_images[idx]  # pick one and keep it static
    mask = jelly_masks[idx]
    x = random.randint(20, SCREEN_WIDTH - 20)
    rect = img.get_rect(midtop=(x, -img.get_height()))
    speed_y = random.uniform(JELLYFISH_SPEED_MIN, JELLYFISH_SPEED_MAX)
    drift = random.uniform(-0.8, 0.8)  # gentle sideways drift
    return {"rect": rect, "vy": speed_y, "vx": drift, "image": img, "mask": mask}

def spawn_score_popup(position, now_ms):
    surf = small_font.render("+1", True, SCORE_POPUP_COLOR)
    x, y = position
    return {"surf": surf, "x": float(x), "y": float(y), "spawn": now_ms, "alpha": 255}

def draw_wobbling(image, item, now_ms):
    wobble = WOBBLE_AMPLITUDE * math.sin(WOBBLE_SPEED * now_ms + item["phase"])
    r = item["rect"].copy()
    r.x += int(round(wobble))
    screen.blit(image, r)

# Growth: rescale all direction sprites and update rect without moving center
def grow_axolotl():
    current_w, current_h = state["ax_sprite"].get_size()
    new_w = min(current_w + AXOLOTL_GROWTH, AXOLOTL_MAX_SIZE[0])
    new_h = min(current_h + AXOLOTL_GROWTH, AXOLOTL_MAX_SIZE[1])
    if (new_w, new_h) == (current_w, current_h):
        return  # already at max size

    global ax_img_idle, ax_img_down, ax_img_left, ax_img_up, ax_img_right
    global ax_mask_idle, ax_mask_down, ax_mask_left, ax_mask_up, ax_mask_right
    ax_img_idle, ax_img_down, ax_img_left, ax_img_up, ax_img_right = load_scaled_axolotl((new_w, new_h))
    ax_mask_idle  = pygame.mask.from_surface(ax_img_idle)
    ax_mask_down  = pygame.mask.from_surface(ax_img_down)
    ax_mask_left  = pygame.mask.from_surface(ax_img_left)
    ax_mask_up    = pygame.mask.from_surface(ax_img_up)
    ax_mask_right = pygame.mask.from_surface(ax_img_right)

    center = state["ax_rect"].center
    state["ax_sprite"] = ax_img_idle
    state["ax_rect"] = ax_img_idle.get_rect(center=center)
    state["ax_mask"] = ax_mask_idle

# -------------------------
# High score helpers
# -------------------------
def load_high_scores():
    try:
        with open(HIGH_SCORES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure ints, sorted desc, capped
        scores = sorted([int(s) for s in data], reverse=True)[:MAX_HIGH_SCORES]
        return scores
    except Exception:
        return []

def save_high_scores(scores):
    try:
        with open(HIGH_SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f)
    except Exception:
        pass

def submit_high_score(scores, new_score):
    # returns (updated_scores, qualifies: bool, rank: int)
    arr = scores[:] + [int(new_score)]
    arr = sorted(arr, reverse=True)[:MAX_HIGH_SCORES]
    rank = arr.index(int(new_score)) + 1
    qualifies = rank <= MAX_HIGH_SCORES
    return arr, qualifies, rank

def reset_game_state():
    now = pygame.time.get_ticks()
    s = {
        "ax_rect": new_axolotl_rect(),
        "ax_sprite": ax_img_idle,
        "ax_mask": ax_mask_idle,
        "lives": 3,
        "has_shield": False,
        "starfruits": [],
        "turtles": [],
        "jellies": [],
        "score_popups": [],
        "starfruit_spawns": 0,
        "last_starfruit_spawn": now,
        "last_jelly_spawn": now,
        "game_over": False,
        "score": 0,                # score counter
        "score_submitted": False,  # high score submitted flag
        "new_high": False,         # whether this run hit the board
        "rank": None,              # rank on the board
    }
    # Spawn a turtle power-up at the start of the game (retry until not overlapping axolotl)
    t = spawn_turtle(now)
    while t["rect"].colliderect(s["ax_rect"]):
        t = spawn_turtle(now)
    s["turtles"].append(t)
    return s

# -------------------------
# Initialize
# -------------------------
high_scores = load_high_scores()
state = reset_game_state()

# -------------------------
# Game loop
# -------------------------
running = True
while running:
    dt = clock.tick(FPS)
    now = pygame.time.get_ticks()

    # Events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        running = False

    # Update
    if not state["game_over"]:
        # Movement: Arrow keys and WASD
        dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = int(keys[pygame.K_DOWN]  or keys[pygame.K_s]) - int(keys[pygame.K_UP]   or keys[pygame.K_w])

        # Normalize diagonal (keeps speed consistent)
        if dx != 0 or dy != 0:
            length = math.sqrt(dx*dx + dy*dy)
            ux, uy = dx / length, dy / length
            move_x = int(round(ux * MOVE_SPEED))
            move_y = int(round(uy * MOVE_SPEED))
        else:
            move_x = move_y = 0

        # Move axolotl and clamp
        state["ax_rect"].x += move_x
        state["ax_rect"].y += move_y
        clamp_rect_to_screen(state["ax_rect"])

        # Choose sprite by direction
        if move_x > 0:
            state["ax_sprite"] = ax_img_right
            state["ax_mask"] = ax_mask_right
        elif move_x < 0:
            state["ax_sprite"] = ax_img_left
            state["ax_mask"] = ax_mask_left
        elif move_y > 0:
            state["ax_sprite"] = ax_img_down
            state["ax_mask"] = ax_mask_down
        elif move_y < 0:
            state["ax_sprite"] = ax_img_up
            state["ax_mask"] = ax_mask_up
        else:
            state["ax_sprite"] = ax_img_idle
            state["ax_mask"] = ax_mask_idle

        # Spawning: Starfruit (random positions, stationary with wobble)
        if now - state["last_starfruit_spawn"] >= STARFRUIT_SPAWN_INTERVAL:
            state["starfruits"].append(spawn_starfruit(now))
            state["starfruit_spawns"] += 1
            state["last_starfruit_spawn"] = now

            # Every N starfruit spawns, add a turtle shield
            if state["starfruit_spawns"] % TURTLE_SPAWN_EVERY == 0:
                state["turtles"].append(spawn_turtle(now))

        # Spawning: Jellyfish (static image selection per spawn)
        if now - state["last_jelly_spawn"] >= JELLYFISH_SPAWN_INTERVAL:
            state["jellies"].append(spawn_jelly())
            state["last_jelly_spawn"] = now

        # Update jellyfish movement (no animation)
        for j in state["jellies"]:
            j["rect"].x += int(j["vx"])
            j["rect"].y += int(j["vy"])

        # Remove off-screen jellies
        state["jellies"] = [j for j in state["jellies"] if j["rect"].top <= SCREEN_HEIGHT]

        # Collisions: Jellyfish with axolotl
        for j in state["jellies"][:]:
            if state["ax_rect"].colliderect(j["rect"]):
                offset = (j["rect"].x - state["ax_rect"].x, j["rect"].y - state["ax_rect"].y)
                if state["ax_mask"].overlap(j["mask"], offset):
                    if state["has_shield"]:
                        state["has_shield"] = False
                        state["jellies"].remove(j)
                    else:
                        state["lives"] -= 1
                        state["jellies"].remove(j)
                        if state["lives"] <= 0:
                            state["game_over"] = True
                            if not state["score_submitted"]:
                                updated, qualifies, rank = submit_high_score(high_scores, state["score"])
                                high_scores[:] = updated
                                save_high_scores(high_scores)
                                state["score_submitted"] = True
                                state["new_high"] = qualifies
                                state["rank"] = rank
                            break

        # Collisions: Starfruits with axolotl
        for f in state["starfruits"][:]:
            if state["ax_rect"].colliderect(f["rect"]):
                offset = (f["rect"].x - state["ax_rect"].x, f["rect"].y - state["ax_rect"].y)
                if state["ax_mask"].overlap(starfruit_mask, offset):
                    pos = f["rect"].center
                    state["starfruits"].remove(f)
                    state["score"] += 1  # 1 point per starfruit
                    grow_axolotl()       # grow on pickup
                    state["score_popups"].append(spawn_score_popup(pos, now))
                    if pickup_sound:
                        pickup_sound.play()

        # Collisions: Turtle shields with axolotl
        for t in state["turtles"][:]:
            if state["ax_rect"].colliderect(t["rect"]):
                offset = (t["rect"].x - state["ax_rect"].x, t["rect"].y - state["ax_rect"].y)
                if state["ax_mask"].overlap(turtle_mask, offset):
                    state["turtles"].remove(t)
                    state["has_shield"] = True

    else:
        # Game Over: allow restart
           if keys[pygame.K_r]:
            state = reset_game_state()

    # Update score popups
    for p in state["score_popups"][:]:
        elapsed = now - p["spawn"]
        p["y"] -= SCORE_POPUP_RISE_SPEED * dt
        p["alpha"] = 255 - (elapsed / SCORE_POPUP_DURATION) * 255
        if elapsed >= SCORE_POPUP_DURATION:
            state["score_popups"].remove(p)

    # -------------------------
    # Drawing
    # -------------------------
    # Background first
    screen.blit(background_img, (0, 0))

    # Draw pickups with wobble
    for f in state["starfruits"]:
        draw_wobbling(starfruit_img, f, now)
    for t in state["turtles"]:
        draw_wobbling(turtle_img, t, now)

    # Draw jellyfish (static images)
    for j in state["jellies"]:
        screen.blit(j["image"], j["rect"])

    # Draw axolotl
    screen.blit(state["ax_sprite"], state["ax_rect"])

    # Draw score popups
    for p in state["score_popups"]:
        surf = p["surf"].copy()
        surf.set_alpha(max(0, int(p["alpha"])))
        rect = surf.get_rect(center=(int(p["x"]), int(p["y"])))
        screen.blit(surf, rect)

    # UI: Lives, score, and shield indicator
    blit_text_with_shadow(f"Lives: {state['lives']}", font, HUD_STATS_COLOR, (10, 10))
    blit_text_with_shadow(f"Score: {state['score']}", font, HUD_STATS_COLOR, (10, 46))

    if state["has_shield"]:
        blit_text_with_shadow("Shield Active", font, HUD_TEXT_COLOR, (10, 82))

    # Game over overlay with Top 10
    if state["game_over"]:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        cx = SCREEN_WIDTH // 2
        y = SCREEN_HEIGHT // 2 - 120

        blit_text_with_shadow("Game Over", font, HUD_TEXT_COLOR, (cx, y), center=True)
        y += 40

        blit_text_with_shadow(f"Score: {state['score']}", font, HUD_TEXT_COLOR, (cx, y), center=True)
        y += 36

        if state.get("new_high"):
            blit_text_with_shadow(
                f"New High Score! Rank #{state.get('rank', '?')}",
                font,
                (255, 215, 0),
                (cx, y),
                center=True,
            )
            y += 36

        blit_text_with_shadow("Top 10 High Scores", font, HUD_TEXT_COLOR, (cx, y), center=True)
        y += 32

        for idx, sc in enumerate(high_scores[:MAX_HIGH_SCORES], start=1):
            is_this_run = (state["score_submitted"] and sc == state["score"] and idx == state.get("rank"))
            color = (255, 215, 0) if is_this_run else (230, 230, 230)
            blit_text_with_shadow(f"{idx:2d}. {sc}", small_font, color, (cx, y), center=True)
            y += 24

        blit_text_with_shadow(
            "Press R to Restart or Esc to Quit",
            font,
            HUD_TEXT_COLOR,
            (cx, SCREEN_HEIGHT // 2 + 220),
            center=True,
        )

    pygame.display.flip()

pygame.quit()

sys.exit()






