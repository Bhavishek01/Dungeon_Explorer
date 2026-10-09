import sys
import pygame as pg

import config
from gameplay.inventory import starter_items
from ui import Button, TextInput, draw_label
from screens.menu_screen import MenuScreen


class SetupScreen:
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state
        self.menu_background = MenuScreen(manager, client, game_state)

        self.title_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_TITLE, bold=True)
        self.label_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_MEDIUM)
        self.small_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)

        self.mode = "pick"
        self.name_input = TextInput(
            (config.SCREEN_WIDTH // 2 - 150, 290, 300, 44),
            font=self.label_font,
            placeholder="Explorer name",
            on_submit=self._create_player,
        )
        self.create_button = Button(
            (config.SCREEN_WIDTH // 2 - 130, 350, 260, 44),
            "Create Explorer",
            on_click=lambda: self._create_player(self.name_input.text),
            font=self.label_font,
        )
        self.new_player_button = Button(
            (config.SCREEN_WIDTH // 2 - 130, 410, 260, 44),
            "New Explorer",
            on_click=self._switch_to_create,
            font=self.label_font,
        )

        self.player_buttons = []
        self.status_message = ""
        self.status_color = config.COLOR_GRAY

    def on_enter(self, **kwargs):
        self._rebuild_player_buttons()
        self.status_message = ""
        self.status_color = config.COLOR_GRAY
        player_count = len(self.client.list_players())
        if player_count == 1:
            self._choose_player(self.client.list_players()[0]["player_id"])
        elif player_count > 1:
            self.mode = "pick"
        else:
            self.mode = "create"
            self.name_input.text = ""
            self.name_input.active = True

    def on_exit(self):
        pass

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)

        if self.mode == "pick":
            for button in self.player_buttons:
                button.handle_event(event)
            self.new_player_button.handle_event(event)
        else:
            self.name_input.handle_event(event)
            self.create_button.handle_event(event)

    def update(self, dt):
        self.menu_background.background_elapsed += dt
        if self.mode == "create":
            self.name_input.update(dt)

    def draw(self, surface):
        self.menu_background._draw_background(surface)
        draw_label(surface, "Dungeon Exploration", (config.SCREEN_WIDTH // 2, 100),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        if self.mode == "pick":
            draw_label(surface, "Choose an explorer profile", (config.SCREEN_WIDTH // 2, 170),
                       font=self.label_font, color=config.COLOR_WHITE, center=True)
            for button in self.player_buttons:
                button.draw(surface)
            self.new_player_button.draw(surface)
        else:
            draw_label(surface, "Create your first explorer", (config.SCREEN_WIDTH // 2, 200),
                       font=self.label_font, color=config.COLOR_WHITE, center=True)
            self.name_input.draw(surface)
            self.create_button.draw(surface)

        if self.status_message:
            draw_label(surface, self.status_message, (config.SCREEN_WIDTH // 2, 470),
                       font=self.small_font, color=self.status_color, center=True)

    def _switch_to_create(self):
        self.mode = "create"
        self.status_message = ""
        self.name_input.text = ""
        self.name_input.active = True

    def _create_player(self, player_name):
        player_name = player_name.strip()
        if not player_name:
            self.status_message = "Type a name first."
            self.status_color = config.COLOR_RED
            return

        self.client.register(player_name)
        snapshot = self.client.get_active_profile_snapshot()
        self._apply_profile(snapshot)

    def _choose_player(self, player_id):
        if not self.client.select_player(player_id):
            self.status_message = "Could not load that profile."
            self.status_color = config.COLOR_RED
            return

        snapshot = self.client.get_active_profile_snapshot()
        self._apply_profile(snapshot)

    def _apply_profile(self, snapshot):
        self.game_state["player_id"] = snapshot.get("player_id")
        self.game_state["player_name"] = snapshot.get("player_name")
        self.game_state["player_class"] = snapshot.get("player_class") or config.DEFAULT_CLASS
        self.game_state["items"] = snapshot.get("items") or starter_items()
        self.game_state["equipped"] = snapshot.get("equipped", [0, 0, 0])
        self.game_state["profile"] = snapshot.get("profile", self.game_state.get("profile", {}))
        self.manager.switch_to(config.SCREEN_MENU)

    def _rebuild_player_buttons(self):
        self.player_buttons = []
        players = self.client.list_players()
        btn_w, btn_h, gap = 320, 48, 14
        start_y = 220
        cx = config.SCREEN_WIDTH // 2

        for index, player in enumerate(players):
            rect = (cx - btn_w // 2, start_y + index * (btn_h + gap), btn_w, btn_h)
            label = f"{player['player_name']}  [{player['player_id']}]"
            self.player_buttons.append(
                Button(rect, label, on_click=lambda pid=player["player_id"]: self._choose_player(pid), font=self.small_font)
            )