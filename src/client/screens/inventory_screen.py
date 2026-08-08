# ============================================================
# screens/inventory_screen.py — equivalent of inventory.java
#
# Reads game_state["items"] (list of {"id","name","quantity"}) and
# game_state["equipped"] (list of 3 item ids, 0 = empty slot).
# This is fully local now; the session saves and restores the data.
# ============================================================

import sys
import pygame as pg

import config
from ui import Button, draw_label


class InventoryScreen:
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.title_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_LARGE, bold=True)
        self.label_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_MEDIUM)
        self.small_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)

        self.resume_button = Button(
            (config.SCREEN_WIDTH // 2 - 130, config.SCREEN_HEIGHT - 70, 260, 46),
            "Resume", on_click=lambda: self.manager.switch_to(config.SCREEN_GAME, resumed=True),
            font=self.label_font)

        self.slot_rects = [pg.Rect(60 + i * 170, 60, 150, 130) for i in range(3)]
        self.item_row_height = 56
        self.list_top = 230

    def on_enter(self, **kwargs):
        self.game_state.update(self.client.get_active_profile_snapshot())

    def on_exit(self):
        pass

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        self.resume_button.handle_event(event)

    def update(self, dt):
        self.client.poll_events()

    def draw(self, surface):
        surface.fill(config.COLOR_BG)
        draw_label(surface, "Inventory", (config.SCREEN_WIDTH // 2, 24),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        # Equipped slots
        equipped = self.game_state.get("equipped", [0, 0, 0])
        items_by_id = {item["id"]: item for item in self.game_state.get("items", [])}
        for i, rect in enumerate(self.slot_rects):
            pg.draw.rect(surface, config.COLOR_PANEL, rect, border_radius=8)
            pg.draw.rect(surface, config.COLOR_CYAN, rect, width=2, border_radius=8)
            item_id = equipped[i] if i < len(equipped) else 0
            if item_id:
                label = items_by_id.get(item_id, {}).get("name", f"#{item_id}")
                draw_label(surface, label, rect.center, font=self.small_font,
                           color=config.COLOR_WHITE, center=True)
            else:
                draw_label(surface, "Empty", rect.center, font=self.small_font,
                           color=config.COLOR_GRAY, center=True)

        # Item list
        items = self.game_state.get("items", [])
        if not items:
            draw_label(surface, "No items yet.", (60, self.list_top),
                       font=self.small_font, color=config.COLOR_GRAY)
        else:
            for i, item in enumerate(items):
                y = self.list_top + i * self.item_row_height
                row_rect = pg.Rect(60, y, config.SCREEN_WIDTH - 120, self.item_row_height - 8)
                pg.draw.rect(surface, config.COLOR_PANEL, row_rect, border_radius=6)
                pg.draw.rect(surface, config.COLOR_PANEL_BORDER, row_rect, width=1, border_radius=6)
                draw_label(surface, item.get("name", "?"), (row_rect.x + 16, row_rect.y + 14),
                           font=self.label_font, color=config.COLOR_YELLOW)
                draw_label(surface, f"x{item.get('quantity', 0)}",
                           (row_rect.right - 60, row_rect.y + 16),
                           font=self.small_font, color=config.COLOR_WHITE)

        self.resume_button.draw(surface)
