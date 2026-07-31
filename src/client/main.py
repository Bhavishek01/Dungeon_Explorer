import sys
import pygame as pg

import config
from session import ClientSession
from screens import ScreenManager
from screens.setup_screen import SetupScreen
from screens.menu_screen import MenuScreen
from screens.game_screen import GameScreen
from screens.inventory_screen import InventoryScreen
from screens.profile_screen import ProfileScreen
from screens.pause_screen import PauseScreen


class DungeonQuest:
    def __init__(self):
        pg.init()
        pg.display.set_caption(config.WINDOW_TITLE)

        self.screen = pg.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.clock = pg.time.Clock()
        self.running = True

        # Shared across every screen for the lifetime of the process.
        self.client = ClientSession()
        self.game_state = {
            "player_id": None,
            "player_name": None,
            "player_class": None,
            "items": [],
            "equipped": [0, 0, 0],
            "profile": {
                "level": 1,
                "monster_kills": {},
                "skill_usage": {},
            },
        }

        self.manager = ScreenManager(self.client, self.game_state)
        self.manager.register(config.SCREEN_SETUP, SetupScreen)
        self.manager.register(config.SCREEN_MENU, MenuScreen)
        self.manager.register(config.SCREEN_GAME, GameScreen)
        self.manager.register(config.SCREEN_INVENTORY, InventoryScreen)
        self.manager.register(config.SCREEN_PROFILE, ProfileScreen)
        self.manager.register(config.SCREEN_PAUSE, PauseScreen)

        self.manager.switch_to(config.SCREEN_SETUP)

    def run(self):
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    self.running = False
                    continue
                self.manager.handle_event(event)

            self.manager.update(dt)
            self.manager.draw(self.screen)
            pg.display.flip()

        self.client.disconnect()
        pg.quit()
        sys.exit()


def main():
    game = DungeonQuest()
    game.run()


if __name__ == "__main__":
    main()