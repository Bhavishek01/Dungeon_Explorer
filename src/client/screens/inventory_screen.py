# ============================================================
# screens/inventory_screen.py — equivalent of inventory.java
#
# Reads game_state["items"] (list of {"id","name","quantity"}) and
# game_state["equipped"] (list of 3 item ids, 0 = empty slot).
# This is fully local now; the session saves and restores the data.
# ============================================================

import sys
from pathlib import Path

import pygame as pg

import config
from shared.mapgen import ITEM_ROOT
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
        self.back_button = None
        self.use_buttons = []
        self.allow_item_use = True
        self.show_equipped = False
        self.item_scroll = 0
        self.visible_item_rows = 7
        self.item_images = {}
        self.item_asset_names = {
            "key": "key.png",
            "door_key": "door_key.png",
            "health_gradual": "health +250 gradually.png",
            "stamina_gradual": "stamina +50 gradually.png",
            "stamina_50": "stamina +50 gradually.png",
            "health_50": "health 50.png",
            "health_full": "health full.png",
            "stamina_full": "stamina full.png",
            "stamina_250": "stamina +250.png",
            "coins": "coins.png",
            "bow": "bow gun.png",
            "light": "light.png",
            "debuff": "debuff.png",
        }

        self.slot_rects = [pg.Rect(60 + i * 170, 60, 150, 130) for i in range(3)]
        self.item_row_height = 56
        self.list_top = 80

    def on_enter(self, **kwargs):
        self.game_state.update(self.client.get_active_profile_snapshot())
        self._rebuild_use_buttons()

    def on_exit(self):
        pass

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        if event.type == pg.MOUSEWHEEL:
            self.item_scroll = max(0, min(self._max_item_scroll(), self.item_scroll - event.y))
        self.resume_button.handle_event(event)
        if self.allow_item_use:
            for _, button in self.use_buttons:
                button.handle_event(event)
        if event.type == pg.KEYDOWN and event.key == pg.K_e:
            self.manager.switch_to(config.SCREEN_GAME, resumed=True)

    def update(self, dt):
        self.client.poll_events()
        self.item_scroll = min(self.item_scroll, self._max_item_scroll())
        self._rebuild_use_buttons()

    def draw(self, surface):
        surface.fill(config.COLOR_BG)
        draw_label(surface, "Inventory", (config.SCREEN_WIDTH // 2, 24),
                   font=self.title_font, color=config.COLOR_CYAN, center=True)

        if self.show_equipped:
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
            self.item_scroll = min(self.item_scroll, self._max_item_scroll(items))
            visible_items = items[self.item_scroll:self.item_scroll + self.visible_item_rows]
            for i, item in enumerate(visible_items):
                y = self.list_top + i * self.item_row_height
                row_rect = pg.Rect(60, y, config.SCREEN_WIDTH - 120, self.item_row_height - 8)
                pg.draw.rect(surface, config.COLOR_PANEL, row_rect, border_radius=6)
                pg.draw.rect(surface, config.COLOR_PANEL_BORDER, row_rect, width=1, border_radius=6)
                image = self._item_image(item.get("id"))
                if image is not None:
                    surface.blit(image, (row_rect.x + 10, row_rect.y + 5))
                draw_label(surface, item.get("name", "?"), (row_rect.x + 58, row_rect.y + 14),
                           font=self.label_font, color=config.COLOR_YELLOW)
                draw_label(surface, f"Qty: {item.get('quantity', 0)}",
                           (row_rect.right - 190, row_rect.y + 16),
                           font=self.small_font, color=config.COLOR_WHITE)
                if self.allow_item_use:
                    for item_id, button in self.use_buttons:
                        if item_id == item.get("id"):
                            button.rect.y = row_rect.y + 7
                            button.draw(surface)
                            break

        self.resume_button.draw(surface)
        if self.back_button is not None:
            self.back_button.draw(surface)

        if self._max_item_scroll(items) > 0:
            draw_label(
                surface,
                f"Items {self.item_scroll + 1}-{min(len(items), self.item_scroll + self.visible_item_rows)} of {len(items)}",
                (config.SCREEN_WIDTH // 2, self.list_top - 22),
                font=self.small_font,
                color=config.COLOR_GRAY,
                center=True,
            )

    def _rebuild_use_buttons(self):
        self.use_buttons = []
        if not self.allow_item_use:
            return
        for item in self.game_state.get("items", []):
            item_id = item.get("id")
            self.use_buttons.append(
                (
                    item_id,
                    Button(
                        (config.SCREEN_WIDTH - 150, 0, 70, 34),
                        "Use",
                        on_click=lambda item_id=item_id: self._use_item(item_id),
                        font=self.small_font,
                    ),
                )
            )

    def _max_item_scroll(self, items=None):
        if items is None:
            items = self.game_state.get("items", [])
        return max(0, len(items) - self.visible_item_rows)

    def _use_item(self, item_id):
        items = self.game_state.setdefault("items", [])
        for item in items:
            if item.get("id") != item_id:
                continue
            if item_id in {"bow", "light"} and item_id in self.game_state.get("active_item_effects", []):
                return
            item_name = item.get("name", item_id)
            if int(item.get("quantity", 0)) <= 0:
                return
            item["quantity"] = int(item["quantity"]) - 1
            if item["quantity"] <= 0:
                items.remove(item)
            pending_effects = self.game_state.setdefault("pending_item_effects", [])
            effect_map = {
                "health_gradual": {"resource": "health", "amount": 250.0, "rate": 20.0},
                "health_50": {"resource": "health", "amount": 50.0, "rate": 50.0},
                "health_full": {"resource": "health", "amount": "full"},
                "stamina_gradual": {"resource": "stamina", "amount": 250.0, "rate": 20.0},
                "stamina_50": {"resource": "stamina", "amount": 50.0, "rate": 50.0},
                "stamina_full": {"resource": "stamina", "amount": "full"},
            }
            if item_id in effect_map:
                pending_effects.append(effect_map[item_id])
            if item_id in {"bow", "light"}:
                self.game_state.setdefault("active_item_effects", []).append(item_id)
            profile = self.game_state.setdefault("profile", {})
            items_used = profile.setdefault("items_used", {})
            items_used[item_name] = int(items_used.get(item_name, 0)) + 1
            self.client.commit_inventory_state(self.game_state)
            self._rebuild_use_buttons()
            return

    def _item_image(self, item_id):
        if item_id not in self.item_asset_names:
            return None
        if item_id in self.item_images:
            return self.item_images[item_id]
        asset_root = ITEM_ROOT.parent / "potions" if item_id in {
            "health_gradual", "stamina_gradual", "stamina_50", "health_50",
            "health_full", "stamina_full", "stamina_250",
        } else ITEM_ROOT
        try:
            image = pg.image.load(str(asset_root / self.item_asset_names[item_id])).convert_alpha()
            image = pg.transform.smoothscale(image, (38, 38))
        except (OSError, pg.error):
            return None
        self.item_images[item_id] = image
        return image
