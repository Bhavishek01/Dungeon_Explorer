import sys

import pygame as pg

import config
from screens.inventory_screen import InventoryScreen
from ui import Button


class MenuInventoryScreen(InventoryScreen):
    def __init__(self, manager, client, game_state):
        super().__init__(manager, client, game_state)
        self.resume_button = self._menu_button()
        self.back_button = None
        self.allow_item_use = False
        self.show_equipped = False

    def _menu_button(self):
        return Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 70, 260, 46),
            "Back to Menu",
            on_click=lambda: self.manager.switch_to(config.SCREEN_MENU),
            font=self.label_font,
        )

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        self.resume_button.handle_event(event)
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.manager.switch_to(config.SCREEN_MENU)
