# ============================================================
# config.py — central constants for the client
# Anything a screen or entity needs to know "by convention"
# lives here so we never hardcode magic numbers in screens/.
# ============================================================

# ---------------- Window / loop ----------------
TILE_SIZE = 48
SCREEN_WIDTH = 16 * TILE_SIZE   # 768
SCREEN_HEIGHT = 12 * TILE_SIZE  # 576
FPS = 60
WINDOW_TITLE = "Dungeon Quest"

# ---------------- Tile types (mirrors shared/tilemap.py) ----------------
TILE_WALL = 0
TILE_STONE = 1
TILE_GROUND = 2
TILE_WATER = 3
TILE_TREASURE = 4   # reserved: treasure chest marker in the generated map

# ---------------- Screen / state identifiers ----------------
# These are the keys the ScreenManager (screens/__init__.py) switches between.
# Equivalent to the string names used with Java's CardLayout.show(cardPanel, "x").
SCREEN_SETUP = "setup"
SCREEN_MENU = "menu"
SCREEN_GAME = "game"
SCREEN_INVENTORY = "inventory"
SCREEN_PROFILE = "profile"
SCREEN_PAUSE = "pause"

# ---------------- Colors ----------------
COLOR_BG = (10, 10, 18)
COLOR_PANEL = (24, 24, 40)
COLOR_PANEL_BORDER = (90, 90, 160)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_CYAN = (0, 255, 255)
COLOR_YELLOW = (255, 220, 0)
COLOR_RED = (220, 60, 60)
COLOR_GREEN = (60, 200, 90)
COLOR_GRAY = (140, 140, 140)
COLOR_LIGHT_GRAY = (200, 200, 200)

BUTTON_COLOR = (35, 35, 60)
BUTTON_HOVER_COLOR = (55, 55, 95)
BUTTON_DISABLED_COLOR = (30, 30, 30)
BUTTON_BORDER_COLOR = COLOR_CYAN
BUTTON_TEXT_COLOR = COLOR_WHITE

INPUT_BG_COLOR = COLOR_WHITE
INPUT_TEXT_COLOR = COLOR_BLACK
INPUT_ACTIVE_BORDER = COLOR_CYAN
INPUT_INACTIVE_BORDER = COLOR_GRAY

# ---------------- Fonts (sizes only; Font objects are built after pg.init()) ----------------
FONT_NAME = "Arial"
FONT_SIZE_TITLE = 44
FONT_SIZE_LARGE = 28
FONT_SIZE_MEDIUM = 20
FONT_SIZE_SMALL = 16

# ---------------- Local persistence ----------------
PROFILE_STORE_FILE = "data/profiles.json"

# ---------------- Assets ----------------
ASSET_DIR = "assets"

# ---------------- Player defaults (base, class-agnostic) ----------------
PLAYER_START_X = 96
PLAYER_START_Y = 96
PLAYER_DEFAULT_LIFE = 300
PLAYER_DEFAULT_SPEED = 3
PLAYER_DEFAULT_STAMINA = 200
PLAYER_DEFAULT_MANA = 200
PLAYER_DEFAULT_POWER = 100
PLAYER_DEFAULT_LIFE_REGEN_RATE = 0.1     # per second
PLAYER_DEFAULT_STAMINA_REGEN_RATE = 0.1  # per second
PLAYER_DEFAULT_MANA_REGEN_RATE = 0.1     # per second
PLAYER_DEFAULT_POWER_REGEN_RATE = 0.1    # per second
PLAYER_DEFAULT_ATTACK_RANGE = 75

# Walk/run: Shift+WASD run multiplier (per project plan)
PLAYER_WALK_SPEED_MULTIPLIER = 1.0
PLAYER_RUN_SPEED_MULTIPLIER = 1.8
PLAYER_RUN_STAMINA_DRAIN_PER_SEC = 8

# ---------------- Per-class stat tables ----------------
# One dict per selectable class. class_select_screen.py reads this directly
# so adding a class later means adding one entry here, not touching a screen.
PLAYER_CLASSES = {
    "mage": {
        "label": "Mage",
        "description": "High mana, ranged spell damage, fragile up close.",
        "life": 300,
        "speed": 2.5,
        "stamina": 100,
        "mana": 250,
        "power": 90,
        "attack_range": 75,
    },
    "melee": {
        "label": "Melee",
        "description": "High life and stamina, strong close-range power.",
        "life": 500,
        "speed": 3.0,
        "stamina": 350,
        "mana": 50,
        "power": 200,
        "attack_range": 40,
    },
    "fighter": {
        "label": "Fighter",
        "description": "Balanced melee/caster hybrid. Combined variant.",
        "life": 450,
        "speed": 3.0,
        "stamina": 250,
        "mana": 150,
        "power": 200,
        "attack_range": 50,
    },
    "archer": {
        "label": "Archer",
        "description": "Optional class. Fast, ranged, low power per hit.",
        "life": 350,
        "speed": 3.5,
        "stamina": 200,
        "mana": 50,
        "power": 150,
        "attack_range": 100,
    },
}
DEFAULT_CLASS = "melee"

# ---------------- Monster defaults ----------------
MONSTER_DEFAULT_LIFE = 500
MONSTER_DEFAULT_SPEED = 2.2
MONSTER_ATTACK_RANGE = 150
MONSTER_CHASE_RANGE = 250
MONSTER_ATTACK_SPEED = 7.0

# ---------------- Projectile defaults ----------------
PROJECTILE_SPEED = 8.0
PROJECTILE_MAX_DISTANCE = 500
FIRE_COOLDOWN_MS = 250
