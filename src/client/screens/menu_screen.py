# ============================================================
# screens/menu_screen.py — equivalent of gamemenu.java
# Adds Profile (not in the Java version) per the project plan.
# ============================================================

import sys
from pathlib import Path

import pygame as pg

import config
from ui import Button, draw_label


class MenuScreen:
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.title_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_TITLE, bold=True)
        self.label_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_LARGE, bold=True)
        self.small_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)
        self.background_elapsed = 0.0
        tiles_root = Path(__file__).resolve().parents[2] / "shared" / "tiles"
        environment_root = tiles_root / "environment"
        monster_root = tiles_root / "monster"
        self.background_floor = self._load_background_image(environment_root / "floor1.png", (96, 96))
        self.background_lava = self._load_background_image(environment_root / "lava.png", (150, 90))
        self.background_water = self._load_background_image(environment_root / "water.png", (150, 90))
        self.background_lava_fountain = self._load_background_image(environment_root / "lava_fountain.png", (132, 132))
        self.background_water_fountain = self._load_background_image(environment_root / "water_fountain.png", (132, 132))
        self.background_traps = [
            self._load_background_image(environment_root / f"trap{index}.png", (74, 74))
            for index in range(1, 4)
        ]
        self.background_monsters = [
            self._load_background_image(monster_root / f"monster{index}_move1.png", (128, 128))
            for index in range(1, 4)
        ]

        cx = config.SCREEN_WIDTH // 2
        btn_w, btn_h, gap = 280, 54, 18
        start_y = 220

        labels_and_targets = [
            ("Start Game", self._start_game),
            ("Inventory", lambda: self.manager.switch_to(config.SCREEN_MENU_INVENTORY)),
            ("Profile", lambda: self.manager.switch_to(config.SCREEN_PROFILE)),
            ("Exit", lambda: sys.exit(0)),
        ]

        self.buttons = []
        for i, (label, callback) in enumerate(labels_and_targets):
            rect = (cx - btn_w // 2, start_y + i * (btn_h + gap), btn_w, btn_h)
            self.buttons.append(Button(rect, label, on_click=callback, font=self.label_font))

    def _start_game(self):
        if not self.game_state.get("player_class"):
            self.game_state["player_class"] = config.DEFAULT_CLASS
        self.manager.switch_to(config.SCREEN_GAME)

    def on_enter(self, **kwargs):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt):
        self.background_elapsed += dt
        self.game_state.update(self.client.get_active_profile_snapshot())

    def draw(self, surface):
        self._draw_background(surface)

        name = self.game_state.get("player_name", "?")
        pid = self.game_state.get("player_id", "?")
        level = self.game_state.get("profile", {}).get("level", 1)
        name_rect = draw_label(surface, f"Explorer: {name}", (20, 20), font=self.small_font, color=config.COLOR_WHITE)
        explorer_id = f"id: {pid}"
        id_width = self.small_font.size(explorer_id)[0]
        draw_label(surface, explorer_id, (config.SCREEN_WIDTH - 20 - id_width, 20),
               font=self.small_font, color=config.COLOR_YELLOW)
        draw_label(surface, f"lv {level}",
               (config.SCREEN_WIDTH // 2, name_rect.bottom - self.small_font.get_height() / 2),
               font=self.small_font, color=config.COLOR_YELLOW, center=True)
        draw_label(surface, "Dungeon Exploration", (config.SCREEN_WIDTH // 2, 125),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        for btn in self.buttons:
            btn.draw(surface)

    def _load_background_image(self, path, size):
        try:
            image = pg.image.load(str(path)).convert_alpha()
        except (OSError, pg.error):
            image = pg.Surface(size, pg.SRCALPHA)
        return pg.transform.smoothscale(image, size)

    def _draw_background(self, surface):
        for y in range(0, config.SCREEN_HEIGHT, self.background_floor.get_height()):
            for x in range(0, config.SCREEN_WIDTH, self.background_floor.get_width()):
                surface.blit(self.background_floor, (x, y))

        for x in range(-20, config.SCREEN_WIDTH + 20, 150):
            surface.blit(self.background_lava, (x, config.SCREEN_HEIGHT - 100))
            surface.blit(self.background_water, (x + 72, 70))

        surface.blit(self.background_lava_fountain, (24, 82))
        surface.blit(self.background_water_fountain, (config.SCREEN_WIDTH - 156, 78))

        trap_index = int(self.background_elapsed * 5) % len(self.background_traps)
        for position in ((70, 300), (config.SCREEN_WIDTH - 142, 300), (326, 480)):
            surface.blit(self.background_traps[trap_index], position)

        for image, position in zip(
            self.background_monsters,
            ((30, 410), (config.SCREEN_WIDTH - 158, 408), (config.SCREEN_WIDTH // 2 - 64, 60)),
        ):
            surface.blit(image, position)

        overlay = pg.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((5, 8, 18, 158))
        surface.blit(overlay, (0, 0))
