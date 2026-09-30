# ============================================================
# screens/profile_screen.py
#
# New screen (no Java equivalent). Shows the player their own local
# history: level, class, most/least killed monster, most used skill.
#
# Expects game_state["profile"] = {
#     "level": int, "player_class": str,
#     "monster_kills": {monster_name: count, ...},
#     "skill_usage": {skill_name: count, ...},
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

    def update(self, dt):
        self.client.poll_events()

    def draw(self, surface):
        surface.fill(config.COLOR_BG)
        draw_label(surface, "Profile", (config.SCREEN_WIDTH // 2, 24),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        profile = self.game_state.get("profile", {})
        name = self.game_state.get("player_name", "?")
        pid = self.game_state.get("player_id", "?")
        pclass = self.game_state.get("player_class", "?")
        level = profile.get("level", 1)

        col_x = 60
        y = 90
        line_gap = 26

        for text in [
            f"Explorer Name: {name}",
            f"id: {pid}",
            f"Class: {config.PLAYER_CLASSES.get(pclass, {}).get('label', pclass)}",
            f"Level: {level}",
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
            y += 20

        y += 20
        draw_label(surface, "Skill Usage", (col_x, y), font=self.label_font, color=config.COLOR_YELLOW)
        y += line_gap
        skill_usage = profile.get("skill_usage", {})
        if skill_usage:
            for skill_name, count in sorted(skill_usage.items(), key=lambda kv: -kv[1]):
                draw_label(surface, f"{skill_name}: {count}", (col_x + 10, y),
                           font=self.body_font, color=config.COLOR_LIGHT_GRAY)
                y += 20
        else:
            draw_label(surface, "No data yet.", (col_x + 10, y),
                       font=self.body_font, color=config.COLOR_GRAY)

        self.back_button.draw(surface)
