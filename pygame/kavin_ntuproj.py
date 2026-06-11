"""
kavin_ntuproj.py
================================================================================
A complete, single-file 2D pixel-art action-RPG built with Pygame.

A blend of Terraria / Mario / Stardew Valley / D&D ideas:
  - Side-scrolling platformer movement (run, jump, double-jump, sprint)
  - Health / Mana / Stamina, XP & leveling
  - Sword, Bow and Magic combat with crits, damage numbers, status effects
  - Multiple biomes (Grasslands, Forest, Desert, Snow, Dungeon)
  - Platforms, hazards, checkpoints, spawn points
  - Enemies (Slime, Goblin, Skeleton, Mage, Dragon) with patrol/chase/attack AI
  - 3 unique bosses with multiple attack patterns and health bars
  - Loot: coins, weapons, armor, potions, rare/boss drops
  - Drag-and-drop inventory, equipment slots, tooltips, stackable items
  - NPCs: merchants, healers, blacksmiths, quest givers + dialogue system
  - Shops (buy/sell), gold currency
  - Quests: main / side / hidden, quest log, rewards
  - Day/night cycle, camera follow, particles, animated sprites
  - Save / load to JSON
  - Menus: main, pause, settings, inventory, quest, game over, victory
  - Audio support that auto-disables when files are missing
  - Custom player sprite from assets/player.png with auto fallback

Run:
    python kavin_ntuproj.py

Controls (also shown in-game):
    A / D or Left / Right .... move
    Space .................... jump (press again in air for double jump)
    Left Shift ............... sprint (uses stamina)
    J ........................ sword attack
    K ........................ bow attack (uses stamina)
    L ........................ magic attack (uses mana)
    I ........................ inventory
    Q ........................ quest log
    E ........................ interact with NPC / checkpoint
    Esc ...................... pause
    F5 / F9 .................. quick save / quick load

Only pygame + Python standard library are used.
================================================================================
"""

import os
import sys
import json
import math
import random
import time
import pygame

# ------------------------------------------------------------------------------
# GLOBAL CONFIGURATION
# ------------------------------------------------------------------------------

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 640
FPS = 60
TITLE = "A Pixel RPG - by grp 23"

TILE = 32  # logical tile size in pixels

GRAVITY = 0.6
TERMINAL_VELOCITY = 18

ASSET_DIR = "assets"
SAVE_FILE = "savegame.json"

# Color palette ----------------------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (245, 245, 245)
GREY = (110, 110, 120)
DARK_GREY = (40, 40, 48)
RED = (210, 60, 60)
GREEN = (70, 190, 90)
BLUE = (70, 120, 220)
YELLOW = (235, 210, 70)
ORANGE = (235, 150, 60)
PURPLE = (160, 90, 200)
BROWN = (120, 80, 50)
CYAN = (90, 210, 220)
PINK = (230, 130, 180)
GOLD = (240, 200, 80)

# Biome background colors (day) ------------------------------------------------
BIOME_COLORS = {
    "grasslands": (135, 206, 235),
    "forest": (90, 150, 120),
    "desert": (230, 200, 140),
    "snow": (200, 220, 235),
    "dungeon": (45, 40, 55),
}

BIOME_GROUND = {
    "grasslands": (95, 160, 75),
    "forest": (60, 110, 70),
    "desert": (210, 180, 110),
    "snow": (220, 230, 240),
    "dungeon": (70, 64, 80),
}

# ------------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------------------------
def clamp(value, low, high):
    """Clamp value between low and high."""
    return max(low, min(high, value))


def lerp(a, b, t):
    """Linear interpolation."""
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    """Interpolate between two RGB colors."""
    return (
        int(clamp(lerp(c1[0], c2[0], t), 0, 255)),
        int(clamp(lerp(c1[1], c2[1], t), 0, 255)),
        int(clamp(lerp(c1[2], c2[2], t), 0, 255)),
    )


def distance(ax, ay, bx, by):
    """Euclidean distance between two points."""
    return math.hypot(ax - bx, ay - by)


def sign(x):
    """Return -1, 0, or 1 depending on sign of x."""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def make_pixel_surface(width, height, base_color, noise=18, alpha=255):
    """Create a simple pixel-art style surface with subtle color noise."""
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    block = 4
    for y in range(0, height, block):
        for x in range(0, width, block):
            shade = random.randint(-noise, noise)
            col = (
                clamp(base_color[0] + shade, 0, 255),
                clamp(base_color[1] + shade, 0, 255),
                clamp(base_color[2] + shade, 0, 255),
                alpha,
            )
            pygame.draw.rect(surf, col, (x, y, block, block))
    return surf


# ------------------------------------------------------------------------------
# ASSET MANAGER - handles images, fonts, and audio with graceful fallback
# ------------------------------------------------------------------------------

class AssetManager:
    """Loads and caches assets. Missing assets fall back gracefully."""

    def __init__(self):
        self.images = {}
        self.fonts = {}
        self.sounds = {}
        self.audio_enabled = True
        self.music_loaded = False

        # Attempt to initialize the mixer; disable audio if it fails.
        try:
            pygame.mixer.init()
        except pygame.error:
            self.audio_enabled = False

    # --- Fonts ----------------------------------------------------------------
    def font(self, size):
        if size not in self.fonts:
            try:
                self.fonts[size] = pygame.font.Font(None, size)
            except Exception:
                self.fonts[size] = pygame.font.SysFont("consolas", size)
        return self.fonts[size]

    # --- Images ---------------------------------------------------------------
    def load_image(self, name, path, fallback_size=(32, 32), fallback_color=GREY):
        """Load an image, building a fallback surface if the file is missing."""
        if name in self.images:
            return self.images[name]

        surf = None
        if os.path.isfile(path):
            try:
                surf = pygame.image.load(path).convert_alpha()
            except Exception:
                surf = None

        if surf is None:
            # Build a recognizable fallback sprite.
            surf = make_pixel_surface(
                fallback_size[0], fallback_size[1], fallback_color
            )
            pygame.draw.rect(surf, BLACK, surf.get_rect(), 2)

        self.images[name] = surf
        return surf

    # --- Sounds ---------------------------------------------------------------
    def load_sound(self, name, path):
        if not self.audio_enabled:
            return None
        if name in self.sounds:
            return self.sounds[name]
        snd = None
        if os.path.isfile(path):
            try:
                snd = pygame.mixer.Sound(path)
            except Exception:
                snd = None
        self.sounds[name] = snd
        return snd

    def play_sound(self, name, path=None, volume=0.5):
        if not self.audio_enabled:
            return
        snd = self.sounds.get(name)
        if snd is None and path is not None:
            snd = self.load_sound(name, path)
        if snd is not None:
            try:
                snd.set_volume(volume)
                snd.play()
            except Exception:
                pass

    def play_music(self, path, volume=0.3):
        if not self.audio_enabled:
            return
        if os.path.isfile(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(volume)
                pygame.mixer.music.play(-1)
                self.music_loaded = True
            except Exception:
                self.music_loaded = False

    def set_music_volume(self, volume):
        if self.audio_enabled and self.music_loaded:
            try:
                pygame.mixer.music.set_volume(volume)
            except Exception:
                pass


# ------------------------------------------------------------------------------
# SPRITE FACTORY - procedurally builds animated pixel sprites
# ------------------------------------------------------------------------------

class SpriteFactory:
    """Generates simple animated pixel-art frames for entities."""

    @staticmethod
    def player_frames(assets):
        """Return a dict of animation frames for the player.

        Tries assets/player.png first; if found it is used as the idle base
        and tinted/shifted for animation. Otherwise builds a fallback hero.
        """
        frames = {"idle": [], "run": [], "jump": [], "attack": []}
        w, h = 28, 40

        base = None
        path = os.path.join(ASSET_DIR, "player.png")
        if os.path.isfile(path):
            try:
                loaded = pygame.image.load(path).convert_alpha()
                base = pygame.transform.scale(loaded, (w, h))
            except Exception:
                base = None

        def build_hero(offset=0, arm=0, color=(80, 120, 200)):
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            # legs
            pygame.draw.rect(s, (60, 50, 80), (6, 28 + offset, 6, 12 - offset))
            pygame.draw.rect(s, (60, 50, 80), (16, 28 - offset, 6, 12 + offset))
            # body / tunic
            pygame.draw.rect(s, color, (5, 14, 18, 16))
            # belt
            pygame.draw.rect(s, BROWN, (5, 26, 18, 3))
            # arms
            pygame.draw.rect(s, color, (2, 15 + arm, 4, 10))
            pygame.draw.rect(s, color, (22, 15 - arm, 4, 10))
            # head
            pygame.draw.rect(s, (235, 200, 165), (7, 2, 14, 13))
            # hair
            pygame.draw.rect(s, (90, 60, 40), (6, 1, 16, 5))
            # eyes
            pygame.draw.rect(s, BLACK, (10, 8, 2, 2))
            pygame.draw.rect(s, BLACK, (16, 8, 2, 2))
            return s

        if base is not None:
            # Use loaded sprite and create variants for motion feel.
            for i in range(2):
                frames["idle"].append(base.copy())
            for i in range(4):
                f = base.copy()
                # bob the sprite for run feel
                shifted = pygame.Surface((w, h), pygame.SRCALPHA)
                shifted.blit(f, (0, (i % 2) * 2 - 1))
                frames["run"].append(shifted)
            frames["jump"].append(base.copy())
            for i in range(2):
                frames["attack"].append(base.copy())
        else:
            frames["idle"] = [build_hero(0, 0), build_hero(0, 1)]
            frames["run"] = [
                build_hero(2, 2),
                build_hero(0, 0),
                build_hero(2, -2),
                build_hero(0, 0),
            ]
            frames["jump"] = [build_hero(-2, 3)]
            frames["attack"] = [build_hero(0, 4), build_hero(0, 5)]

        return frames

    @staticmethod
    def slime_frames():
        frames = []
        for i in range(4):
            s = pygame.Surface((30, 24), pygame.SRCALPHA)
            squash = (i % 2) * 3
            pygame.draw.ellipse(s, (90, 200, 120), (2, 6 + squash, 26, 18 - squash))
            pygame.draw.ellipse(s, (130, 230, 150), (6, 9 + squash, 8, 6))
            pygame.draw.rect(s, BLACK, (10, 13, 3, 3))
            pygame.draw.rect(s, BLACK, (18, 13, 3, 3))
            frames.append(s)
        return frames

    @staticmethod
    def goblin_frames():
        frames = []
        for i in range(4):
            s = pygame.Surface((28, 34), pygame.SRCALPHA)
            leg = (i % 2) * 2
            pygame.draw.rect(s, (60, 100, 60), (6, 24, 5, 9 - leg))
            pygame.draw.rect(s, (60, 100, 60), (16, 24, 5, 9 + leg))
            pygame.draw.rect(s, (90, 150, 90), (5, 12, 17, 14))
            pygame.draw.rect(s, (120, 180, 120), (8, 2, 12, 11))  # head
            pygame.draw.polygon(s, (120, 180, 120), [(5, 6), (8, 2), (8, 9)])
            pygame.draw.polygon(s, (120, 180, 120), [(23, 6), (20, 2), (20, 9)])
            pygame.draw.rect(s, RED, (10, 6, 2, 2))
            pygame.draw.rect(s, RED, (16, 6, 2, 2))
            frames.append(s)
        return frames

    @staticmethod
    def skeleton_frames():
        frames = []
        for i in range(4):
            s = pygame.Surface((26, 36), pygame.SRCALPHA)
            sway = (i % 2) * 2 - 1
            pygame.draw.rect(s, (230, 230, 220), (6 + sway, 24, 4, 10))
            pygame.draw.rect(s, (230, 230, 220), (16 - sway, 24, 4, 10))
            for ry in range(13, 24, 3):
                pygame.draw.rect(s, (230, 230, 220), (8, ry, 10, 2))
            pygame.draw.rect(s, (230, 230, 220), (11, 13, 4, 11))
            pygame.draw.circle(s, (240, 240, 230), (13, 8), 7)
            pygame.draw.rect(s, BLACK, (9, 6, 3, 3))
            pygame.draw.rect(s, BLACK, (15, 6, 3, 3))
            frames.append(s)
        return frames

    @staticmethod
    def mage_frames():
        frames = []
        for i in range(4):
            s = pygame.Surface((28, 38), pygame.SRCALPHA)
            glow = (i % 2)
            pygame.draw.polygon(s, (120, 80, 180), [(14, 6), (4, 34), (24, 34)])
            pygame.draw.circle(s, (235, 200, 165), (14, 8), 6)
            pygame.draw.polygon(s, (90, 60, 150), [(14, -2), (7, 8), (21, 8)])  # hat
            pygame.draw.circle(s, (150 + glow * 80, 100, 230), (24, 20), 4)  # orb
            frames.append(s)
        return frames

    @staticmethod
    def dragon_frames():
        frames = []
        for i in range(4):
            s = pygame.Surface((90, 70), pygame.SRCALPHA)
            wing = (i % 2) * 8
            pygame.draw.polygon(s, (160, 60, 70),
                                [(20, 30), (5, 10 - wing), (35, 28)])
            pygame.draw.polygon(s, (160, 60, 70),
                                [(60, 30), (85, 10 - wing), (50, 28)])
            pygame.draw.ellipse(s, (190, 70, 80), (25, 25, 40, 26))
            pygame.draw.ellipse(s, (200, 80, 90), (58, 14, 26, 22))  # head
            pygame.draw.polygon(s, (200, 80, 90), [(80, 18), (90, 16), (82, 24)])
            pygame.draw.rect(s, YELLOW, (72, 20, 4, 4))  # eye
            frames.append(s)
        return frames

    @staticmethod
    def boss_frames(kind):
        """Generate frames for the unique bosses."""
        frames = []
        for i in range(4):
            s = pygame.Surface((110, 110), pygame.SRCALPHA)
            pulse = (i % 2) * 4
            if kind == "GoblinKing":
                pygame.draw.rect(s, (40, 90, 40), (25, 45, 60, 55))
                pygame.draw.rect(s, (70, 140, 70), (30, 15, 50, 40))
                pygame.draw.polygon(s, GOLD, [(30, 15), (40, 0), (50, 15)])
                pygame.draw.polygon(s, GOLD, [(50, 15), (60, 0), (70, 15)])
                pygame.draw.rect(s, RED, (38, 28, 6, 6))
                pygame.draw.rect(s, RED, (66, 28, 6, 6))
            elif kind == "LichLord":
                pygame.draw.polygon(s, (120, 80, 180),
                                    [(55, 10), (20, 105), (90, 105)])
                pygame.draw.circle(s, (235, 235, 225), (55, 25), 18)
                pygame.draw.rect(s, (50 + pulse * 10, 0, 80), (44, 20, 6, 6))
                pygame.draw.rect(s, (50 + pulse * 10, 0, 80), (60, 20, 6, 6))
            else:  # AncientDragon
                wing = pulse * 2
                pygame.draw.polygon(s, (120, 40, 50),
                                    [(40, 55), (5, 20 - wing), (60, 50)])
                pygame.draw.polygon(s, (120, 40, 50),
                                    [(70, 55), (105, 20 - wing), (50, 50)])
                pygame.draw.ellipse(s, (160, 50, 60), (35, 45, 50, 40))
                pygame.draw.ellipse(s, (180, 60, 70), (70, 25, 35, 30))
                pygame.draw.rect(s, YELLOW, (90, 33, 6, 6))
            frames.append(s)
        return frames


# ------------------------------------------------------------------------------
# PARTICLE SYSTEM
# ------------------------------------------------------------------------------

class Particle:
    """A single particle with velocity, gravity option, and fade."""

    def __init__(self, x, y, vx, vy, color, life, size=4, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surf, camx, camy):
        if self.life <= 0:
            return
        t = self.life / self.max_life
        alpha = int(255 * t)
        size = max(1, int(self.size * t))
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        col = (self.color[0], self.color[1], self.color[2], alpha)
        s.fill(col)
        surf.blit(s, (self.x - camx, self.y - camy))


class ParticleSystem:
    """Manages a pool of particles."""

    def __init__(self):
        self.particles = []

    def emit(self, x, y, count, color, spread=3, life=30, size=4,
             gravity=0.0, upward=False):
        for _ in range(count):
            vx = random.uniform(-spread, spread)
            vy = random.uniform(-spread, spread)
            if upward:
                vy = -abs(vy) - 1
            self.particles.append(
                Particle(x, y, vx, vy, color, random.randint(life // 2, life),
                         size, gravity)
            )

    def burst(self, x, y, color, count=14):
        self.emit(x, y, count, color, spread=4, life=34, size=5, gravity=0.2)

    def update(self):
        self.particles = [p for p in self.particles if p.update()]

    def draw(self, surf, camx, camy):
        for p in self.particles:
            p.draw(surf, camx, camy)


# ------------------------------------------------------------------------------
# FLOATING DAMAGE / TEXT NUMBERS
# ------------------------------------------------------------------------------

class FloatingText:
    """Damage numbers and pickup text that rise and fade."""

    def __init__(self, x, y, text, color, size=24, life=50):
        self.x = x
        self.y = y
        self.text = str(text)
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.vy = -1.4

    def update(self):
        self.y += self.vy
        self.vy *= 0.96
        self.life -= 1
        return self.life > 0

    def draw(self, surf, font, camx, camy):
        t = clamp(self.life / self.max_life, 0, 1)
        alpha = int(255 * t)
        img = font.render(self.text, True, self.color)
        img.set_alpha(alpha)
        surf.blit(img, (self.x - camx, self.y - camy))


# ------------------------------------------------------------------------------
# ITEM SYSTEM
# ------------------------------------------------------------------------------

# Item database. Each entry defines type, stats, value, color, and stacking.
ITEM_DB = {
    # Weapons -----------------------------------------------------------------
    "wooden_sword": {"name": "Wooden Sword", "type": "weapon", "subtype": "sword",
                     "atk": 6, "value": 10, "color": BROWN, "stack": False,
                     "desc": "A simple training blade."},
    "iron_sword": {"name": "Iron Sword", "type": "weapon", "subtype": "sword",
                   "atk": 14, "value": 60, "color": GREY, "stack": False,
                   "desc": "A reliable iron sword."},
    "flame_sword": {"name": "Flame Sword", "type": "weapon", "subtype": "sword",
                    "atk": 24, "value": 220, "color": ORANGE, "stack": False,
                    "desc": "Burns enemies on hit.", "effect": "burn"},
    "short_bow": {"name": "Short Bow", "type": "weapon", "subtype": "bow",
                  "atk": 9, "value": 45, "color": (150, 110, 60), "stack": False,
                  "desc": "Fires quick arrows."},
    "long_bow": {"name": "Long Bow", "type": "weapon", "subtype": "bow",
                 "atk": 18, "value": 160, "color": (180, 140, 80), "stack": False,
                 "desc": "Powerful ranged weapon.", "effect": "stun"},
    "apprentice_staff": {"name": "Apprentice Staff", "type": "weapon",
                         "subtype": "magic", "atk": 12, "value": 80,
                         "color": PURPLE, "stack": False,
                         "desc": "Channels arcane bolts."},
    "frost_staff": {"name": "Frost Staff", "type": "weapon", "subtype": "magic",
                    "atk": 20, "value": 240, "color": CYAN, "stack": False,
                    "desc": "Freezes foes solid.", "effect": "freeze"},
    # Armor -------------------------------------------------------------------
    "leather_armor": {"name": "Leather Armor", "type": "armor", "defense": 4,
                      "value": 40, "color": BROWN, "stack": False,
                      "desc": "Light protective gear."},
    "iron_armor": {"name": "Iron Armor", "type": "armor", "defense": 10,
                   "value": 130, "color": GREY, "stack": False,
                   "desc": "Sturdy iron plating."},
    "dragon_armor": {"name": "Dragon Armor", "type": "armor", "defense": 22,
                     "value": 400, "color": RED, "stack": False,
                     "desc": "Forged from dragon scales."},
    # Consumables -------------------------------------------------------------
    "health_potion": {"name": "Health Potion", "type": "consumable",
                      "heal": 40, "value": 20, "color": RED, "stack": True,
                      "desc": "Restores 40 HP."},
    "mana_potion": {"name": "Mana Potion", "type": "consumable", "mana": 40,
                    "value": 20, "color": BLUE, "stack": True,
                    "desc": "Restores 40 MP."},
    "stamina_potion": {"name": "Stamina Elixir", "type": "consumable",
                       "stamina": 50, "value": 15, "color": GREEN, "stack": True,
                       "desc": "Restores 50 stamina."},
    "greater_health": {"name": "Greater Health Potion", "type": "consumable",
                       "heal": 90, "value": 55, "color": (240, 80, 120),
                       "stack": True, "desc": "Restores 90 HP."},
    # Currency / misc ---------------------------------------------------------
    "coin": {"name": "Gold Coin", "type": "currency", "value": 1, "color": GOLD,
             "stack": True, "desc": "Shiny gold."},
    "gem": {"name": "Ruby Gem", "type": "treasure", "value": 100, "color": RED,
            "stack": True, "desc": "A precious rare gem."},
    "dragon_heart": {"name": "Dragon Heart", "type": "treasure", "value": 500,
                     "color": (220, 40, 60), "stack": True,
                     "desc": "Still warm. A boss trophy."},
    "ancient_relic": {"name": "Ancient Relic", "type": "quest", "value": 0,
                      "color": GOLD, "stack": False,
                      "desc": "Sought by the village elder."},
}


class Item:
    """An item instance referencing the item database, with quantity."""

    def __init__(self, key, qty=1):
        self.key = key
        self.qty = qty
        self.data = ITEM_DB.get(key, ITEM_DB["coin"])

    @property
    def name(self):
        return self.data["name"]

    @property
    def type(self):
        return self.data["type"]

    @property
    def stackable(self):
        return self.data.get("stack", False)

    @property
    def value(self):
        return self.data.get("value", 0)

    @property
    def color(self):
        return self.data.get("color", GREY)

    def icon(self, size=28):
        """Render a small pixel icon for the item."""
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        t = self.type
        col = self.color
        if t == "weapon":
            st = self.data.get("subtype")
            if st == "sword":
                pygame.draw.rect(s, col, (size // 2 - 2, 4, 4, size - 12))
                pygame.draw.rect(s, GREY, (size // 2 - 5, size - 10, 10, 3))
            elif st == "bow":
                pygame.draw.arc(s, col, (4, 4, size - 8, size - 8),
                                -1.2, 1.2, 3)
                pygame.draw.line(s, WHITE, (size - 6, 6), (size - 6, size - 6), 1)
            else:  # magic
                pygame.draw.rect(s, BROWN, (size // 2 - 1, 6, 3, size - 10))
                pygame.draw.circle(s, col, (size // 2, 7), 5)
        elif t == "armor":
            pygame.draw.polygon(s, col, [(size // 2, 3), (size - 5, 9),
                                         (size - 7, size - 4), (7, size - 4),
                                         (5, 9)])
        elif t == "consumable":
            pygame.draw.rect(s, (200, 200, 220), (size // 2 - 4, 4, 8, 6))
            pygame.draw.rect(s, col, (size // 2 - 5, 10, 10, size - 14))
        elif t == "currency":
            pygame.draw.circle(s, col, (size // 2, size // 2), size // 3)
            pygame.draw.circle(s, (255, 240, 160), (size // 2, size // 2),
                               size // 3, 2)
        else:
            pygame.draw.polygon(s, col, [(size // 2, 4), (size - 5, size // 2),
                                         (size // 2, size - 4), (5, size // 2)])
        return s

    def to_dict(self):
        return {"key": self.key, "qty": self.qty}

    @staticmethod
    def from_dict(d):
        return Item(d["key"], d.get("qty", 1))


# ------------------------------------------------------------------------------
# INVENTORY SYSTEM
# ------------------------------------------------------------------------------

class Inventory:
    """Holds items in a grid of slots, supports stacking and equipment."""

    def __init__(self, slots=24):
        self.slots = slots
        self.items = [None] * slots
        # equipment slots: weapon, armor
        self.equipment = {"weapon": None, "armor": None}

    def add(self, key, qty=1):
        """Add an item, stacking when possible. Returns leftover qty."""
        data = ITEM_DB.get(key)
        if data is None:
            return qty
        if data.get("stack", False):
            # try to stack into an existing slot
            for it in self.items:
                if it is not None and it.key == key:
                    it.qty += qty
                    return 0
        # find empty slot
        for i in range(self.slots):
            if self.items[i] is None:
                self.items[i] = Item(key, qty)
                return 0
        return qty  # inventory full

    def remove_at(self, index, qty=1):
        it = self.items[index]
        if it is None:
            return
        it.qty -= qty
        if it.qty <= 0:
            self.items[index] = None

    def count(self, key):
        total = 0
        for it in self.items:
            if it is not None and it.key == key:
                total += it.qty
        for slot in self.equipment.values():
            if slot is not None and slot.key == key:
                total += slot.qty
        return total

    def has(self, key, qty=1):
        return self.count(key) >= qty

    def remove_key(self, key, qty=1):
        """Remove qty of a key from inventory items."""
        for i, it in enumerate(self.items):
            if it is not None and it.key == key:
                take = min(qty, it.qty)
                it.qty -= take
                qty -= take
                if it.qty <= 0:
                    self.items[i] = None
                if qty <= 0:
                    return True
        return qty <= 0

    def first_empty(self):
        for i in range(self.slots):
            if self.items[i] is None:
                return i
        return -1

    def to_dict(self):
        return {
            "items": [it.to_dict() if it else None for it in self.items],
            "equipment": {k: (v.to_dict() if v else None)
                          for k, v in self.equipment.items()},
        }

    def from_dict(self, d):
        self.items = [Item.from_dict(x) if x else None for x in d["items"]]
        # pad/trim to slot count
        while len(self.items) < self.slots:
            self.items.append(None)
        self.items = self.items[:self.slots]
        for k, v in d.get("equipment", {}).items():
            self.equipment[k] = Item.from_dict(v) if v else None


# ------------------------------------------------------------------------------
# STATUS EFFECTS
# ------------------------------------------------------------------------------

class StatusEffect:
    """Represents poison, burn, freeze, or stun on an entity."""

    def __init__(self, kind, duration, power=0):
        self.kind = kind
        self.duration = duration
        self.power = power
        self.tick = 0

    def update(self):
        self.duration -= 1
        self.tick += 1
        return self.duration > 0


# ------------------------------------------------------------------------------
# PROJECTILE (arrows, magic bolts, enemy projectiles)
# ------------------------------------------------------------------------------

class Projectile:
    """A flying projectile with owner type and optional status effect."""

    def __init__(self, x, y, vx, vy, damage, owner, color, kind="arrow",
                 effect=None, crit=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.owner = owner  # "player" or "enemy"
        self.color = color
        self.kind = kind
        self.effect = effect
        self.crit = crit
        self.life = 140
        self.rect = pygame.Rect(int(x), int(y), 12, 6)
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.kind == "arrow":
            self.vy += 0.15  # slight gravity on arrows
        self.life -= 1
        self.rect.topleft = (int(self.x), int(self.y))
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, camx, camy):
        sx, sy = self.x - camx, self.y - camy
        if self.kind == "arrow":
            ang = math.atan2(self.vy, self.vx)
            ex = sx + math.cos(ang) * 14
            ey = sy + math.sin(ang) * 14
            pygame.draw.line(surf, self.color, (sx, sy), (ex, ey), 3)
            pygame.draw.circle(surf, WHITE, (int(ex), int(ey)), 2)
        else:
            pygame.draw.circle(surf, self.color, (int(sx), int(sy)), 7)
            pygame.draw.circle(surf, WHITE, (int(sx), int(sy)), 3)


# ------------------------------------------------------------------------------
# ENTITY BASE CLASS (shared physics & status handling)
# ------------------------------------------------------------------------------

class Entity:
    """Base class providing rect, physics and status effects."""

    def __init__(self, x, y, w, h):
        self.x = float(x)
        self.y = float(y)
        self.w = w
        self.h = h
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.facing = 1
        self.statuses = []
        self.max_hp = 100
        self.hp = 100
        self.alive = True

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def cx(self):
        return self.x + self.w / 2

    @property
    def cy(self):
        return self.y + self.h / 2

    def apply_status(self, kind, duration, power=0):
        # refresh if already present
        for st in self.statuses:
            if st.kind == kind:
                st.duration = max(st.duration, duration)
                st.power = max(st.power, power)
                return
        self.statuses.append(StatusEffect(kind, duration, power))

    def has_status(self, kind):
        return any(s.kind == kind for s in self.statuses)

    def update_statuses(self, particles):
        new = []
        for st in self.statuses:
            if st.kind == "poison" and st.tick % 30 == 0 and st.tick > 0:
                self.hp -= st.power
                particles.emit(self.cx, self.cy, 4, GREEN, life=18)
            if st.kind == "burn" and st.tick % 24 == 0 and st.tick > 0:
                self.hp -= st.power
                particles.emit(self.cx, self.cy, 4, ORANGE, life=18, upward=True)
            if st.update():
                new.append(st)
        self.statuses = new

    def is_frozen(self):
        return self.has_status("freeze")

    def is_stunned(self):
        return self.has_status("stun")

    def physics(self, world):
        """Apply gravity and resolve collisions against world platforms."""
        # horizontal
        self.x += self.vx
        for plat in world.solid_rects_near(self.rect):
            if self.rect.colliderect(plat):
                if self.vx > 0:
                    self.x = plat.left - self.w
                elif self.vx < 0:
                    self.x = plat.right
                self.vx = 0

        # vertical
        self.vy = clamp(self.vy + GRAVITY, -30, TERMINAL_VELOCITY)
        self.y += self.vy
        self.on_ground = False
        for plat in world.solid_rects_near(self.rect):
            if self.rect.colliderect(plat):
                if self.vy > 0:
                    self.y = plat.top - self.h
                    self.on_ground = True
                    self.vy = 0
                elif self.vy < 0:
                    self.y = plat.bottom
                    self.vy = 0

        # world bounds
        self.x = clamp(self.x, 0, world.width - self.w)
        if self.y > world.height + 200:
            self.hp = 0  # fell out of world


# ------------------------------------------------------------------------------
# PLAYER CLASS
# ------------------------------------------------------------------------------

class Player(Entity):
    """The controllable hero with full RPG stats and combat."""

    def __init__(self, x, y, assets):
        super().__init__(x, y, 28, 40)
        self.assets = assets
        self.frames = SpriteFactory.player_frames(assets)
        self.anim = "idle"
        self.anim_index = 0
        self.anim_timer = 0

        # Core stats
        self.max_hp = 120
        self.hp = 120
        self.max_mana = 60
        self.mana = 60
        self.max_stamina = 100
        self.stamina = 100

        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.gold = 30

        self.base_atk = 8
        self.base_def = 0

        # Movement tuning
        self.speed = 4.0
        self.sprint_mult = 1.7
        self.jump_power = 12.5
        self.jumps_left = 2
        self.max_jumps = 2

        # Combat state
        self.attack_cd = 0
        self.bow_cd = 0
        self.magic_cd = 0
        self.attacking = 0
        self.invuln = 0
        self.attack_kind = None

        self.inventory = Inventory(24)
        self.inventory.add("wooden_sword")
        self.inventory.add("short_bow")
        self.inventory.add("apprentice_staff")
        self.inventory.add("health_potion", 3)
        self.inventory.add("mana_potion", 2)
        self.inventory.equipment["weapon"] = Item("wooden_sword")

        self.checkpoint = (x, y)
        self.regen_timer = 0

    # --- Derived stats --------------------------------------------------------
    @property
    def attack_power(self):
        base = self.base_atk + self.level * 2
        wpn = self.inventory.equipment.get("weapon")
        if wpn:
            base += wpn.data.get("atk", 0)
        return base

    @property
    def defense(self):
        base = self.base_def + self.level
        arm = self.inventory.equipment.get("armor")
        if arm:
            base += arm.data.get("defense", 0)
        return base

    @property
    def weapon_subtype(self):
        wpn = self.inventory.equipment.get("weapon")
        if wpn:
            return wpn.data.get("subtype", "sword")
        return "sword"

    # --- Leveling -------------------------------------------------------------
    def gain_xp(self, amount, game):
        self.xp += amount
        game.add_text(self.cx, self.y - 10, f"+{amount} XP", CYAN)
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level_up(game)

    def level_up(self, game):
        self.level += 1
        self.xp_to_next = int(self.xp_to_next * 1.35 + 40)
        self.max_hp += 18
        self.max_mana += 8
        self.max_stamina += 6
        self.hp = self.max_hp
        self.mana = self.max_mana
        self.stamina = self.max_stamina
        game.add_text(self.cx, self.y - 30, "LEVEL UP!", GOLD, size=30)
        game.particles.emit(self.cx, self.cy, 30, GOLD, spread=5, life=40,
                            upward=True)
        game.assets.play_sound("levelup",
                               os.path.join(ASSET_DIR, "levelup.wav"), 0.6)

    # --- Input handling -------------------------------------------------------
    def handle_input(self, keys, game):
        if self.is_frozen() or self.is_stunned():
            self.vx = 0
            return

        moving = False
        sprinting = keys[pygame.K_LSHIFT] and self.stamina > 0

        spd = self.speed * (self.sprint_mult if sprinting else 1.0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vx = -spd
            self.facing = -1
            moving = True
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vx = spd
            self.facing = 1
            moving = True
        else:
            self.vx *= 0.6
            if abs(self.vx) < 0.3:
                self.vx = 0

        if sprinting and moving:
            self.stamina = clamp(self.stamina - 0.6, 0, self.max_stamina)

        # animation selection
        if self.attacking > 0:
            self.anim = "attack"
        elif not self.on_ground:
            self.anim = "jump"
        elif moving:
            self.anim = "run"
        else:
            self.anim = "idle"

    def jump(self, game):
        if self.is_frozen() or self.is_stunned():
            return
        if self.jumps_left > 0:
            # second jump slightly weaker
            power = self.jump_power if self.jumps_left == self.max_jumps \
                else self.jump_power * 0.9
            self.vy = -power
            self.jumps_left -= 1
            game.particles.emit(self.cx, self.y + self.h, 8, WHITE, life=18)
            game.assets.play_sound("jump", os.path.join(ASSET_DIR, "jump.wav"),
                                   0.4)

    # --- Attacks --------------------------------------------------------------
    def sword_attack(self, game):
        if self.attack_cd > 0:
            return
        self.attack_cd = 26
        self.attacking = 12
        self.attack_kind = "sword"
        reach = 46
        ax = self.cx + self.facing * 20
        hit_rect = pygame.Rect(0, 0, reach, self.h)
        if self.facing > 0:
            hit_rect.midleft = (self.cx + 6, self.cy)
        else:
            hit_rect.midright = (self.cx - 6, self.cy)

        wpn = self.inventory.equipment.get("weapon")
        effect = wpn.data.get("effect") if wpn else None
        dmg, crit = self.roll_damage()
        for enemy in game.enemies + game.bosses:
            if enemy.alive and hit_rect.colliderect(enemy.rect):
                enemy.take_damage(dmg, game, crit=crit, source=self)
                if effect:
                    self._apply_weapon_effect(enemy, effect)
        game.particles.emit(ax, self.cy, 8, WHITE, life=14)
        game.assets.play_sound("sword", os.path.join(ASSET_DIR, "sword.wav"),
                               0.4)

    def bow_attack(self, game):
        if self.bow_cd > 0 or self.stamina < 8:
            return
        self.bow_cd = 22
        self.stamina = clamp(self.stamina - 8, 0, self.max_stamina)
        self.attacking = 10
        self.attack_kind = "bow"
        dmg, crit = self.roll_damage(mult=0.9)
        wpn = self.inventory.equipment.get("weapon")
        effect = wpn.data.get("effect") if wpn else None
        speed = 11
        proj = Projectile(self.cx, self.cy, self.facing * speed, -1.5, dmg,
                          "player", (200, 180, 120), kind="arrow",
                          effect=effect, crit=crit)
        game.projectiles.append(proj)
        game.assets.play_sound("bow", os.path.join(ASSET_DIR, "bow.wav"), 0.4)

    def magic_attack(self, game):
        if self.magic_cd > 0 or self.mana < 12:
            return
        self.magic_cd = 30
        self.mana = clamp(self.mana - 12, 0, self.max_mana)
        self.attacking = 12
        self.attack_kind = "magic"
        dmg, crit = self.roll_damage(mult=1.2)
        wpn = self.inventory.equipment.get("weapon")
        effect = wpn.data.get("effect") if wpn else None
        col = CYAN if effect == "freeze" else PURPLE
        proj = Projectile(self.cx, self.cy, self.facing * 9, 0, dmg, "player",
                          col, kind="magic", effect=effect, crit=crit)
        game.projectiles.append(proj)
        game.particles.emit(self.cx, self.cy, 10, col, life=20)
        game.assets.play_sound("magic", os.path.join(ASSET_DIR, "magic.wav"),
                               0.4)

    def _apply_weapon_effect(self, enemy, effect):
        if effect == "burn":
            enemy.apply_status("burn", 120, power=3)
        elif effect == "freeze":
            enemy.apply_status("freeze", 90)
        elif effect == "stun":
            enemy.apply_status("stun", 50)
        elif effect == "poison":
            enemy.apply_status("poison", 150, power=2)

    def roll_damage(self, mult=1.0):
        """Return (damage, is_crit)."""
        base = self.attack_power * mult
        crit = random.random() < 0.18
        if crit:
            base *= 2.0
        variance = random.uniform(0.85, 1.15)
        return max(1, int(base * variance)), crit

    # --- Damage / death -------------------------------------------------------
    def take_damage(self, amount, game, source=None):
        if self.invuln > 0:
            return
        dmg = max(1, int(amount - self.defense * 0.5))
        self.hp -= dmg
        self.invuln = 40
        game.add_text(self.cx, self.y - 10, f"-{dmg}", RED)
        game.particles.burst(self.cx, self.cy, RED, count=12)
        game.shake(6)
        game.assets.play_sound("hurt", os.path.join(ASSET_DIR, "hurt.wav"), 0.4)
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def use_item(self, index, game):
        it = self.inventory.items[index]
        if it is None:
            return
        data = it.data
        if data["type"] == "consumable":
            if "heal" in data:
                self.hp = clamp(self.hp + data["heal"], 0, self.max_hp)
                game.add_text(self.cx, self.y - 10, f"+{data['heal']} HP", GREEN)
                game.particles.emit(self.cx, self.cy, 10, GREEN, life=20,
                                    upward=True)
            if "mana" in data:
                self.mana = clamp(self.mana + data["mana"], 0, self.max_mana)
                game.add_text(self.cx, self.y - 10, f"+{data['mana']} MP", BLUE)
            if "stamina" in data:
                self.stamina = clamp(self.stamina + data["stamina"], 0,
                                     self.max_stamina)
            self.inventory.remove_at(index, 1)
            game.assets.play_sound("drink", os.path.join(ASSET_DIR, "drink.wav"),
                                   0.4)
        elif data["type"] == "weapon":
            self.inventory.equipment["weapon"], self.inventory.items[index] = \
                it, self.inventory.equipment["weapon"]
            game.add_text(self.cx, self.y - 10, "Equipped", YELLOW)
        elif data["type"] == "armor":
            self.inventory.equipment["armor"], self.inventory.items[index] = \
                it, self.inventory.equipment["armor"]
            game.add_text(self.cx, self.y - 10, "Equipped", YELLOW)

    # --- Update ---------------------------------------------------------------
    def update(self, game):
        # timers
        for attr in ("attack_cd", "bow_cd", "magic_cd", "invuln"):
            v = getattr(self, attr)
            if v > 0:
                setattr(self, attr, v - 1)
        if self.attacking > 0:
            self.attacking -= 1

        if self.on_ground:
            self.jumps_left = self.max_jumps

        # regen
        self.regen_timer += 1
        if self.regen_timer % 18 == 0:
            self.stamina = clamp(self.stamina + 1.5, 0, self.max_stamina)
            self.mana = clamp(self.mana + 0.5, 0, self.max_mana)
        if self.regen_timer % 90 == 0 and self.hp < self.max_hp:
            self.hp = clamp(self.hp + 1, 0, self.max_hp)

        self.update_statuses(game.particles)
        self.physics(game.world)

        if self.hp <= 0:
            self.alive = False

        # animate
        self.anim_timer += 1
        speed = 6 if self.anim != "run" else 4
        if self.anim_timer >= speed:
            self.anim_timer = 0
            frames = self.frames[self.anim]
            self.anim_index = (self.anim_index + 1) % len(frames)

    def draw(self, surf, camx, camy):
        frames = self.frames.get(self.anim, self.frames["idle"])
        idx = self.anim_index % len(frames)
        img = frames[idx]
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        # flicker when invulnerable
        if self.invuln > 0 and (self.invuln // 3) % 2 == 0:
            img = img.copy()
            img.set_alpha(120)
        surf.blit(img, (self.x - camx, self.y - camy))

        # status tints
        if self.is_frozen():
            tint = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            tint.fill((120, 200, 255, 90))
            surf.blit(tint, (self.x - camx, self.y - camy))

        # draw equipped weapon swing arc
        if self.attacking > 0 and self.attack_kind == "sword":
            ang = (12 - self.attacking) / 12 * math.pi
            cx = self.cx - camx
            cy = self.cy - camy
            r = 36
            ex = cx + math.cos(ang * self.facing) * r * self.facing
            ey = cy - math.sin(ang) * r
            pygame.draw.line(surf, WHITE, (cx, cy), (ex, ey), 3)


# ------------------------------------------------------------------------------
# ENEMY CLASS (Slime, Goblin, Skeleton, Mage, Dragon)
# ------------------------------------------------------------------------------

ENEMY_TEMPLATES = {
    "slime": {"hp": 30, "atk": 8, "speed": 1.2, "xp": 12, "gold": (2, 6),
              "ai": "patrol_jump", "ranged": False, "size": (30, 24),
              "color": GREEN, "drops": [("health_potion", 0.2)]},
    "goblin": {"hp": 50, "atk": 12, "speed": 2.2, "xp": 22, "gold": (5, 12),
               "ai": "chase", "ranged": False, "size": (28, 34),
               "color": (90, 150, 90),
               "drops": [("coin", 0.5), ("iron_sword", 0.05)]},
    "skeleton": {"hp": 65, "atk": 15, "speed": 1.8, "xp": 30, "gold": (6, 14),
                 "ai": "chase", "ranged": True, "size": (26, 36),
                 "color": WHITE,
                 "drops": [("short_bow", 0.06), ("health_potion", 0.15)]},
    "mage": {"hp": 55, "atk": 18, "speed": 1.4, "xp": 38, "gold": (10, 20),
             "ai": "ranged_kite", "ranged": True, "size": (28, 38),
             "color": PURPLE,
             "drops": [("mana_potion", 0.3), ("apprentice_staff", 0.05)]},
    "dragon": {"hp": 160, "atk": 26, "speed": 1.6, "xp": 90, "gold": (30, 60),
               "ai": "flyer", "ranged": True, "size": (90, 70), "color": RED,
               "drops": [("gem", 0.3), ("dragon_armor", 0.04)]},
}


class Enemy(Entity):
    """A standard enemy with patrol/chase/ranged AI."""

    def __init__(self, x, y, kind):
        tpl = ENEMY_TEMPLATES[kind]
        super().__init__(x, y, tpl["size"][0], tpl["size"][1])
        self.kind = kind
        self.tpl = tpl
        self.max_hp = tpl["hp"]
        self.hp = tpl["hp"]
        self.atk = tpl["atk"]
        self.move_speed = tpl["speed"]
        self.ai = tpl["ai"]
        self.ranged = tpl["ranged"]
        self.xp = tpl["xp"]
        self.color = tpl["color"]

        # animation frames
        if kind == "slime":
            self.frames = SpriteFactory.slime_frames()
        elif kind == "goblin":
            self.frames = SpriteFactory.goblin_frames()
        elif kind == "skeleton":
            self.frames = SpriteFactory.skeleton_frames()
        elif kind == "mage":
            self.frames = SpriteFactory.mage_frames()
        else:
            self.frames = SpriteFactory.dragon_frames()

        self.anim_index = 0
        self.anim_timer = 0
        self.patrol_origin = x
        self.patrol_range = random.randint(80, 200)
        self.direction = random.choice([-1, 1])
        self.attack_cd = 0
        self.jump_cd = 0
        self.aggro_range = 320
        self.attack_range = 50
        self.hit_flash = 0
        self.spawn_y = y

    def take_damage(self, amount, game, crit=False, source=None):
        self.hp -= amount
        self.hit_flash = 8
        color = YELLOW if crit else WHITE
        txt = f"{amount}!" if crit else str(amount)
        game.add_text(self.cx, self.y - 10, txt, color,
                      size=28 if crit else 22)
        game.particles.burst(self.cx, self.cy, self.color, count=8)
        if self.hp <= 0:
            self.die(game, source)

    def die(self, game, source):
        self.alive = False
        game.particles.burst(self.cx, self.cy, self.color, count=20)
        if isinstance(source, Player):
            source.gain_xp(self.xp, game)
        # gold drop
        gmin, gmax = self.tpl["gold"]
        gold = random.randint(gmin, gmax)
        game.spawn_loot(self.cx, self.cy, "coin", gold)
        # item drops
        for key, chance in self.tpl["drops"]:
            if random.random() < chance:
                game.spawn_loot(self.cx, self.cy - 10, key, 1)
        game.on_enemy_killed(self.kind)
        game.assets.play_sound("enemy_die",
                               os.path.join(ASSET_DIR, "enemy_die.wav"), 0.4)

    def update(self, game):
        player = game.player
        if self.is_frozen() or self.is_stunned():
            self.vx = 0
            self.update_statuses(game.particles)
            self.physics(game.world)
            return

        if self.attack_cd > 0:
            self.attack_cd -= 1
        if self.jump_cd > 0:
            self.jump_cd -= 1
        if self.hit_flash > 0:
            self.hit_flash -= 1

        dist = distance(self.cx, self.cy, player.cx, player.cy)
        aggro = dist < self.aggro_range and player.alive

        # AI behaviors -------------------------------------------------------
        if self.ai == "patrol_jump":
            self._patrol(game)
            if self.on_ground and self.jump_cd <= 0 and random.random() < 0.02:
                self.vy = -8
                self.jump_cd = 60
            if aggro:
                self.direction = sign(player.cx - self.cx)
                self.vx = self.direction * self.move_speed
            self._melee_contact(game, player)

        elif self.ai == "chase":
            if aggro:
                self.facing = sign(player.cx - self.cx)
                self.vx = self.facing * self.move_speed
                # hop over obstacles
                if self.on_ground and abs(self.vx) > 0 and self.jump_cd <= 0:
                    ahead = self.rect.move(self.facing * 20, 0)
                    blocked = any(ahead.colliderect(r)
                                  for r in game.world.solid_rects_near(ahead))
                    if blocked:
                        self.vy = -10
                        self.jump_cd = 40
            else:
                self._patrol(game)
            if self.ranged and aggro and dist < 280 and self.attack_cd <= 0:
                self._shoot(game, player)
            self._melee_contact(game, player)

        elif self.ai == "ranged_kite":
            if aggro:
                self.facing = sign(player.cx - self.cx)
                # keep distance
                if dist < 180:
                    self.vx = -self.facing * self.move_speed
                elif dist > 260:
                    self.vx = self.facing * self.move_speed
                else:
                    self.vx *= 0.6
                if self.attack_cd <= 0:
                    self._shoot(game, player)
            else:
                self._patrol(game)

        elif self.ai == "flyer":
            # dragons float and dive
            self.vy = math.sin(game.frame_count * 0.04) * 1.5
            if aggro:
                self.facing = sign(player.cx - self.cx)
                self.vx = self.facing * self.move_speed
                if self.attack_cd <= 0 and dist < 360:
                    self._shoot(game, player)
            else:
                self.vx = self.direction * self.move_speed * 0.6
                if abs(self.x - self.patrol_origin) > self.patrol_range:
                    self.direction *= -1
            # custom physics for flyers (no gravity collisions vertically)
            self.x += self.vx
            self.y += self.vy
            self.x = clamp(self.x, 0, game.world.width - self.w)
            self.update_statuses(game.particles)
            self._melee_contact(game, player)
            self._animate()
            return

        self.update_statuses(game.particles)
        self.physics(game.world)
        self._animate()

    def _patrol(self, game):
        self.vx = self.direction * self.move_speed * 0.6
        self.facing = self.direction
        if abs(self.x - self.patrol_origin) > self.patrol_range:
            self.direction *= -1
        # turn at ledges
        if self.on_ground:
            ahead = pygame.Rect(int(self.cx + self.direction * 18),
                                int(self.y + self.h + 4), 6, 6)
            grounded = any(ahead.colliderect(r)
                           for r in game.world.solid_rects_near(ahead))
            if not grounded:
                self.direction *= -1

    def _melee_contact(self, game, player):
        if self.rect.colliderect(player.rect) and self.attack_cd <= 0:
            player.take_damage(self.atk, game, source=self)
            self.attack_cd = 45

    def _shoot(self, game, player):
        self.attack_cd = 70
        ang = math.atan2(player.cy - self.cy, player.cx - self.cx)
        speed = 6
        if self.kind == "mage":
            col = PURPLE
            kind = "magic"
            effect = "poison" if random.random() < 0.3 else None
        elif self.kind == "dragon":
            col = ORANGE
            kind = "magic"
            effect = "burn"
        else:
            col = WHITE
            kind = "arrow"
            effect = None
        proj = Projectile(self.cx, self.cy, math.cos(ang) * speed,
                          math.sin(ang) * speed, self.atk, "enemy", col,
                          kind=kind, effect=effect)
        game.projectiles.append(proj)

    def _animate(self):
        self.anim_timer += 1
        if self.anim_timer >= 8:
            self.anim_timer = 0
            self.anim_index = (self.anim_index + 1) % len(self.frames)

    def draw(self, surf, camx, camy):
        img = self.frames[self.anim_index % len(self.frames)]
        if self.facing < 0:
            img = pygame.transform.flip(img, True, False)
        if self.hit_flash > 0:
            img = img.copy()
            white = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            white.fill((255, 255, 255, 150))
            img.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        surf.blit(img, (self.x - camx, self.y - camy))

        # frozen tint
        if self.is_frozen():
            tint = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            tint.fill((120, 200, 255, 90))
            surf.blit(tint, (self.x - camx, self.y - camy))

        # health bar above enemy
        if self.hp < self.max_hp:
            bw = self.w
            ratio = clamp(self.hp / self.max_hp, 0, 1)
            bx = self.x - camx
            by = self.y - camy - 8
            pygame.draw.rect(surf, DARK_GREY, (bx, by, bw, 4))
            pygame.draw.rect(surf, RED, (bx, by, int(bw * ratio), 4))


# ------------------------------------------------------------------------------
# BOSS CLASS - 3 unique bosses with multiple attack patterns
# ------------------------------------------------------------------------------

BOSS_TEMPLATES = {
    "GoblinKing": {"name": "Goblin King", "hp": 600, "atk": 22, "xp": 400,
                   "gold": (200, 300), "color": (60, 140, 60),
                   "drops": [("iron_sword", 1.0), ("greater_health", 3),
                             ("gem", 2)]},
    "LichLord": {"name": "Lich Lord", "hp": 850, "atk": 28, "xp": 700,
                 "gold": (350, 500), "color": PURPLE,
                 "drops": [("frost_staff", 1.0), ("mana_potion", 5),
                           ("ancient_relic", 1)]},
    "AncientDragon": {"name": "Ancient Dragon", "hp": 1400, "atk": 38,
                      "xp": 1500, "gold": (700, 1000), "color": RED,
                      "drops": [("dragon_armor", 1.0), ("flame_sword", 1.0),
                                ("dragon_heart", 1)]},
}


class Boss(Entity):
    """A multi-phase boss with telegraphed attack patterns."""

    def __init__(self, x, y, kind):
        tpl = BOSS_TEMPLATES[kind]
        super().__init__(x, y, 110, 110)
        self.kind = kind
        self.tpl = tpl
        self.name = tpl["name"]
        self.max_hp = tpl["hp"]
        self.hp = tpl["hp"]
        self.atk = tpl["atk"]
        self.xp = tpl["xp"]
        self.color = tpl["color"]
        self.frames = SpriteFactory.boss_frames(kind)
        self.anim_index = 0
        self.anim_timer = 0
        self.phase = 1
        self.attack_timer = 90
        self.pattern = 0
        self.state = "idle"
        self.state_timer = 0
        self.hit_flash = 0
        self.activated = False
        self.facing = -1
        self.home_x = x
        self.home_y = y

    def take_damage(self, amount, game, crit=False, source=None):
        self.hp -= amount
        self.hit_flash = 6
        self.activated = True
        color = YELLOW if crit else WHITE
        game.add_text(self.cx, self.y - 14, str(amount), color,
                      size=26 if crit else 22)
        game.particles.burst(self.cx, self.cy, self.color, count=6)
        # phase transitions
        if self.hp < self.max_hp * 0.66 and self.phase == 1:
            self.phase = 2
            game.add_text(self.cx, self.y - 40, "Phase 2!", ORANGE, size=30)
        elif self.hp < self.max_hp * 0.33 and self.phase == 2:
            self.phase = 3
            game.add_text(self.cx, self.y - 40, "ENRAGED!", RED, size=32)
        if self.hp <= 0:
            self.die(game, source)

    def die(self, game, source):
        self.alive = False
        game.particles.emit(self.cx, self.cy, 60, self.color, spread=7,
                            life=60, upward=True)
        game.shake(20)
        if isinstance(source, Player):
            source.gain_xp(self.xp, game)
        gmin, gmax = self.tpl["gold"]
        game.spawn_loot(self.cx, self.cy, "coin", random.randint(gmin, gmax))
        for entry in self.tpl["drops"]:
            key = entry[0]
            qty = entry[1] if isinstance(entry[1], int) else 1
            game.spawn_loot(self.cx + random.randint(-40, 40),
                            self.cy, key, qty)
        game.on_boss_killed(self.kind)
        game.assets.play_sound("boss_die",
                               os.path.join(ASSET_DIR, "boss_die.wav"), 0.7)

    def update(self, game):
        player = game.player
        if self.hit_flash > 0:
            self.hit_flash -= 1

        dist = distance(self.cx, self.cy, player.cx, player.cy)
        if not self.activated and dist < 420:
            self.activated = True
        if not self.activated:
            self._animate()
            return

        self.facing = sign(player.cx - self.cx)
        self.attack_timer -= 1

        phase_speed = 1 + (self.phase - 1) * 0.4

        # State machine for attacks ------------------------------------------
        if self.state == "idle":
            # drift toward player slowly
            self.vx = self.facing * 1.2 * phase_speed
            if self.attack_timer <= 0:
                self.pattern = random.randint(0, 2)
                self.state = "telegraph"
                self.state_timer = 30
        elif self.state == "telegraph":
            self.vx *= 0.7
            self.state_timer -= 1
            if self.state_timer % 4 == 0:
                game.particles.emit(self.cx, self.cy, 6, self.color, life=14)
            if self.state_timer <= 0:
                self.state = "attack"
                self.state_timer = 1
                self._do_attack(game, player)
        elif self.state == "attack":
            self.state_timer -= 1
            if self.state_timer <= 0:
                self.state = "idle"
                self.attack_timer = max(40, 110 - self.phase * 20)

        # contact damage
        if self.rect.colliderect(player.rect):
            player.take_damage(self.atk, game, source=self)

        # bosses float (dragon) or walk (others)
        if self.kind == "AncientDragon":
            self.vy = math.sin(game.frame_count * 0.05) * 2
            self.x += self.vx
            self.y += self.vy
            self.x = clamp(self.x, 0, game.world.width - self.w)
        else:
            self.physics(game.world)

        self._animate()

    def _do_attack(self, game, player):
        """Execute the chosen attack pattern for this boss."""
        if self.kind == "GoblinKing":
            if self.pattern == 0:
                # spread of three projectiles
                for off in (-0.3, 0, 0.3):
                    ang = math.atan2(player.cy - self.cy,
                                     player.cx - self.cx) + off
                    self._spawn_proj(game, ang, 7, GREEN, "magic")
            elif self.pattern == 1:
                # leap toward player
                self.vy = -12
                self.vx = self.facing * 8
            else:
                # summon minions
                for _ in range(2):
                    ex = self.cx + random.randint(-60, 60)
                    game.enemies.append(Enemy(ex, self.cy, "goblin"))

        elif self.kind == "LichLord":
            if self.pattern == 0:
                # ring of bolts
                for k in range(8):
                    ang = k / 8 * math.tau
                    self._spawn_proj(game, ang, 5, PURPLE, "magic",
                                     effect="poison")
            elif self.pattern == 1:
                # frost nova homing-ish
                for off in (-0.5, -0.25, 0, 0.25, 0.5):
                    ang = math.atan2(player.cy - self.cy,
                                     player.cx - self.cx) + off
                    self._spawn_proj(game, ang, 6, CYAN, "magic",
                                     effect="freeze")
            else:
                # teleport near player + summon skeleton
                self.x = clamp(player.cx + random.choice([-200, 200]), 0,
                               game.world.width - self.w)
                game.enemies.append(Enemy(self.cx, self.cy - 40, "skeleton"))

        else:  # AncientDragon
            if self.pattern == 0:
                # fire breath fan
                for off in (-0.4, -0.2, 0, 0.2, 0.4):
                    ang = (0 if self.facing > 0 else math.pi) + off
                    self._spawn_proj(game, ang, 8, ORANGE, "magic",
                                     effect="burn")
            elif self.pattern == 1:
                # dive bomb
                self.vy = 14
                self.vx = self.facing * 6
            else:
                # meteor volley from above
                for _ in range(4):
                    mx = player.cx + random.randint(-150, 150)
                    proj = Projectile(mx, self.y - 200, 0, 7, self.atk,
                                      "enemy", RED, kind="magic", effect="burn")
                    game.projectiles.append(proj)
        game.assets.play_sound("boss_attack",
                               os.path.join(ASSET_DIR, "boss_attack.wav"), 0.5)

    def _spawn_proj(self, game, ang, speed, color, kind, effect=None):
        proj = Projectile(self.cx, self.cy, math.cos(ang) * speed,
                          math.sin(ang) * speed, self.atk, "enemy", color,
                          kind=kind, effect=effect)
        game.projectiles.append(proj)

    def _animate(self):
        self.anim_timer += 1
        if self.anim_timer >= 10:
            self.anim_timer = 0
            self.anim_index = (self.anim_index + 1) % len(self.frames)

    def draw(self, surf, camx, camy):
        img = self.frames[self.anim_index % len(self.frames)]
        if self.facing > 0:
            img = pygame.transform.flip(img, True, False)
        if self.hit_flash > 0:
            img = img.copy()
            white = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            white.fill((255, 255, 255, 160))
            img.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        # telegraph glow
        if self.state == "telegraph":
            glow = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            glow.fill((255, 60, 60, 60))
            surf.blit(glow, (self.x - camx, self.y - camy))
        surf.blit(img, (self.x - camx, self.y - camy))


# ------------------------------------------------------------------------------
# LOOT DROP (pickup in world)
# ------------------------------------------------------------------------------

class Loot(Entity):
    """A loot pickup floating in the world."""

    def __init__(self, x, y, key, qty=1):
        super().__init__(x, y, 20, 20)
        self.key = key
        self.qty = qty
        self.item = Item(key, qty)
        self.icon = self.item.icon(20)
        self.bob = random.uniform(0, math.tau)
        self.vy = -4
        self.vx = random.uniform(-2, 2)
        self.collected = False
        self.life = 60 * 30  # despawn after 30s

    def update(self, game):
        self.life -= 1
        self.physics_simple(game.world)
        self.bob += 0.1

    def physics_simple(self, world):
        self.vy = clamp(self.vy + GRAVITY, -20, TERMINAL_VELOCITY)
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.9
        for plat in world.solid_rects_near(self.rect):
            if self.rect.colliderect(plat) and self.vy > 0:
                self.y = plat.top - self.h
                self.vy = 0
                self.vx *= 0.7

    def draw(self, surf, camx, camy):
        oy = math.sin(self.bob) * 3
        surf.blit(self.icon, (self.x - camx, self.y - camy + oy))
        # glow ring for rare items
        if self.item.type in ("treasure", "weapon", "armor"):
            pygame.draw.circle(surf, GOLD,
                               (int(self.cx - camx), int(self.cy - camy + oy)),
                               14, 1)


# ------------------------------------------------------------------------------
# NPC CLASS (merchant, healer, blacksmith, quest giver)
# ------------------------------------------------------------------------------

class NPC(Entity):
    """A non-combat NPC with dialogue and an optional role."""

    def __init__(self, x, y, name, role, dialogue, color=BLUE, shop_items=None,
                 quest_key=None):
        super().__init__(x, y, 28, 42)
        self.name = name
        self.role = role  # "merchant", "healer", "blacksmith", "quest", "elder"
        self.dialogue = dialogue
        self.color = color
        self.shop_items = shop_items or []
        self.quest_key = quest_key
        self.frames = self._build_frames()
        self.anim_index = 0
        self.anim_timer = 0
        self.bob = random.uniform(0, math.tau)

    def _build_frames(self):
        frames = []
        for i in range(2):
            s = pygame.Surface((28, 42), pygame.SRCALPHA)
            offset = i
            pygame.draw.rect(s, self.color, (5, 16, 18, 22))  # robe
            pygame.draw.rect(s, (235, 200, 165), (8, 2, 12, 14))  # head
            # role hat / hint
            if self.role == "merchant":
                pygame.draw.rect(s, GOLD, (6, 0, 16, 4))
            elif self.role == "healer":
                pygame.draw.rect(s, WHITE, (5, 16, 18, 22))
                pygame.draw.rect(s, RED, (12, 22, 4, 10))
                pygame.draw.rect(s, RED, (8, 26, 12, 4))
            elif self.role == "blacksmith":
                pygame.draw.rect(s, DARK_GREY, (5, 16, 18, 22))
                pygame.draw.rect(s, GREY, (18, 24, 8, 4))
            elif self.role in ("quest", "elder"):
                pygame.draw.rect(s, (220, 220, 220), (7, 12, 14, 6))  # beard
            pygame.draw.rect(s, BLACK, (10, 6 + offset, 2, 2))
            pygame.draw.rect(s, BLACK, (16, 6 + offset, 2, 2))
            frames.append(s)
        return frames

    def update(self):
        self.bob += 0.05
        self.anim_timer += 1
        if self.anim_timer >= 30:
            self.anim_timer = 0
            self.anim_index = (self.anim_index + 1) % len(self.frames)

    def draw(self, surf, camx, camy, player):
        img = self.frames[self.anim_index]
        surf.blit(img, (self.x - camx, self.y - camy))
        # name tag
        font = pygame.font.Font(None, 20)
        tag = font.render(self.name, True, WHITE)
        surf.blit(tag, (self.cx - camx - tag.get_width() // 2,
                        self.y - camy - 18))
        # interaction prompt
        if distance(self.cx, self.cy, player.cx, player.cy) < 70:
            prompt = font.render("[E] Talk", True, YELLOW)
            oy = math.sin(self.bob) * 2
            surf.blit(prompt, (self.cx - camx - prompt.get_width() // 2,
                               self.y - camy - 36 + oy))


# ------------------------------------------------------------------------------
# QUEST SYSTEM
# ------------------------------------------------------------------------------

class Quest:
    """A quest with objective tracking and rewards."""

    def __init__(self, key, title, desc, qtype, objective, reward_gold=0,
                 reward_xp=0, reward_items=None, hidden=False):
        self.key = key
        self.title = title
        self.desc = desc
        self.qtype = qtype  # "main", "side", "hidden"
        self.objective = objective  # dict describing goal
        self.progress = 0
        self.target = objective.get("count", 1)
        self.reward_gold = reward_gold
        self.reward_xp = reward_xp
        self.reward_items = reward_items or []
        self.hidden = hidden
        self.active = False
        self.completed = False
        self.claimed = False

    @property
    def is_done(self):
        return self.progress >= self.target

    def advance(self, amount=1):
        if self.active and not self.completed:
            self.progress = min(self.target, self.progress + amount)
            if self.progress >= self.target:
                self.completed = True

    def to_dict(self):
        return {"key": self.key, "progress": self.progress,
                "active": self.active, "completed": self.completed,
                "claimed": self.claimed}

    def from_dict(self, d):
        self.progress = d.get("progress", 0)
        self.active = d.get("active", False)
        self.completed = d.get("completed", False)
        self.claimed = d.get("claimed", False)


class QuestManager:
    """Manages all quests and dispatches progress events."""

    def __init__(self):
        self.quests = {}
        self._build_quests()

    def _build_quests(self):
        self.add(Quest("slay_slimes", "Pest Control",
                       "Defeat 5 slimes in the Grasslands.", "main",
                       {"event": "kill", "target": "slime", "count": 5},
                       reward_gold=50, reward_xp=80,
                       reward_items=[("health_potion", 2)]))
        self.add(Quest("goblin_menace", "Goblin Menace",
                       "Defeat 6 goblins in the Forest.", "main",
                       {"event": "kill", "target": "goblin", "count": 6},
                       reward_gold=120, reward_xp=160,
                       reward_items=[("iron_armor", 1)]))
        self.add(Quest("defeat_goblin_king", "The Goblin King",
                       "Defeat the Goblin King boss.", "main",
                       {"event": "boss", "target": "GoblinKing", "count": 1},
                       reward_gold=300, reward_xp=400,
                       reward_items=[("greater_health", 3)]))
        self.add(Quest("lich_hunt", "Undead Rising",
                       "Defeat 4 skeletons in the Dungeon.", "side",
                       {"event": "kill", "target": "skeleton", "count": 4},
                       reward_gold=100, reward_xp=140,
                       reward_items=[("mana_potion", 3)]))
        self.add(Quest("defeat_lich", "The Lich Lord",
                       "Defeat the Lich Lord and recover the relic.", "main",
                       {"event": "boss", "target": "LichLord", "count": 1},
                       reward_gold=500, reward_xp=700,
                       reward_items=[("frost_staff", 1)]))
        self.add(Quest("dragon_slayer", "Dragon Slayer",
                       "Defeat the Ancient Dragon.", "main",
                       {"event": "boss", "target": "AncientDragon", "count": 1},
                       reward_gold=1000, reward_xp=1500,
                       reward_items=[("dragon_heart", 1)]))
        self.add(Quest("coin_collector", "Treasure Hunter",
                       "Collect 200 gold total.", "side",
                       {"event": "gold", "count": 200},
                       reward_gold=0, reward_xp=120,
                       reward_items=[("gem", 1)]))
        self.add(Quest("hidden_relic", "Whispered Secret",
                       "Find the hidden Ancient Relic chamber.", "hidden",
                       {"event": "find", "target": "relic", "count": 1},
                       reward_gold=250, reward_xp=300,
                       reward_items=[("dragon_armor", 1)], hidden=True))

    def add(self, quest):
        self.quests[quest.key] = quest

    def activate(self, key):
        q = self.quests.get(key)
        if q and not q.active and not q.completed:
            q.active = True
            return q
        return None

    def on_event(self, event, target=None, amount=1, game=None):
        """Dispatch a game event to update quest progress."""
        for q in self.quests.values():
            if not q.active or q.completed:
                continue
            obj = q.objective
            if obj.get("event") != event:
                continue
            if event in ("kill", "boss", "find"):
                if obj.get("target") == target:
                    q.advance(amount)
                    if q.completed and game:
                        game.add_text(game.player.cx, game.player.y - 50,
                                      "Quest Complete!", GOLD, size=28)
            elif event == "gold":
                q.advance(amount)

    def active_quests(self):
        return [q for q in self.quests.values()
                if q.active and not q.claimed]

    def to_dict(self):
        return {k: q.to_dict() for k, q in self.quests.items()}

    def from_dict(self, d):
        for k, qd in d.items():
            if k in self.quests:
                self.quests[k].from_dict(qd)


# ------------------------------------------------------------------------------
# WORLD / LEVEL GENERATION
# ------------------------------------------------------------------------------

class Platform:
    """A solid platform with a biome-based appearance."""

    def __init__(self, x, y, w, h, biome="grasslands", hazard=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.biome = biome
        self.hazard = hazard
        color = BIOME_GROUND.get(biome, GREY)
        if hazard:
            color = (200, 60, 50)
        self.surface = make_pixel_surface(w, h, color, noise=14)
        # add a grassy / textured top
        if not hazard:
            top_col = lerp_color(color, WHITE, 0.25)
            pygame.draw.rect(self.surface, top_col, (0, 0, w, 5))


class Checkpoint:
    """A checkpoint flag that sets the player's respawn point."""

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y - 48, 24, 48)
        self.active = False

    def draw(self, surf, camx, camy):
        bx = self.rect.x - camx
        by = self.rect.y - camy
        pygame.draw.rect(surf, GREY, (bx + 8, by, 4, 48))
        flag_color = GREEN if self.active else (160, 160, 160)
        pygame.draw.polygon(surf, flag_color,
                            [(bx + 12, by + 4), (bx + 32, by + 12),
                             (bx + 12, by + 20)])


class World:
    """Holds the full level: platforms, biomes, checkpoints, spawn points."""

    def __init__(self):
        self.width = 8000
        self.height = 1200
        self.platforms = []
        self.checkpoints = []
        self.biome_regions = []  # list of (x_start, x_end, biome)
        self.spawn_points = []   # (x, y, kind)
        self.boss_arenas = []    # (x, y, kind)
        self.npc_spawns = []     # (x, y) for npc placement
        self.relic_zone = None
        self._generate()
        # spatial buckets for collision optimization
        self._build_buckets()

    def biome_at(self, x):
        for (xs, xe, biome) in self.biome_regions:
            if xs <= x < xe:
                return biome
        return "grasslands"

    def _generate(self):
        """Procedurally lay out the world across five biomes."""
        seg = self.width // 5
        biomes = ["grasslands", "forest", "desert", "snow", "dungeon"]
        for i, b in enumerate(biomes):
            self.biome_regions.append((i * seg, (i + 1) * seg, b))

        ground_y = 820
        # Continuous ground with occasional gaps (hazards / pits)
        x = 0
        while x < self.width:
            biome = self.biome_at(x)
            seg_w = random.randint(180, 420)
            # occasionally create a pit
            if x > 400 and random.random() < 0.18:
                gap = random.randint(60, 130)
                # hazard spikes at bottom of pit sometimes
                if random.random() < 0.5:
                    self.platforms.append(
                        Platform(x, ground_y + 120, gap, 24, biome,
                                 hazard=True))
                x += gap
                continue
            self.platforms.append(Platform(x, ground_y, seg_w, 380, biome))
            x += seg_w

        # Floating platforms for traversal & loot
        for i in range(120):
            px = random.randint(200, self.width - 200)
            py = random.randint(480, 740)
            pw = random.randint(80, 200)
            biome = self.biome_at(px)
            self.platforms.append(Platform(px, py, pw, 24, biome))

        # Hazard platforms (lava / spikes) scattered
        for i in range(25):
            px = random.randint(600, self.width - 400)
            biome = self.biome_at(px)
            self.platforms.append(
                Platform(px, ground_y - 4, random.randint(40, 90), 12, biome,
                         hazard=True))

        # Checkpoints once per biome region
        for i in range(5):
            cx = i * seg + seg // 2
            self.checkpoints.append(Checkpoint(cx, ground_y))

        # Enemy spawn points scaled by biome difficulty
        biome_enemy = {
            "grasslands": ["slime", "slime", "goblin"],
            "forest": ["goblin", "goblin", "skeleton"],
            "desert": ["skeleton", "goblin", "mage"],
            "snow": ["mage", "skeleton", "dragon"],
            "dungeon": ["skeleton", "mage", "dragon"],
        }
        for i in range(70):
            sx = random.randint(300, self.width - 300)
            biome = self.biome_at(sx)
            kind = random.choice(biome_enemy[biome])
            self.spawn_points.append((sx, ground_y - 60, kind))

        # Boss arenas placed near end of certain biomes
        self.boss_arenas.append((seg * 2 - 200, ground_y - 120, "GoblinKing"))
        self.boss_arenas.append((seg * 4 - 200, ground_y - 140, "LichLord"))
        self.boss_arenas.append((self.width - 400, ground_y - 160,
                                 "AncientDragon"))

        # NPC hub near start (a small village)
        for i in range(5):
            self.npc_spawns.append((140 + i * 90, ground_y - 42))

        # Hidden relic chamber deep in the dungeon
        relic_x = seg * 4 + seg // 2
        self.relic_zone = pygame.Rect(relic_x, ground_y - 200, 60, 60)
        # platform island for the relic
        self.platforms.append(Platform(relic_x - 40, ground_y - 150, 140, 20,
                                        "dungeon"))

    def _build_buckets(self):
        """Bucket platforms by x for faster collision queries."""
        self.bucket_size = 256
        self.buckets = {}
        for plat in self.platforms:
            start = plat.rect.left // self.bucket_size
            end = plat.rect.right // self.bucket_size
            for b in range(start, end + 1):
                self.buckets.setdefault(b, []).append(plat)

    def solid_rects_near(self, rect):
        """Return solid (non-hazard) platform rects near a rect."""
        result = []
        start = rect.left // self.bucket_size - 1
        end = rect.right // self.bucket_size + 1
        seen = set()
        for b in range(start, end + 1):
            for plat in self.buckets.get(b, []):
                if id(plat) in seen:
                    continue
                seen.add(id(plat))
                if not plat.hazard:
                    result.append(plat.rect)
        return result

    def hazard_rects_near(self, rect):
        result = []
        start = rect.left // self.bucket_size - 1
        end = rect.right // self.bucket_size + 1
        for b in range(start, end + 1):
            for plat in self.buckets.get(b, []):
                if plat.hazard:
                    result.append(plat.rect)
        return result

    def draw(self, surf, camx, camy, tint):
        """Draw visible platforms with day/night tint."""
        view = pygame.Rect(camx - 50, camy - 50, SCREEN_WIDTH + 100,
                           SCREEN_HEIGHT + 100)
        start = view.left // self.bucket_size - 1
        end = view.right // self.bucket_size + 1
        seen = set()
        for b in range(start, end + 1):
            for plat in self.buckets.get(b, []):
                if id(plat) in seen:
                    continue
                seen.add(id(plat))
                r = plat.rect
                if view.colliderect(r):
                    surf.blit(plat.surface, (r.x - camx, r.y - camy))
                    if tint[3] > 0:
                        overlay = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
                        overlay.fill(tint)
                        surf.blit(overlay, (r.x - camx, r.y - camy))


# ------------------------------------------------------------------------------
# CAMERA
# ------------------------------------------------------------------------------

class Camera:
    """Smoothly follows the player and supports screen shake."""

    def __init__(self, world):
        self.world = world
        self.x = 0
        self.y = 0
        self.shake_amount = 0

    def update(self, target):
        target_x = target.cx - SCREEN_WIDTH / 2
        target_y = target.cy - SCREEN_HEIGHT / 2
        self.x += (target_x - self.x) * 0.12
        self.y += (target_y - self.y) * 0.12
        self.x = clamp(self.x, 0, max(0, self.world.width - SCREEN_WIDTH))
        self.y = clamp(self.y, 0, max(0, self.world.height - SCREEN_HEIGHT))

        if self.shake_amount > 0:
            self.shake_amount -= 1

    @property
    def offset(self):
        ox = self.x
        oy = self.y
        if self.shake_amount > 0:
            ox += random.randint(-6, 6)
            oy += random.randint(-6, 6)
        return ox, oy

    def shake(self, amount):
        self.shake_amount = max(self.shake_amount, amount)


# ------------------------------------------------------------------------------
# DAY / NIGHT CYCLE
# ------------------------------------------------------------------------------

class DayNightCycle:
    """Tracks time of day and provides sky color + darkness tint."""

    def __init__(self, length=3600):
        self.length = length  # frames per full cycle
        self.time = length * 0.25  # start at morning

    def update(self):
        self.time = (self.time + 1) % self.length

    @property
    def phase(self):
        """0..1 across the day."""
        return self.time / self.length

    def darkness(self):
        """Return alpha (0..150) of night overlay."""
        # Peak darkness at phase 0.0/1.0 (midnight), bright at 0.5 (noon)
        p = self.phase
        # distance from noon
        d = abs(p - 0.5) * 2  # 0 at noon, 1 at midnight
        return int(clamp(d * d * 150, 0, 150))

    def sky_color(self, base):
        d = self.darkness() / 150.0
        night = (15, 18, 40)
        return lerp_color(base, night, d)

    def label(self):
        p = self.phase
        if p < 0.2:
            return "Night"
        if p < 0.35:
            return "Dawn"
        if p < 0.65:
            return "Day"
        if p < 0.8:
            return "Dusk"
        return "Night"


# ------------------------------------------------------------------------------
# UI WIDGETS (buttons, bars)
# ------------------------------------------------------------------------------

class Button:
    """A clickable menu button."""

    def __init__(self, x, y, w, h, text, callback, color=DARK_GREY):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.callback = callback
        self.color = color
        self.hover = False

    def update(self, mouse_pos):
        self.hover = self.rect.collidepoint(mouse_pos)

    def draw(self, surf, font):
        col = lerp_color(self.color, WHITE, 0.25) if self.hover else self.color
        pygame.draw.rect(surf, col, self.rect, border_radius=6)
        pygame.draw.rect(surf, WHITE, self.rect, 2, border_radius=6)
        img = font.render(self.text, True, WHITE)
        surf.blit(img, (self.rect.centerx - img.get_width() // 2,
                        self.rect.centery - img.get_height() // 2))

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.callback()
            return True
        return False


def draw_bar(surf, x, y, w, h, ratio, fg, bg=DARK_GREY, border=True,
             label=None, font=None):
    """Draw a stat bar (health/mana/stamina/xp)."""
    ratio = clamp(ratio, 0, 1)
    pygame.draw.rect(surf, bg, (x, y, w, h))
    pygame.draw.rect(surf, fg, (x, y, int(w * ratio), h))
    if border:
        pygame.draw.rect(surf, WHITE, (x, y, w, h), 1)
    if label and font:
        img = font.render(label, True, WHITE)
        surf.blit(img, (x + 4, y + (h - img.get_height()) // 2))


# ------------------------------------------------------------------------------
# GAME STATES
# ------------------------------------------------------------------------------

STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_PAUSE = "pause"
STATE_SETTINGS = "settings"
STATE_INVENTORY = "inventory"
STATE_QUESTS = "quests"
STATE_DIALOGUE = "dialogue"
STATE_SHOP = "shop"
STATE_GAMEOVER = "gameover"
STATE_VICTORY = "victory"


# ------------------------------------------------------------------------------
# MAIN GAME CLASS
# ------------------------------------------------------------------------------

class Game:
    """Top-level game object: owns the loop, state, and all systems."""

    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = STATE_MENU
        self.frame_count = 0

        self.assets = AssetManager()
        # Try to load background music (auto-disables if missing).
        self.assets.play_music(os.path.join(ASSET_DIR, "Hazelwood - Coming Of Age (freetouse.com).mp3"), 0.25)

        # Settings
        self.settings = {
            "music_volume": 0.25,
            "sfx_volume": 0.5,
            "show_fps": True,
            "difficulty": 1.0,
        }

        # UI fonts
        self.font_sm = self.assets.font(20)
        self.font_md = self.assets.font(26)
        self.font_lg = self.assets.font(40)
        self.font_xl = self.assets.font(72)

        # Build menu buttons
        self._build_menus()

        # World / entities initialized on new game
        self.world = None
        self.player = None
        self.camera = None
        self.daynight = None
        self.particles = ParticleSystem()
        self.enemies = []
        self.bosses = []
        self.projectiles = []
        self.loot = []
        self.npcs = []
        self.floating_texts = []
        self.quests = None

        # interaction / dialogue
        self.active_npc = None
        self.dialogue_index = 0
        self.shop_npc = None
        self.shop_mode = "buy"

        # inventory drag-drop
        self.drag_item = None
        self.drag_from = None

        # spawn management
        self.spawn_cooldown = 0
        self.relic_found = False

        self.message = ""
        self.message_timer = 0

        self.bosses_defeated = set()

    # --- Menu setup -----------------------------------------------------------
    def _build_menus(self):
        cx = SCREEN_WIDTH // 2
        self.menu_buttons = [
            Button(cx - 120, 280, 240, 54, "New Game",
                   self.start_new_game, GREEN),
            Button(cx - 120, 348, 240, 54, "Load Game",
                   self.load_game, BLUE),
            Button(cx - 120, 416, 240, 54, "Settings",
                   lambda: self.set_state(STATE_SETTINGS), DARK_GREY),
            Button(cx - 120, 484, 240, 54, "Quit",
                   self.quit_game, RED),
        ]
        self.pause_buttons = [
            Button(cx - 120, 240, 240, 50, "Resume",
                   lambda: self.set_state(STATE_PLAY), GREEN),
            Button(cx - 120, 300, 240, 50, "Save Game",
                   self.save_game, BLUE),
            Button(cx - 120, 360, 240, 50, "Settings",
                   lambda: self.set_state(STATE_SETTINGS), DARK_GREY),
            Button(cx - 120, 420, 240, 50, "Quit to Menu",
                   self.quit_to_menu, RED),
        ]
        self.settings_buttons = [
            Button(cx - 120, 460, 240, 50, "Back",
                   self.settings_back, DARK_GREY),
        ]
        self.gameover_buttons = [
            Button(cx - 120, 360, 240, 54, "Respawn",
                   self.respawn_player, GREEN),
            Button(cx - 120, 428, 240, 54, "Quit to Menu",
                   self.quit_to_menu, RED),
        ]
        self.victory_buttons = [
            Button(cx - 120, 420, 240, 54, "Continue",
                   lambda: self.set_state(STATE_PLAY), GREEN),
            Button(cx - 120, 488, 240, 54, "Quit to Menu",
                   self.quit_to_menu, BLUE),
        ]
        self._prev_state_for_settings = STATE_MENU

    def settings_back(self):
        self.set_state(self._prev_state_for_settings)

    def set_state(self, state):
        if state == STATE_SETTINGS:
            self._prev_state_for_settings = self.state
        self.state = state

    # --- New game / world setup ----------------------------------------------
    def start_new_game(self):
        self.world = World()
        spawn_x = 100
        spawn_y = 700
        self.player = Player(spawn_x, spawn_y, self.assets)
        self.camera = Camera(self.world)
        self.daynight = DayNightCycle()
        self.particles = ParticleSystem()
        self.enemies = []
        self.bosses = []
        self.projectiles = []
        self.loot = []
        self.npcs = []
        self.floating_texts = []
        self.quests = QuestManager()
        self.relic_found = False
        self.bosses_defeated = set()

        self._spawn_npcs()
        self._spawn_initial_enemies()
        self._spawn_bosses()

        # auto-activate the first main quest and a side quest
        self.quests.activate("slay_slimes")
        self.quests.activate("coin_collector")

        self.set_state(STATE_PLAY)
        self.show_message("Defeat enemies, complete quests, and slay the "
                          "three bosses!")

    def _spawn_npcs(self):
        sp = self.world.npc_spawns
        # Merchant
        merch_items = ["health_potion", "mana_potion", "stamina_potion",
                       "iron_sword", "leather_armor", "short_bow",
                       "greater_health"]
        self.npcs.append(NPC(sp[0][0], sp[0][1], "Merchant Bron", "merchant",
                             ["Welcome, traveler!",
                              "Buy low, sell high. That's my motto.",
                              "Take a look at my wares."],
                             color=GOLD, shop_items=merch_items))
        # Healer
        self.npcs.append(NPC(sp[1][0], sp[1][1], "Sister Elara", "healer",
                             ["May light guide you.",
                              "Rest here and I'll mend your wounds.",
                              "You are fully healed. Go bravely."],
                             color=WHITE))
        # Blacksmith
        smith_items = ["iron_sword", "iron_armor", "long_bow",
                       "apprentice_staff"]
        self.npcs.append(NPC(sp[2][0], sp[2][1], "Smith Korga", "blacksmith",
                             ["The forge is always hot.",
                              "Need a sturdier blade? I've got steel.",
                              "Browse my forged goods."],
                             color=DARK_GREY, shop_items=smith_items))
        # Quest giver (main)
        self.npcs.append(NPC(sp[3][0], sp[3][1], "Captain Reyne", "quest",
                             ["The land is overrun with monsters.",
                              "Slimes infest our fields. Thin them out.",
                              "Then the goblins in the forest must fall."],
                             color=BLUE, quest_key="goblin_menace"))
        # Elder (hidden quest + lore)
        self.npcs.append(NPC(sp[4][0], sp[4][1], "Elder Maelo", "elder",
                             ["I have lived through three dragon ages.",
                              "A relic lies hidden in the dungeon depths.",
                              "Find it, and great power is yours."],
                             color=PURPLE, quest_key="hidden_relic"))

    def _spawn_initial_enemies(self):
        # Spawn a subset of spawn points initially; the rest stream in.
        for (sx, sy, kind) in self.world.spawn_points:
            if random.random() < 0.55:
                self.enemies.append(Enemy(sx, sy, kind))

    def _spawn_bosses(self):
        for (bx, by, kind) in self.world.boss_arenas:
            self.bosses.append(Boss(bx, by, kind))

    # --- Loot / events --------------------------------------------------------
    def spawn_loot(self, x, y, key, qty=1):
        if key == "coin":
            # spread coins into a few pickups for feel
            remaining = qty
            while remaining > 0:
                take = min(remaining, random.randint(3, 10))
                self.loot.append(Loot(x + random.randint(-10, 10), y, "coin",
                                      take))
                remaining -= take
        else:
            self.loot.append(Loot(x, y, key, qty))

    def on_enemy_killed(self, kind):
        self.quests.on_event("kill", target=kind, game=self)

    def on_boss_killed(self, kind):
        self.bosses_defeated.add(kind)
        self.quests.on_event("boss", target=kind, game=self)
        self.show_message(f"{BOSS_TEMPLATES[kind]['name']} defeated!")
        # victory if all three bosses are dead
        if len(self.bosses_defeated) >= 3:
            self.set_state(STATE_VICTORY)

    def add_text(self, x, y, text, color, size=22):
        self.floating_texts.append(FloatingText(x, y, text, color, size))

    def shake(self, amount):
        if self.camera:
            self.camera.shake(amount)

    def show_message(self, text, duration=240):
        self.message = text
        self.message_timer = duration

    # --- Save / load ----------------------------------------------------------
    def save_game(self):
        if self.player is None:
            return
        data = {
            "player": {
                "x": self.player.x, "y": self.player.y,
                "hp": self.player.hp, "max_hp": self.player.max_hp,
                "mana": self.player.mana, "max_mana": self.player.max_mana,
                "stamina": self.player.stamina,
                "max_stamina": self.player.max_stamina,
                "level": self.player.level, "xp": self.player.xp,
                "xp_to_next": self.player.xp_to_next,
                "gold": self.player.gold,
                "checkpoint": self.player.checkpoint,
            },
            "inventory": self.player.inventory.to_dict(),
            "quests": self.quests.to_dict(),
            "daynight": self.daynight.time,
            "bosses_defeated": list(self.bosses_defeated),
            "relic_found": self.relic_found,
        }
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f, indent=2)
            self.show_message("Game saved.")
        except Exception as e:
            self.show_message("Save failed: " + str(e))
        if self.state == STATE_PAUSE:
            pass

    def load_game(self):
        if not os.path.isfile(SAVE_FILE):
            self.show_message("No save file found.")
            return
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
        except Exception as e:
            self.show_message("Load failed: " + str(e))
            return

        # rebuild world fresh then overlay saved state
        self.world = World()
        self.camera = Camera(self.world)
        self.daynight = DayNightCycle()
        self.particles = ParticleSystem()
        self.enemies = []
        self.bosses = []
        self.projectiles = []
        self.loot = []
        self.npcs = []
        self.floating_texts = []
        self.quests = QuestManager()
        self._spawn_npcs()
        self._spawn_initial_enemies()
        self._spawn_bosses()

        pd = data["player"]
        self.player = Player(pd["x"], pd["y"], self.assets)
        self.player.hp = pd["hp"]
        self.player.max_hp = pd["max_hp"]
        self.player.mana = pd["mana"]
        self.player.max_mana = pd["max_mana"]
        self.player.stamina = pd["stamina"]
        self.player.max_stamina = pd["max_stamina"]
        self.player.level = pd["level"]
        self.player.xp = pd["xp"]
        self.player.xp_to_next = pd["xp_to_next"]
        self.player.gold = pd["gold"]
        self.player.checkpoint = tuple(pd["checkpoint"])
        self.player.inventory.from_dict(data["inventory"])
        self.quests.from_dict(data["quests"])
        self.daynight.time = data.get("daynight", 0)
        self.bosses_defeated = set(data.get("bosses_defeated", []))
        self.relic_found = data.get("relic_found", False)

        # remove already-defeated bosses
        self.bosses = [b for b in self.bosses
                       if b.kind not in self.bosses_defeated]

        self.set_state(STATE_PLAY)
        self.show_message("Game loaded.")

    def respawn_player(self):
        cp = self.player.checkpoint
        self.player.x, self.player.y = cp
        self.player.hp = self.player.max_hp
        self.player.mana = self.player.max_mana
        self.player.stamina = self.player.max_stamina
        self.player.alive = True
        self.player.vx = 0
        self.player.vy = 0
        self.player.statuses = []
        self.set_state(STATE_PLAY)
        self.show_message("Respawned at checkpoint.")

    def quit_to_menu(self):
        self.set_state(STATE_MENU)

    def quit_game(self):
        self.running = False

    # --- Main loop ------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)
            self.frame_count += 1
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()
        sys.exit()

    # --- Event handling -------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self._handle_mouse_down(event)

            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_up(event)

    def _handle_keydown(self, event):
        key = event.key

        if self.state == STATE_PLAY:
            if key == pygame.K_ESCAPE:
                self.set_state(STATE_PAUSE)
            elif key == pygame.K_i:
                self.set_state(STATE_INVENTORY)
            elif key == pygame.K_q:
                self.set_state(STATE_QUESTS)
            elif key == pygame.K_SPACE:
                self.player.jump(self)
            elif key == pygame.K_j:
                self.player.sword_attack(self)
            elif key == pygame.K_k:
                self.player.bow_attack(self)
            elif key == pygame.K_l:
                self.player.magic_attack(self)
            elif key == pygame.K_e:
                self._interact()
            elif key == pygame.K_F5:
                self.save_game()
            elif key == pygame.K_F9:
                self.load_game()
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self._quick_use_potion(key)

        elif self.state == STATE_INVENTORY:
            if key in (pygame.K_i, pygame.K_ESCAPE):
                self.set_state(STATE_PLAY)

        elif self.state == STATE_QUESTS:
            if key in (pygame.K_q, pygame.K_ESCAPE):
                self.set_state(STATE_PLAY)

        elif self.state == STATE_PAUSE:
            if key == pygame.K_ESCAPE:
                self.set_state(STATE_PLAY)

        elif self.state == STATE_SETTINGS:
            if key == pygame.K_ESCAPE:
                self.settings_back()
            self._settings_keys(key)

        elif self.state == STATE_DIALOGUE:
            if key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN):
                self._advance_dialogue()
            elif key == pygame.K_ESCAPE:
                self.active_npc = None
                self.set_state(STATE_PLAY)

        elif self.state == STATE_SHOP:
            if key == pygame.K_ESCAPE:
                self.set_state(STATE_PLAY)
            elif key == pygame.K_TAB:
                self.shop_mode = "sell" if self.shop_mode == "buy" else "buy"

        elif self.state == STATE_MENU:
            if key == pygame.K_RETURN:
                self.start_new_game()

        elif self.state in (STATE_GAMEOVER, STATE_VICTORY):
            if key == pygame.K_RETURN:
                if self.state == STATE_GAMEOVER:
                    self.respawn_player()
                else:
                    self.set_state(STATE_PLAY)

    def _quick_use_potion(self, key):
        """Quick-use a potion by number key."""
        mapping = {pygame.K_1: "health_potion", pygame.K_2: "mana_potion",
                   pygame.K_3: "stamina_potion", pygame.K_4: "greater_health"}
        want = mapping[key]
        for i, it in enumerate(self.player.inventory.items):
            if it is not None and it.key == want:
                self.player.use_item(i, self)
                return

    def _settings_keys(self, key):
        if key == pygame.K_LEFT:
            self.settings["music_volume"] = clamp(
                self.settings["music_volume"] - 0.05, 0, 1)
            self.assets.set_music_volume(self.settings["music_volume"])
        elif key == pygame.K_RIGHT:
            self.settings["music_volume"] = clamp(
                self.settings["music_volume"] + 0.05, 0, 1)
            self.assets.set_music_volume(self.settings["music_volume"])
        elif key == pygame.K_UP:
            self.settings["sfx_volume"] = clamp(
                self.settings["sfx_volume"] + 0.05, 0, 1)
        elif key == pygame.K_DOWN:
            self.settings["sfx_volume"] = clamp(
                self.settings["sfx_volume"] - 0.05, 0, 1)
        elif key == pygame.K_f:
            self.settings["show_fps"] = not self.settings["show_fps"]

    def _handle_mouse_down(self, event):
        pos = event.pos
        if self.state == STATE_MENU:
            for b in self.menu_buttons:
                if b.click(pos):
                    return
        elif self.state == STATE_PAUSE:
            for b in self.pause_buttons:
                if b.click(pos):
                    return
        elif self.state == STATE_SETTINGS:
            for b in self.settings_buttons:
                if b.click(pos):
                    return
        elif self.state == STATE_GAMEOVER:
            for b in self.gameover_buttons:
                if b.click(pos):
                    return
        elif self.state == STATE_VICTORY:
            for b in self.victory_buttons:
                if b.click(pos):
                    return
        elif self.state == STATE_INVENTORY:
            self._inventory_mouse_down(pos, event.button)
        elif self.state == STATE_SHOP:
            self._shop_mouse_down(pos, event.button)

    def _handle_mouse_up(self, event):
        if self.state == STATE_INVENTORY:
            self._inventory_mouse_up(event.pos)

    # --- Interaction ----------------------------------------------------------
    def _interact(self):
        # Checkpoints
        for cp in self.world.checkpoints:
            if self.player.rect.colliderect(cp.rect.inflate(30, 30)):
                cp.active = True
                self.player.checkpoint = (self.player.x, self.player.y)
                self.show_message("Checkpoint activated!")
                self.particles.emit(cp.rect.centerx, cp.rect.centery, 14,
                                    GREEN, life=24, upward=True)
        # NPCs
        for npc in self.npcs:
            if distance(npc.cx, npc.cy, self.player.cx, self.player.cy) < 70:
                self.active_npc = npc
                self.dialogue_index = 0
                self.set_state(STATE_DIALOGUE)
                return

    def _advance_dialogue(self):
        npc = self.active_npc
        if npc is None:
            self.set_state(STATE_PLAY)
            return
        self.dialogue_index += 1
        if self.dialogue_index >= len(npc.dialogue):
            # dialogue finished: perform role action
            self._npc_action(npc)
            self.active_npc = None
            if self.state == STATE_DIALOGUE:
                self.set_state(STATE_PLAY)

    def _npc_action(self, npc):
        if npc.role == "healer":
            self.player.hp = self.player.max_hp
            self.player.mana = self.player.max_mana
            self.player.stamina = self.player.max_stamina
            self.particles.emit(self.player.cx, self.player.cy, 20, GREEN,
                                life=30, upward=True)
            self.show_message("Fully restored!")
        elif npc.role in ("merchant", "blacksmith"):
            self.shop_npc = npc
            self.shop_mode = "buy"
            self.set_state(STATE_SHOP)
        elif npc.role in ("quest", "elder"):
            if npc.quest_key:
                q = self.quests.activate(npc.quest_key)
                if q:
                    self.show_message(f"Quest accepted: {q.title}")
                else:
                    self.show_message("No new quests right now.")

    # --- Inventory mouse interaction (drag & drop) ---------------------------
    def _inv_slot_rects(self):
        """Return list of (rect, index) for inventory grid slots."""
        rects = []
        cols = 6
        slot = 56
        pad = 8
        gx = SCREEN_WIDTH // 2 - (cols * (slot + pad)) // 2
        gy = 180
        for i in range(self.player.inventory.slots):
            r = i % cols
            c = i // cols
            rect = pygame.Rect(gx + r * (slot + pad), gy + c * (slot + pad),
                               slot, slot)
            rects.append((rect, i))
        return rects

    def _equip_slot_rects(self):
        """Return weapon/armor equipment slot rects."""
        slot = 56
        ex = SCREEN_WIDTH // 2 + 230
        rects = {
            "weapon": pygame.Rect(ex, 200, slot, slot),
            "armor": pygame.Rect(ex, 280, slot, slot),
        }
        return rects

    def _inventory_mouse_down(self, pos, button):
        # pick up an item for dragging (left click)
        if button == 1:
            for rect, idx in self._inv_slot_rects():
                if rect.collidepoint(pos) and \
                        self.player.inventory.items[idx] is not None:
                    self.drag_item = self.player.inventory.items[idx]
                    self.drag_from = ("inv", idx)
                    return
            for slot, rect in self._equip_slot_rects().items():
                if rect.collidepoint(pos) and \
                        self.player.inventory.equipment[slot] is not None:
                    self.drag_item = self.player.inventory.equipment[slot]
                    self.drag_from = ("equip", slot)
                    return
        # right click: use / equip item
        elif button == 3:
            for rect, idx in self._inv_slot_rects():
                if rect.collidepoint(pos) and \
                        self.player.inventory.items[idx] is not None:
                    self.player.use_item(idx, self)
                    return

    def _inventory_mouse_up(self, pos):
        if self.drag_item is None:
            return
        placed = False
        # drop into inventory slot
        for rect, idx in self._inv_slot_rects():
            if rect.collidepoint(pos):
                self._place_drag_into_inv(idx)
                placed = True
                break
        # drop into equipment slot
        if not placed:
            for slot, rect in self._equip_slot_rects().items():
                if rect.collidepoint(pos):
                    self._place_drag_into_equip(slot)
                    placed = True
                    break
        if not placed:
            # return item to original location
            self._return_drag()
        self.drag_item = None
        self.drag_from = None

    def _place_drag_into_inv(self, idx):
        inv = self.player.inventory
        src_type, src_loc = self.drag_from
        target = inv.items[idx]
        if src_type == "inv":
            inv.items[self.drag_from[1]], inv.items[idx] = target, self.drag_item
        else:  # from equipment
            # only allow if target slot empty or swap-compatible
            if target is None:
                inv.items[idx] = self.drag_item
                inv.equipment[src_loc] = None
            else:
                # swap if target is equippable of same slot type
                if self._fits_equip(target, src_loc):
                    inv.equipment[src_loc] = target
                    inv.items[idx] = self.drag_item
                else:
                    self._return_drag()

    def _place_drag_into_equip(self, slot):
        inv = self.player.inventory
        if not self._fits_equip(self.drag_item, slot):
            self._return_drag()
            return
        src_type, src_loc = self.drag_from
        current = inv.equipment[slot]
        inv.equipment[slot] = self.drag_item
        if src_type == "inv":
            inv.items[src_loc] = current
        else:
            inv.equipment[src_loc] = current

    def _fits_equip(self, item, slot):
        if item is None:
            return False
        if slot == "weapon":
            return item.type == "weapon"
        if slot == "armor":
            return item.type == "armor"
        return False

    def _return_drag(self):
        src_type, src_loc = self.drag_from
        if src_type == "inv":
            if self.player.inventory.items[src_loc] is None:
                self.player.inventory.items[src_loc] = self.drag_item
        else:
            if self.player.inventory.equipment[src_loc] is None:
                self.player.inventory.equipment[src_loc] = self.drag_item

    # --- Shop mouse interaction ----------------------------------------------
    def _shop_item_rects(self):
        rects = []
        if self.shop_npc is None:
            return rects
        if self.shop_mode == "buy":
            items = self.shop_npc.shop_items
            for i, key in enumerate(items):
                r = pygame.Rect(160, 170 + i * 46, 520, 40)
                rects.append((r, key, i))
        else:
            for i, it in enumerate(self.player.inventory.items):
                if it is not None and it.type != "quest":
                    r = pygame.Rect(160, 170 + len(rects) * 46, 520, 40)
                    rects.append((r, it.key, i))
        return rects

    def _shop_mouse_down(self, pos, button):
        # toggle buy/sell tabs
        buy_tab = pygame.Rect(160, 120, 120, 36)
        sell_tab = pygame.Rect(300, 120, 120, 36)
        if buy_tab.collidepoint(pos):
            self.shop_mode = "buy"
            return
        if sell_tab.collidepoint(pos):
            self.shop_mode = "sell"
            return
        for r, key, idx in self._shop_item_rects():
            if r.collidepoint(pos):
                if self.shop_mode == "buy":
                    self._buy_item(key)
                else:
                    self._sell_item(idx)
                return

    def _buy_item(self, key):
        data = ITEM_DB[key]
        price = data["value"]
        if self.player.gold >= price:
            if self.player.inventory.first_empty() == -1 and \
                    not data.get("stack", False):
                self.show_message("Inventory full!")
                return
            self.player.gold -= price
            self.player.inventory.add(key, 1)
            self.show_message(f"Bought {data['name']} for {price}g.")
            self.assets.play_sound("coin", os.path.join(ASSET_DIR, "coin.wav"),
                                   0.4)
        else:
            self.show_message("Not enough gold!")

    def _sell_item(self, idx):
        it = self.player.inventory.items[idx]
        if it is None:
            return
        price = max(1, it.value // 2)
        self.player.gold += price
        self.player.inventory.remove_at(idx, 1)
        self.show_message(f"Sold {it.name} for {price}g.")

    # --- Update ---------------------------------------------------------------
    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        # update hovered buttons regardless of state
        for blist in (self.menu_buttons, self.pause_buttons,
                      self.settings_buttons, self.gameover_buttons,
                      self.victory_buttons):
            for b in blist:
                b.update(mouse_pos)

        if self.message_timer > 0:
            self.message_timer -= 1

        if self.state != STATE_PLAY:
            # still animate NPCs/particles a touch in inventory/quest views
            self.particles.update()
            return

        keys = pygame.key.get_pressed()
        player = self.player

        if not player.alive:
            self.set_state(STATE_GAMEOVER)
            return

        # Player
        player.handle_input(keys, self)
        player.update(self)

        # Day/night
        self.daynight.update()

        # Camera
        self.camera.update(player)

        # Hazards under player
        for hz in self.world.hazard_rects_near(player.rect):
            if player.rect.colliderect(hz) and player.invuln <= 0:
                player.take_damage(12 * self.settings["difficulty"], self)
                player.vy = -8

        # Enemies
        for e in self.enemies:
            e.update(self)
            # hazard damage to enemies
            for hz in self.world.hazard_rects_near(e.rect):
                if e.rect.colliderect(hz):
                    e.hp -= 1
                    if e.hp <= 0 and e.alive:
                        e.die(self, None)
        self.enemies = [e for e in self.enemies if e.alive]

        # Bosses
        for b in self.bosses:
            b.update(self)
        self.bosses = [b for b in self.bosses if b.alive]

        # Projectiles
        self._update_projectiles()

        # Loot
        self._update_loot()

        # NPCs
        for npc in self.npcs:
            npc.update()

        # Floating texts
        self.floating_texts = [t for t in self.floating_texts if t.update()]

        # Particles
        self.particles.update()

        # Enemy streaming: respawn some enemies over time near player
        self._stream_enemies()

        # Hidden relic discovery
        if not self.relic_found and \
                player.rect.colliderect(self.world.relic_zone):
            self.relic_found = True
            self.player.inventory.add("ancient_relic", 1)
            self.quests.activate("hidden_relic")
            self.quests.on_event("find", target="relic", game=self)
            self.show_message("You found the Ancient Relic!")
            self.particles.emit(self.world.relic_zone.centerx,
                                self.world.relic_zone.centery, 40, GOLD,
                                spread=6, life=50, upward=True)

        # Quest auto-claim rewards when completed
        self._process_quest_rewards()

    def _update_projectiles(self):
        alive = []
        for p in self.projectiles:
            p.update()
            if not p.alive:
                continue
            # collide with world solids
            hit_wall = False
            for r in self.world.solid_rects_near(p.rect):
                if p.rect.colliderect(r):
                    hit_wall = True
                    break
            if hit_wall:
                self.particles.emit(p.x, p.y, 6, p.color, life=14)
                continue
            # collisions
            if p.owner == "player":
                hit = False
                for enemy in self.enemies + self.bosses:
                    if enemy.alive and p.rect.colliderect(enemy.rect):
                        enemy.take_damage(p.damage, self, crit=p.crit,
                                          source=self.player)
                        if p.effect:
                            self.player._apply_weapon_effect(enemy, p.effect)
                        hit = True
                        break
                if hit:
                    continue
            else:  # enemy projectile
                if self.player.rect.colliderect(p.rect):
                    self.player.take_damage(p.damage, self)
                    if p.effect:
                        if p.effect == "burn":
                            self.player.apply_status("burn", 90, 2)
                        elif p.effect == "freeze":
                            self.player.apply_status("freeze", 60)
                        elif p.effect == "poison":
                            self.player.apply_status("poison", 120, 2)
                        elif p.effect == "stun":
                            self.player.apply_status("stun", 40)
                    continue
            alive.append(p)
        self.projectiles = alive

    def _update_loot(self):
        remaining = []
        for l in self.loot:
            l.update(self)
            if l.life <= 0:
                continue
            if self.player.rect.colliderect(l.rect.inflate(12, 12)):
                # pick up
                if l.key == "coin":
                    self.player.gold += l.qty
                    self.quests.on_event("gold", amount=l.qty, game=self)
                    self.add_text(l.x, l.y - 6, f"+{l.qty}g", GOLD, size=18)
                    self.assets.play_sound("coin",
                                           os.path.join(ASSET_DIR, "coin.wav"),
                                           0.3)
                else:
                    leftover = self.player.inventory.add(l.key, l.qty)
                    if leftover > 0:
                        # inventory full; keep loot in world
                        remaining.append(l)
                        continue
                    self.add_text(l.x, l.y - 6, l.item.name, WHITE, size=16)
                continue
            remaining.append(l)
        self.loot = remaining

    def _stream_enemies(self):
        """Periodically spawn enemies from spawn points near the player."""
        self.spawn_cooldown -= 1
        if self.spawn_cooldown > 0:
            return
        self.spawn_cooldown = 180
        if len(self.enemies) > 40:
            return
        px = self.player.cx
        candidates = [sp for sp in self.world.spawn_points
                      if 700 < abs(sp[0] - px) < 1400]
        if candidates and random.random() < 0.7:
            sx, sy, kind = random.choice(candidates)
            self.enemies.append(Enemy(sx, sy, kind))

    def _process_quest_rewards(self):
        for q in self.quests.quests.values():
            if q.completed and not q.claimed:
                q.claimed = True
                self.player.gold += q.reward_gold
                if q.reward_xp:
                    self.player.gain_xp(q.reward_xp, self)
                for key, qty in q.reward_items:
                    self.player.inventory.add(key, qty)
                self.show_message(f"Reward claimed: {q.title} "
                                  f"(+{q.reward_gold}g)")

    # --- Drawing dispatch -----------------------------------------------------
    def draw(self):
        if self.state == STATE_MENU:
            self._draw_menu()
        elif self.state in (STATE_PLAY, STATE_INVENTORY, STATE_QUESTS,
                            STATE_DIALOGUE, STATE_SHOP, STATE_PAUSE):
            self._draw_world()
            if self.state == STATE_INVENTORY:
                self._draw_inventory()
            elif self.state == STATE_QUESTS:
                self._draw_quests()
            elif self.state == STATE_DIALOGUE:
                self._draw_dialogue()
            elif self.state == STATE_SHOP:
                self._draw_shop()
            elif self.state == STATE_PAUSE:
                self._draw_pause()
        elif self.state == STATE_SETTINGS:
            self._draw_world_or_menu_bg()
            self._draw_settings()
        elif self.state == STATE_GAMEOVER:
            self._draw_world()
            self._draw_gameover()
        elif self.state == STATE_VICTORY:
            self._draw_world()
            self._draw_victory()

        if self.settings["show_fps"]:
            fps = int(self.clock.get_fps())
            img = self.font_sm.render(f"FPS {fps}", True, WHITE)
            self.screen.blit(img, (SCREEN_WIDTH - 80, 8))

        pygame.display.flip()

    def _draw_world_or_menu_bg(self):
        if self.world is not None and self.player is not None:
            self._draw_world()
        else:
            self.screen.fill((20, 24, 40))

    # --- World rendering ------------------------------------------------------
    def _draw_world(self):
        if self.world is None:
            self.screen.fill(BLACK)
            return
        camx, camy = self.camera.offset
        player = self.player

        # Sky / background based on biome + day-night
        biome = self.world.biome_at(player.cx)
        base_sky = BIOME_COLORS.get(biome, (135, 206, 235))
        sky = self.daynight.sky_color(base_sky)
        self.screen.fill(sky)

        # Parallax background hills / stars
        self._draw_background(camx, camy, biome)

        # Night overlay tint for platforms
        darkness = self.daynight.darkness()
        tint = (0, 0, 30, darkness)

        # World platforms
        self.world.draw(self.screen, camx, camy, tint)

        # Checkpoints
        for cp in self.world.checkpoints:
            if abs(cp.rect.centerx - player.cx) < SCREEN_WIDTH:
                cp.draw(self.screen, camx, camy)

        # Relic marker (if not found)
        if not self.relic_found:
            rz = self.world.relic_zone
            if abs(rz.centerx - player.cx) < SCREEN_WIDTH:
                glow = (math.sin(self.frame_count * 0.1) + 1) / 2
                col = lerp_color(GOLD, WHITE, glow)
                pygame.draw.rect(self.screen, col,
                                 (rz.x - camx, rz.y - camy, rz.w, rz.h), 2)
                star = self.font_md.render("?", True, col)
                self.screen.blit(star, (rz.centerx - camx - 6, rz.centery -
                                        camy - 12))

        # Loot
        for l in self.loot:
            if abs(l.cx - player.cx) < SCREEN_WIDTH:
                l.draw(self.screen, camx, camy)

        # NPCs
        for npc in self.npcs:
            if abs(npc.cx - player.cx) < SCREEN_WIDTH:
                npc.draw(self.screen, camx, camy, player)

        # Enemies
        for e in self.enemies:
            if abs(e.cx - player.cx) < SCREEN_WIDTH + 100:
                e.draw(self.screen, camx, camy)

        # Bosses
        for b in self.bosses:
            if abs(b.cx - player.cx) < SCREEN_WIDTH + 200:
                b.draw(self.screen, camx, camy)

        # Projectiles
        for p in self.projectiles:
            p.draw(self.screen, camx, camy)

        # Player
        player.draw(self.screen, camx, camy)

        # Particles
        self.particles.draw(self.screen, camx, camy)

        # Floating texts
        for t in self.floating_texts:
            t.draw(self.screen, self.font_sm, camx, camy)

        # Apply a soft global night vignette
        if darkness > 0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                     pygame.SRCALPHA)
            overlay.fill((10, 12, 40, darkness))
            self.screen.blit(overlay, (0, 0))

        # HUD
        self._draw_hud()

    def _draw_background(self, camx, camy, biome):
        """Parallax hills, trees, dunes, or stars per biome."""
        darkness = self.daynight.darkness()
        # stars at night
        if darkness > 60:
            random.seed(42)
            for _ in range(60):
                sx = random.randint(0, SCREEN_WIDTH)
                sy = random.randint(0, SCREEN_HEIGHT // 2)
                b = random.randint(150, 255)
                self.screen.set_at((sx, sy), (b, b, b))
            random.seed()
            # moon
            pygame.draw.circle(self.screen, (230, 230, 210),
                               (SCREEN_WIDTH - 140, 90), 36)
        else:
            # sun
            sun_y = 80 + int(self.daynight.darkness() * 0.6)
            pygame.draw.circle(self.screen, (255, 240, 180),
                               (SCREEN_WIDTH - 140, sun_y), 40)

        # parallax hills (depend on biome)
        hill_color = lerp_color(BIOME_GROUND.get(biome, GREEN), (40, 40, 60),
                                darkness / 150.0)
        par = camx * 0.3
        for i in range(-1, SCREEN_WIDTH // 200 + 2):
            hx = i * 220 - (par % 220)
            base_y = 460
            pygame.draw.ellipse(self.screen, hill_color,
                                (hx, base_y, 260, 300))

    def _draw_hud(self):
        player = self.player
        # Bars
        draw_bar(self.screen, 16, 16, 220, 20,
                 player.hp / player.max_hp, RED,
                 label=f"HP {int(player.hp)}/{player.max_hp}",
                 font=self.font_sm)
        draw_bar(self.screen, 16, 42, 220, 16,
                 player.mana / player.max_mana, BLUE,
                 label=f"MP {int(player.mana)}", font=self.font_sm)
        draw_bar(self.screen, 16, 62, 220, 12,
                 player.stamina / player.max_stamina, GREEN)
        draw_bar(self.screen, 16, 78, 220, 10,
                 player.xp / player.xp_to_next, CYAN)

        # Level / gold
        lvl = self.font_sm.render(f"Lv {player.level}", True, WHITE)
        self.screen.blit(lvl, (16, 92))
        gold = self.font_sm.render(f"Gold: {player.gold}", True, GOLD)
        self.screen.blit(gold, (90, 92))

        # Weapon indicator
        wpn = player.inventory.equipment.get("weapon")
        wname = wpn.name if wpn else "Unarmed"
        wimg = self.font_sm.render(f"Weapon: {wname}", True, WHITE)
        self.screen.blit(wimg, (16, 112))

        # Time of day
        tod = self.font_sm.render(self.daynight.label(), True, WHITE)
        self.screen.blit(tod, (SCREEN_WIDTH - 80, 30))

        # Status effect icons
        sx = 16
        for st in player.statuses:
            col = {"poison": GREEN, "burn": ORANGE, "freeze": CYAN,
                   "stun": YELLOW}.get(st.kind, WHITE)
            pygame.draw.rect(self.screen, col, (sx, 132, 16, 16))
            sx += 20

        # Active boss health bar (if a boss is engaged & on screen)
        for b in self.bosses:
            if b.activated and abs(b.cx - player.cx) < SCREEN_WIDTH:
                self._draw_boss_bar(b)
                break

        # Mini objective tracker
        active = self.quests.active_quests()
        oy = 160
        track = [q for q in active if not q.completed][:3]
        if track:
            title = self.font_sm.render("Objectives:", True, YELLOW)
            self.screen.blit(title, (16, oy))
            oy += 20
            for q in track:
                txt = f"- {q.title} ({q.progress}/{q.target})"
                img = self.font_sm.render(txt, True, WHITE)
                self.screen.blit(img, (16, oy))
                oy += 18

        # Message banner
        if self.message_timer > 0:
            img = self.font_md.render(self.message, True, WHITE)
            bg = pygame.Surface((img.get_width() + 24, img.get_height() + 12),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            bx = SCREEN_WIDTH // 2 - bg.get_width() // 2
            self.screen.blit(bg, (bx, SCREEN_HEIGHT - 90))
            self.screen.blit(img, (bx + 12, SCREEN_HEIGHT - 84))

        # Controls hint
        hint = self.font_sm.render(
            "J:Sword K:Bow L:Magic  Space:Jump  Shift:Sprint  "
            "E:Interact  I:Inv  Q:Quests", True, WHITE)
        self.screen.blit(hint, (16, SCREEN_HEIGHT - 24))

    def _draw_boss_bar(self, boss):
        w = 500
        x = SCREEN_WIDTH // 2 - w // 2
        y = 30
        name = self.font_md.render(boss.name + f"  (Phase {boss.phase})",
                                   True, WHITE)
        self.screen.blit(name, (SCREEN_WIDTH // 2 - name.get_width() // 2,
                                y - 26))
        draw_bar(self.screen, x, y, w, 22, boss.hp / boss.max_hp,
                 (200, 50, 50))

    # --- Menu rendering -------------------------------------------------------
    def _draw_menu(self):
        # animated gradient background
        for y in range(0, SCREEN_HEIGHT, 4):
            t = y / SCREEN_HEIGHT
            col = lerp_color((20, 24, 60), (60, 30, 80), t)
            pygame.draw.rect(self.screen, col, (0, y, SCREEN_WIDTH, 4))

        # title
        title = self.font_xl.render("The Adventurer's Quest", True, GOLD)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 110))
        sub = self.font_md.render("A Pixel RPG Adventure", True, WHITE)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 190))

        # floating decorative particles
        if self.frame_count % 4 == 0:
            self.particles.emit(random.randint(0, SCREEN_WIDTH), 0, 1,
                                random.choice([GOLD, CYAN, PINK]), spread=1,
                                life=120, gravity=0.05)
        self.particles.update()
        # draw particles in screen space
        for p in self.particles.particles:
            p.draw(self.screen, 0, 0)

        for b in self.menu_buttons:
            b.draw(self.screen, self.font_md)

        tip = self.font_sm.render("Press Enter for New Game", True, WHITE)
        self.screen.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 560))

    def _draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        title = self.font_lg.render("PAUSED", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 160))
        for b in self.pause_buttons:
            b.draw(self.screen, self.font_md)

    def _draw_settings(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        title = self.font_lg.render("SETTINGS", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 120))

        cx = SCREEN_WIDTH // 2
        lines = [
            f"Music Volume: {int(self.settings['music_volume'] * 100)}%  "
            "(Left/Right)",
            f"SFX Volume: {int(self.settings['sfx_volume'] * 100)}%  (Up/Down)",
            f"Show FPS: {'On' if self.settings['show_fps'] else 'Off'}  "
            "(Press F)",
        ]
        y = 220
        for line in lines:
            img = self.font_md.render(line, True, WHITE)
            self.screen.blit(img, (cx - img.get_width() // 2, y))
            y += 50

        for b in self.settings_buttons:
            b.draw(self.screen, self.font_md)

    def _draw_gameover(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((40, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))
        title = self.font_xl.render("YOU DIED", True, RED)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 180))
        sub = self.font_md.render(
            f"Level {self.player.level}  -  Gold {self.player.gold}",
            True, WHITE)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 290))
        for b in self.gameover_buttons:
            b.draw(self.screen, self.font_md)

    def _draw_victory(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 30, 10, 190))
        self.screen.blit(overlay, (0, 0))
        # celebratory particles
        if self.frame_count % 3 == 0:
            self.particles.emit(random.randint(0, SCREEN_WIDTH),
                                random.randint(0, 100), 2,
                                random.choice([GOLD, CYAN, PINK, GREEN]),
                                spread=2, life=80, gravity=0.08)
        for p in self.particles.particles:
            p.draw(self.screen, 0, 0)

        title = self.font_xl.render("VICTORY!", True, GOLD)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 150))
        sub = self.font_md.render("All three bosses have fallen. The land "
                                  "is saved.", True, WHITE)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 270))
        stat = self.font_md.render(
            f"Final Level {self.player.level}  -  Gold {self.player.gold}",
            True, CYAN)
        self.screen.blit(stat, (SCREEN_WIDTH // 2 - stat.get_width() // 2, 320))
        for b in self.victory_buttons:
            b.draw(self.screen, self.font_md)

    # --- Inventory rendering --------------------------------------------------
    def _draw_inventory(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.font_lg.render("INVENTORY", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 110))

        mouse_pos = pygame.mouse.get_pos()
        hovered_item = None

        # inventory grid
        for rect, idx in self._inv_slot_rects():
            pygame.draw.rect(self.screen, DARK_GREY, rect, border_radius=4)
            pygame.draw.rect(self.screen, GREY, rect, 2, border_radius=4)
            it = self.player.inventory.items[idx]
            if it is not None and (self.drag_from != ("inv", idx) or
                                   self.drag_item is None):
                icon = it.icon(40)
                self.screen.blit(icon, (rect.x + 8, rect.y + 8))
                if it.stackable and it.qty > 1:
                    qimg = self.font_sm.render(str(it.qty), True, WHITE)
                    self.screen.blit(qimg, (rect.right - qimg.get_width() - 4,
                                            rect.bottom - 18))
                if rect.collidepoint(mouse_pos):
                    hovered_item = (it, rect)

        # equipment slots
        eq_labels = {"weapon": "Weapon", "armor": "Armor"}
        for slot, rect in self._equip_slot_rects().items():
            pygame.draw.rect(self.screen, (50, 50, 70), rect, border_radius=4)
            pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=4)
            lbl = self.font_sm.render(eq_labels[slot], True, WHITE)
            self.screen.blit(lbl, (rect.x, rect.y - 20))
            it = self.player.inventory.equipment[slot]
            if it is not None and self.drag_from != ("equip", slot):
                self.screen.blit(it.icon(40), (rect.x + 8, rect.y + 8))
                if rect.collidepoint(mouse_pos):
                    hovered_item = (it, rect)

        # equipped stats panel
        px = SCREEN_WIDTH // 2 + 210
        stats = [
            f"Attack: {self.player.attack_power}",
            f"Defense: {self.player.defense}",
            f"Level: {self.player.level}",
            f"Gold: {self.player.gold}",
        ]
        sy = 380
        for s in stats:
            img = self.font_sm.render(s, True, WHITE)
            self.screen.blit(img, (px, sy))
            sy += 22

        # instructions
        inst = self.font_sm.render(
            "Left-drag to move/equip. Right-click to use/equip. "
            "I or Esc to close.", True, WHITE)
        self.screen.blit(inst, (SCREEN_WIDTH // 2 - inst.get_width() // 2,
                                SCREEN_HEIGHT - 60))

        # dragged item follows cursor
        if self.drag_item is not None:
            self.screen.blit(self.drag_item.icon(40),
                             (mouse_pos[0] - 20, mouse_pos[1] - 20))

        # tooltip
        if hovered_item and self.drag_item is None:
            self._draw_tooltip(hovered_item[0], mouse_pos)

    def _draw_tooltip(self, item, pos):
        data = item.data
        lines = [item.name]
        if "atk" in data:
            lines.append(f"Attack +{data['atk']}")
        if "defense" in data:
            lines.append(f"Defense +{data['defense']}")
        if "heal" in data:
            lines.append(f"Heals {data['heal']} HP")
        if "mana" in data:
            lines.append(f"Restores {data['mana']} MP")
        if "stamina" in data:
            lines.append(f"Restores {data['stamina']} Stamina")
        if "effect" in data:
            lines.append(f"Effect: {data['effect'].title()}")
        lines.append(f"Value: {data.get('value', 0)}g")
        lines.append(data.get("desc", ""))

        w = max(self.font_sm.size(l)[0] for l in lines) + 16
        h = len(lines) * 20 + 12
        tx = clamp(pos[0] + 16, 0, SCREEN_WIDTH - w)
        ty = clamp(pos[1] + 16, 0, SCREEN_HEIGHT - h)
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((20, 20, 30, 235))
        self.screen.blit(bg, (tx, ty))
        pygame.draw.rect(self.screen, GOLD, (tx, ty, w, h), 1)
        yy = ty + 6
        for i, l in enumerate(lines):
            col = GOLD if i == 0 else WHITE
            img = self.font_sm.render(l, True, col)
            self.screen.blit(img, (tx + 8, yy))
            yy += 20

    # --- Quest log rendering --------------------------------------------------
    def _draw_quests(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        title = self.font_lg.render("QUEST LOG", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2,
                                 60))

        y = 130
        categories = [("main", "Main Quests", GOLD),
                      ("side", "Side Quests", CYAN),
                      ("hidden", "Hidden Quests", PURPLE)]
        for qtype, label, color in categories:
            header = self.font_md.render(label, True, color)
            self.screen.blit(header, (120, y))
            y += 32
            found = False
            for q in self.quests.quests.values():
                if q.qtype != qtype:
                    continue
                if q.hidden and not q.active and not q.completed:
                    continue  # don't reveal undiscovered hidden quests
                if not q.active and not q.completed:
                    continue
                found = True
                status = "[DONE]" if q.completed else \
                    f"[{q.progress}/{q.target}]"
                scol = GREEN if q.completed else WHITE
                line = f"{status} {q.title} - {q.desc}"
                img = self.font_sm.render(line, True, scol)
                self.screen.blit(img, (140, y))
                y += 22
                rew = (f"     Reward: {q.reward_gold}g, {q.reward_xp} XP")
                rimg = self.font_sm.render(rew, True, YELLOW)
                self.screen.blit(rimg, (140, y))
                y += 24
            if not found:
                img = self.font_sm.render("   (none active)", True, GREY)
                self.screen.blit(img, (140, y))
                y += 24
            y += 10

        inst = self.font_sm.render("Q or Esc to close", True, WHITE)
        self.screen.blit(inst, (SCREEN_WIDTH // 2 - inst.get_width() // 2,
                                SCREEN_HEIGHT - 40))

    # --- Dialogue rendering ---------------------------------------------------
    def _draw_dialogue(self):
        npc = self.active_npc
        if npc is None:
            return
        # dialogue box
        box_h = 150
        box = pygame.Surface((SCREEN_WIDTH - 80, box_h), pygame.SRCALPHA)
        box.fill((15, 15, 25, 230))
        self.screen.blit(box, (40, SCREEN_HEIGHT - box_h - 30))
        pygame.draw.rect(self.screen, GOLD,
                         (40, SCREEN_HEIGHT - box_h - 30,
                          SCREEN_WIDTH - 80, box_h), 2)

        name = self.font_md.render(npc.name, True, GOLD)
        self.screen.blit(name, (60, SCREEN_HEIGHT - box_h - 14))

        idx = min(self.dialogue_index, len(npc.dialogue) - 1)
        line = npc.dialogue[idx]
        img = self.font_md.render(line, True, WHITE)
        self.screen.blit(img, (60, SCREEN_HEIGHT - box_h + 20))

        prompt = self.font_sm.render("[E] Continue   [Esc] Leave", True,
                                     CYAN)
        self.screen.blit(prompt, (SCREEN_WIDTH - 260, SCREEN_HEIGHT - 50))

    # --- Shop rendering -------------------------------------------------------
    def _draw_shop(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        self.screen.blit(overlay, (0, 0))

        npc = self.shop_npc
        title = self.font_lg.render(
            f"{npc.name}'s Shop" if npc else "Shop", True, GOLD)
        self.screen.blit(title, (160, 60))
        gold = self.font_md.render(f"Your Gold: {self.player.gold}", True, GOLD)
        self.screen.blit(gold, (SCREEN_WIDTH - 320, 70))

        # tabs
        buy_tab = pygame.Rect(160, 120, 120, 36)
        sell_tab = pygame.Rect(300, 120, 120, 36)
        for tab, mode, label in ((buy_tab, "buy", "BUY"),
                                 (sell_tab, "sell", "SELL")):
            col = GREEN if self.shop_mode == mode else DARK_GREY
            pygame.draw.rect(self.screen, col, tab, border_radius=4)
            pygame.draw.rect(self.screen, WHITE, tab, 1, border_radius=4)
            img = self.font_sm.render(label, True, WHITE)
            self.screen.blit(img, (tab.centerx - img.get_width() // 2,
                                   tab.centery - img.get_height() // 2))

        mouse_pos = pygame.mouse.get_pos()
        for r, key, idx in self._shop_item_rects():
            hover = r.collidepoint(mouse_pos)
            bgc = (60, 60, 80) if hover else (35, 35, 50)
            pygame.draw.rect(self.screen, bgc, r, border_radius=4)
            data = ITEM_DB[key]
            icon = Item(key).icon(32)
            self.screen.blit(icon, (r.x + 6, r.y + 4))
            name = self.font_sm.render(data["name"], True, WHITE)
            self.screen.blit(name, (r.x + 46, r.y + 4))
            desc = self.font_sm.render(data.get("desc", ""), True, GREY)
            self.screen.blit(desc, (r.x + 46, r.y + 22))
            if self.shop_mode == "buy":
                price = data["value"]
                pcol = GOLD if self.player.gold >= price else RED
                ptxt = f"{price}g"
            else:
                price = max(1, data["value"] // 2)
                pcol = GREEN
                qty = self.player.inventory.items[idx].qty \
                    if self.player.inventory.items[idx] else 1
                ptxt = f"Sell {price}g (x{qty})"
            pimg = self.font_sm.render(ptxt, True, pcol)
            self.screen.blit(pimg, (r.right - pimg.get_width() - 8, r.y + 12))

        inst = self.font_sm.render(
            "Click item to buy/sell. Tab switches mode. Esc to leave.",
            True, WHITE)
        self.screen.blit(inst, (160, SCREEN_HEIGHT - 50))


# ------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    game = Game()
    game.run()


pygame.mixer.music.stop()
pygame.quit()