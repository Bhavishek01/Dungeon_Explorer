# ============================================================
# screens/pause_screen.py — equivalent of pausemenu.java
# ============================================================

import sys
import pygame as pg

import config
from ui import Button, draw_label


class PauseScreen:
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.title_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_TITLE, bold=True)
        self.label_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_LARGE, bold=True)

        cx = config.SCREEN_WIDTH // 2
        btn_w, btn_h, gap = 260, 50, 18
        start_y = 220

        labels_and_targets = [
            ("Resume", self._resume),
            ("Quit Game", self._quit_game),
        ]
        self.buttons = []
        for i, (label, callback) in enumerate(labels_and_targets):
            rect = (cx - btn_w // 2, start_y + i * (btn_h + gap), btn_w, btn_h)
            self.buttons.append(Button(rect, label, on_click=callback, font=self.label_font))

    def _resume(self):
        self.manager.switch_to(config.SCREEN_GAME, resumed=True)

    def _quit_game(self):
        self.client.discard_game_run(self.game_state)
        self.manager.switch_to(config.SCREEN_MENU)

    def on_enter(self, **kwargs):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        if event.type == pg.KEYDOWN and event.key in (pg.K_ESCAPE, pg.K_q):
            self._resume()
            return
        for btn in self.buttons:
            btn.handle_event(event)

    def update(self, dt):
        self.client.poll_events()

    def draw(self, surface):
        surface.fill(config.COLOR_BG)
        draw_label(surface, "Paused", (config.SCREEN_WIDTH // 2, 120),
                   font=self.title_font, color=config.COLOR_WHITE, center=True)
        for btn in self.buttons:
            btn.draw(surface)
