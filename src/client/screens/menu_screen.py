# ============================================================
# screens/menu_screen.py — equivalent of gamemenu.java
# Adds Profile (not in the Java version) per the project plan.
# ============================================================

import sys
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

        cx = config.SCREEN_WIDTH // 2
        btn_w, btn_h, gap = 280, 54, 18
        start_y = 220

        labels_and_targets = [
            ("Start Game", self._start_game),
            ("Inventory", lambda: self.manager.switch_to(config.SCREEN_INVENTORY)),
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
        self.game_state.update(self.client.get_active_profile_snapshot())

    def draw(self, surface):
        surface.fill(config.COLOR_BG)

        name = self.game_state.get("player_name", "?")
        pid = self.game_state.get("player_id", "?")
        draw_label(surface, f"Player: {name}", (20, 20), font=self.small_font, color=config.COLOR_WHITE)
        draw_label(surface, f"ID: {pid}", (config.SCREEN_WIDTH - 20, 20),
                   font=self.small_font, color=config.COLOR_WHITE)

        draw_label(surface, "Dungeon Quest", (config.SCREEN_WIDTH // 2, 120),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        for btn in self.buttons:
            btn.draw(surface)
