# ============================================================
# screens/profile_screen.py
#
# New screen (no Java equivalent). Shows the player their own local
# history: level, class, most/least killed monster, most used skill.
#
# Expects game_state["profile"] = {
#     "level": int, "player_class": str,
#     "experience": int, "experience_required": int,
#     "monster_kills": {monster_name: count, ...},
#     "items_used": {item_name: count, ...},
# }
# Falls back to placeholders if the profile is still empty.
# ============================================================

import sys
import pygame as pg

import config
from ui import Button, draw_label


class ProfileScreen:
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.title_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_LARGE, bold=True)
        self.label_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_MEDIUM, bold=True)
        self.body_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)

        self.back_button = Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 70, 260, 46),
            "Back to Menu", on_click=lambda: self.manager.switch_to(config.SCREEN_MENU),
            font=self.label_font)

    def on_enter(self, **kwargs):
        self.game_state.update(self.client.get_active_profile_snapshot())

    def on_exit(self):
        pass

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        self.back_button.handle_event(event)
        if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
            self.manager.switch_to(config.SCREEN_MENU)

    def update(self, dt):
        self.client.poll_events()

    def draw(self, surface):
        surface.fill(config.COLOR_BG)
        draw_label(surface, "Profile", (config.SCREEN_WIDTH // 2, 24),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        profile = self.game_state.get("profile", {})
        name = self.game_state.get("player_name", "?")
        pid = self.game_state.get("player_id", "?")
        level = profile.get("level", 1)
        experience = profile.get("experience", 0)
        experience_required = profile.get("experience_required", config.PLAYER_INITIAL_EXPERIENCE_REQUIRED)
        total_games = int(profile.get("total_games_played", 0))
        games_cleared = int(profile.get("games_cleared", 0))

        col_x = 60
        y = 90
        line_gap = 26

        for text in [
            f"Explorer Name: {name}",
            f"id: {pid}",
            f"Level: {level}",
            f"XP: {experience}/{experience_required}",
            f"Games Played: {total_games}",
            f"Games Cleared: {games_cleared}",
        ]:
            draw_label(surface, text, (col_x, y), font=self.body_font, color=config.COLOR_WHITE)
            y += line_gap

        y += 20
        draw_label(surface, "Monster Kills", (col_x, y), font=self.label_font, color=config.COLOR_YELLOW)
        y += line_gap
        monster_kills = profile.get("monster_kills", {})
        if monster_kills:
            for monster_name, count in sorted(monster_kills.items(), key=lambda kv: -kv[1]):
                draw_label(surface, f"{monster_name}: {count}", (col_x + 10, y),
                           font=self.body_font, color=config.COLOR_LIGHT_GRAY)
                y += 20
        else:
            draw_label(surface, "No data yet.", (col_x + 10, y),
                       font=self.body_font, color=config.COLOR_GRAY)

        history_x = config.SCREEN_WIDTH // 2 + 20
        history_y = 90
        draw_label(surface, "Last Five Games", (history_x, history_y),
                   font=self.label_font, color=config.COLOR_YELLOW)
        history_y += line_gap
        recent_games = profile.get("last_five_games", [])
        if recent_games:
            for index, game in enumerate(reversed(recent_games[-5:]), start=1):
                result = "CLEARED" if game.get("cleared", False) else "LOST"
                killed = int(game.get("monsters_killed", 0))
                items = game.get("items", [])
                item_text = ", ".join(str(item) for item in items) if items else "none"
                draw_label(surface, f"{index}. {result} | Kills: {killed}",
                           (history_x, history_y), font=self.body_font, color=config.COLOR_LIGHT_GRAY)
                history_y += 19
                draw_label(surface, f"Items: {item_text[:36]}",
                           (history_x + 12, history_y), font=self.body_font, color=config.COLOR_GRAY)
                history_y += 24
        else:
            draw_label(surface, "No games yet.", (history_x, history_y),
                       font=self.body_font, color=config.COLOR_GRAY)
            y += 20

        y += 20
        draw_label(surface, "Items Used", (col_x, y), font=self.label_font, color=config.COLOR_YELLOW)
        y += line_gap
        items_used = profile.get("items_used", {})
        if items_used:
            for item_name, count in sorted(items_used.items(), key=lambda kv: -kv[1]):
                draw_label(surface, f"{item_name}: {count}", (col_x + 10, y),
                           font=self.body_font, color=config.COLOR_LIGHT_GRAY)
                y += 20
        else:
            draw_label(surface, "No data yet.", (col_x + 10, y),
                       font=self.body_font, color=config.COLOR_GRAY)

        self.back_button.draw(surface)
