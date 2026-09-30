import math
import random
import sys
import secrets
from copy import deepcopy
from pathlib import Path

import pygame as pg

# Make both src/ and src/client importable so shared and client packages load reliably.
CLIENT_DIR = Path(__file__).resolve().parents[1]
BASE_DIR = Path(__file__).resolve().parents[2]
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config
from entities.player import Player
from gameplay.inventory import add_item, consume_item, count_item, label_for_kind
from entities.monster1 import Monster1
from entities.monster2 import Monster2
from entities.monster3 import Monster3
from renderers.world_renderer import WorldRenderer
from screens import Screen
from ui import Button, draw_label
from shared.mapgen.astar import find_path
from shared.mapgen import TILE_BASIC_SCROLL, TILE_FLOOR, TILE_KEY, TILE_LAVA, TILE_RARE_SCROLL, TILE_TREASURE, TILE_TRAP, TILE_WALL, TILE_WATER, generate_map


class GameScreen(Screen):
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.hud_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)
        self.death_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_TITLE + 18, bold=True)
        self.hp_icon = self._load_hud_icon("hp.png")
        self.stamina_icon = self._load_hud_icon("sta.png")
        self.coin_icon = self._load_hud_icon("coins.png")
        self.tile_size = max(32, config.TILE_SIZE - 16)
        self.elapsed = 0.0
        self.reveal_elapsed = 0.0
        self.reveal_duration = 3.5

        self.player = Player(game_state)
        self.player.apply_progression(game_state.get("profile", {}))
        self.projectiles = []
        self.monster_projectiles = []
        self.scroll_pickups = []
        self.active_regens = []
        self.active_debuffs = []
        self.level_complete = False
        self.run_active = False
        self.bullet_image = self._load_bullet_sprite()
        self.world = None
        self.monsters = []
        self.renderer = WorldRenderer(self.tile_size)
        self.death_buttons = [
            Button(
                (config.SCREEN_WIDTH // 2 - 140, config.SCREEN_HEIGHT // 2 + 70, 280, 48),
                "Restart",
                on_click=self._restart_after_death,
                font=self.hud_font,
            ),
            Button(
                (config.SCREEN_WIDTH // 2 - 140, config.SCREEN_HEIGHT // 2 + 130, 280, 48),
                "Exit",
                on_click=self._exit_after_death,
                font=self.hud_font,
            ),
        ]
        self.level_buttons = [
            Button(
                (config.SCREEN_WIDTH // 2 - 140, config.SCREEN_HEIGHT // 2 + 25, 280, 48),
                "Next Level",
                on_click=self._next_level,
                font=self.hud_font,
            ),
            Button(
                (config.SCREEN_WIDTH // 2 - 140, config.SCREEN_HEIGHT // 2 + 85, 280, 48),
                "Exit",
                on_click=self._exit_after_level,
                font=self.hud_font,
            ),
        ]

    def on_enter(self, **kwargs):
        resumed = bool(kwargs.get("resumed", False))
        if not resumed or self.world is None:
            self._generate_new_world()
        self.projectiles.clear()
        self.monster_projectiles.clear()
        self.scroll_pickups.clear()

    def _generate_new_world(self):
        if not self.run_active:
            self.game_state["_run_start_items"] = deepcopy(self.game_state.get("items", []))
            self.game_state["_run_start_equipped"] = deepcopy(self.game_state.get("equipped", [0, 0, 0]))
            self.game_state["_run_start_profile"] = deepcopy(self.game_state.get("profile", {}))
            self.run_active = True
        self.reveal_elapsed = 0.0
        self.level_complete = False
        self.game_state["equipped"] = [0, 0, 0]
        self.game_state["active_item_effects"] = []
        self.active_regens.clear()
        self.active_debuffs.clear()
        profile = self.game_state.get("profile", {})
        self.world = generate_map(profile=profile, seed=secrets.randbits(64))
        class_key = self.game_state.get("player_class", config.DEFAULT_CLASS)
        class_stats = config.PLAYER_CLASSES.get(class_key, {})
        self.player.apply_class_stats(class_stats)
        self.player.reset_stats(class_stats)
        self.game_state["health"] = self.player.health
        self.game_state["stamina"] = self.player.stamina
        self.monsters = [self._monster_from_data(monster) for monster in self.world.monsters]
        self.world.monsters = self.monsters
        self.world.spawn_schedule = [
            {"spawn_at": event["spawn_at"], "monster": self._monster_from_data(event["monster"])}
            for event in self.world.spawn_schedule
        ]
        self.player.world_x = self.world.player_spawn[1] * self.tile_size + self.tile_size // 2 - self.player.size // 2
        self.player.world_y = self.world.player_spawn[0] * self.tile_size + self.tile_size // 2 - self.player.size // 2

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        if self.player.health <= 0:
            for button in self.death_buttons:
                button.handle_event(event)
            return
        if self.level_complete:
            for button in self.level_buttons:
                button.handle_event(event)
            return
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                self.manager.switch_to(config.SCREEN_PAUSE)
            if event.key == pg.K_e:
                self.manager.switch_to(config.SCREEN_INVENTORY, resumed=True)
            if event.key == pg.K_SPACE:
                self._resolve_world_interactions()

        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pg.mouse.get_pos()
            if not self.player.handle_attack(mouse_pos):
                return

            # Spawn projectile from the player's center
            start_x = self.player.world_x + self.player.size // 2
            start_y = self.player.world_y + self.player.size // 2
            dx = mouse_pos[0] - (config.SCREEN_WIDTH // 2)
            dy = mouse_pos[1] - (config.SCREEN_HEIGHT // 2)
            self._create_projectile(start_x, start_y, dx, dy)

    def update(self, dt):
        if self.world is None:
            self._generate_new_world()
        if self.player.health <= 0:
            self.player.health = 0
            self.client.poll_events()
            return
        if self.level_complete:
            self.client.poll_events()
            return
        self.elapsed += dt
        self._update_scroll_pickups(dt)
        self.reveal_elapsed = min(self.reveal_duration, self.reveal_elapsed + dt)
        keys = pg.key.get_pressed()
        class_key = self.game_state.get("player_class", config.DEFAULT_CLASS)
        stats = config.PLAYER_CLASSES.get(class_key, {})
        self.player.speed = stats.get("speed", config.PLAYER_DEFAULT_SPEED)
        self.player.apply_class_stats(stats)
        self._apply_pending_item_effects()

        moving_input = any((keys[pg.K_w], keys[pg.K_UP], keys[pg.K_s], keys[pg.K_DOWN], keys[pg.K_a], keys[pg.K_LEFT], keys[pg.K_d], keys[pg.K_RIGHT]))
        # Run multiplier
        sprinting = moving_input and (keys[pg.K_LSHIFT] or keys[pg.K_RSHIFT]) and self.player.stamina > 0
        if sprinting:
            self.player.speed *= config.PLAYER_RUN_SPEED_MULTIPLIER

        terrain_multiplier = self._terrain_speed_multiplier()
        self.player.speed *= terrain_multiplier

        self.player.update(dt, keys, can_move=self._can_move_player)
        self.world.update(dt)
        self._sync_monsters()
        self._update_monsters(dt)
        self._update_monster_projectiles()
        self._apply_survival_effects(dt, sprinting)
        self._apply_monster_terrain_effects(dt)
        self.client.poll_events()

        # Update bullets
        for p in self.projectiles[:]:
            next_x = p['x'] + p['dx']
            next_y = p['y'] + p['dy']
            if self._projectile_hits_blocker(next_x, next_y) or self._projectile_hits_monster(next_x, next_y, p):
                self.projectiles.remove(p)
                continue
            p['x'] = next_x
            p['y'] = next_y
            p['dist'] += p['speed']
            if p['dist'] >= p['max_distance']:
                self.projectiles.remove(p)

    def draw(self, surface):
        if self.world is None:
            self._generate_new_world()
        surface.fill((10, 10, 18))

        # === CAMERA CENTER ===
        cam_x = self.player.world_x - config.SCREEN_WIDTH // 2 + self.player.size // 2
        cam_y = self.player.world_y - config.SCREEN_HEIGHT // 2 + self.player.size // 2

        self.renderer.draw(surface, self.world, cam_x, cam_y, self.elapsed)
        self._draw_monster_health_bars(surface, cam_x, cam_y)
        self._draw_scroll_pickups(surface, cam_x, cam_y)

        for projectile in self.monster_projectiles:
            pg.draw.circle(
                surface,
                (255, 120, 50),
                (int(projectile["x"] - cam_x), int(projectile["y"] - cam_y)),
                6,
            )

        # Draw Player (centered)
        self.player.draw(surface)

        # Draw Projectiles
        for p in self.projectiles:
            sx = p['x'] - cam_x
            sy = p['y'] - cam_y
            rotated = pg.transform.rotate(self.bullet_image, p['angle'])
            rect = rotated.get_rect(center=(int(sx), int(sy)))
            surface.blit(rotated, rect)

        self._draw_fog_of_war(surface)

        # HUD
        draw_label(surface,
            "WASD/Arrows: Move | Shift: Run | Mouse: Shoot | Esc: Pause | E: Inventory",
            (10, config.SCREEN_HEIGHT - 30),
            font=self.hud_font, color=config.COLOR_GRAY)
        self._draw_stat_bar(surface, self.hp_icon, self.player.health, self.player.max_health, (16, 12), config.COLOR_RED)
        self._draw_stat_bar(surface, self.stamina_icon, self.player.stamina, self.player.max_stamina, (16, 32), config.COLOR_CYAN)
        self._draw_coin_counter(surface)
        self._draw_reveal_overlay(surface)
        if self.player.health <= 0:
            self._draw_death_overlay(surface)
        if self.level_complete:
            self._draw_level_complete_overlay(surface)

    def _draw_fog_of_war(self, surface):
        if "light" in self.game_state.get("active_item_effects", []):
            return

        overlay = pg.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pg.SRCALPHA)
        center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2)
        max_radius = self.tile_size * config.FOG_RADIUS_TILES
        clear_radius = self.tile_size * 2.2
        bands = 24
        overlay.fill((12, 14, 24, config.FOG_ALPHA))
        for band in range(bands, -1, -1):
            progress = band / bands
            radius = int(clear_radius + (max_radius - clear_radius) * progress)
            alpha = int(config.FOG_ALPHA * (progress ** 1.7))
            pg.draw.circle(overlay, (12, 14, 24, alpha), center, radius)
        surface.blit(overlay, (0, 0))

    def _draw_reveal_overlay(self, surface):
        if self.reveal_elapsed >= self.reveal_duration:
            return

        progress = self.reveal_elapsed / self.reveal_duration
        max_radius = math.hypot(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
        radius = max(1, int(max_radius * progress))
        overlay = pg.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 255))
        pg.draw.circle(
            overlay,
            (0, 0, 0, 0),
            (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2),
            radius,
        )
        surface.blit(overlay, (0, 0))

    def _draw_death_overlay(self, surface):
        overlay = pg.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((8, 0, 0, 190))
        surface.blit(overlay, (0, 0))
        draw_label(
            surface,
            "YOU DIED!",
            (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2),
            font=self.death_font,
            color=config.COLOR_RED,
            center=True,
        )
        for button in self.death_buttons:
            button.draw(surface)

    def _start_item_pickup(self, image_path, row, col):
        try:
            image = pg.image.load(str(image_path)).convert_alpha()
        except (OSError, pg.error):
            image = pg.Surface((32, 32), pg.SRCALPHA)
        self.scroll_pickups.append(
            {
                "x": int(col) * self.tile_size + self.tile_size / 2,
                "y": int(row) * self.tile_size + self.tile_size / 2,
                "image": pg.transform.smoothscale(image, (34, 34)),
                "elapsed": 0.0,
                "duration": 0.9,
            }
        )

    def _start_scroll_pickup(self, scroll):
        self._start_item_pickup(scroll["image"], scroll["row"], scroll["col"])

    def _update_scroll_pickups(self, dt):
        for pickup in self.scroll_pickups[:]:
            pickup["elapsed"] += dt
            if pickup["elapsed"] >= pickup["duration"]:
                self.scroll_pickups.remove(pickup)

    def _draw_scroll_pickups(self, surface, camera_x, camera_y):
        for pickup in self.scroll_pickups:
            progress = pickup["elapsed"] / pickup["duration"]
            image = pickup["image"].copy()
            image.set_alpha(max(0, int(255 * (1.0 - progress))))
            x = pickup["x"] - camera_x
            y = pickup["y"] - camera_y - progress * self.tile_size * 1.5
            surface.blit(image, image.get_rect(center=(int(x), int(y))))

    def _draw_level_complete_overlay(self, surface):
        overlay = pg.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 20, 10, 210))
        surface.blit(overlay, (0, 0))
        draw_label(
            surface,
            "LEVEL COMPLETE!",
            (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 55),
            font=self.death_font,
            color=config.COLOR_GREEN,
            center=True,
        )
        for button in self.level_buttons:
            button.draw(surface)

    def _restart_after_death(self):
        self.projectiles.clear()
        self.monster_projectiles.clear()
        self.client.discard_game_run(self.game_state)
        self.run_active = False
        self._generate_new_world()

    def _exit_after_death(self):
        self.client.discard_game_run(self.game_state)
        self.run_active = False
        self.manager.switch_to(config.SCREEN_MENU)

    def _next_level(self):
        self.projectiles.clear()
        self.monster_projectiles.clear()
        self._generate_new_world()

    def _commit_run_progress(self):
        self.client.clear_temporary_keys(self.game_state)
        self.game_state["active_item_effects"] = []
        self.client.commit_game_state(self.game_state)
        self.game_state["_run_start_items"] = deepcopy(self.game_state.get("items", []))
        self.game_state["_run_start_equipped"] = deepcopy(self.game_state.get("equipped", [0, 0, 0]))
        self.game_state["_run_start_profile"] = deepcopy(self.game_state.get("profile", {}))

    def _exit_after_level(self):
        self.run_active = False
        self.manager.switch_to(config.SCREEN_MENU)

    def _draw_stat_bar(self, surface, icon, value, maximum, position, color):
        x, y = position
        bar_width = 180
        bar_height = 14
        icon_width = 24
        bar_rect = pg.Rect(x + icon_width, y + 2, bar_width, bar_height)
        ratio = max(0.0, min(1.0, value / maximum if maximum else 0.0))

        surface.blit(icon, (x, y - 2))
        pg.draw.rect(surface, (35, 35, 45), bar_rect, border_radius=3)
        fill_rect = bar_rect.copy()
        fill_rect.width = int(bar_rect.width * ratio)
        if fill_rect.width > 0:
            pg.draw.rect(surface, color, fill_rect, border_radius=3)
        pg.draw.rect(surface, (210, 210, 220), bar_rect, width=1, border_radius=3)

    def _draw_coin_counter(self, surface):
        surface.blit(self.coin_icon, (config.SCREEN_WIDTH - 118, 12))
        draw_label(
            surface,
            str(self.game_state.get("profile", {}).get("coins", 0)),
            (config.SCREEN_WIDTH - 72, 14),
            font=self.hud_font,
            color=config.COLOR_YELLOW,
        )

    def _load_hud_icon(self, filename):
        path = Path(__file__).resolve().parents[2] / "shared" / "tiles" / "items" / filename
        try:
            image = pg.image.load(str(path)).convert_alpha()
        except (OSError, pg.error):
            image = pg.Surface((24, 24), pg.SRCALPHA)
        return pg.transform.smoothscale(image, (24, 24))

    def on_exit(self):
        self.game_state["health"] = self.player.health
        self.game_state["stamina"] = self.player.stamina

    def _create_projectile(self, start_x, start_y, dx, dy):
        length = math.hypot(dx, dy) or 1
        projectile_multiplier = 2 if self.player.has_bow_gun() else 1
        projectile_speed = config.PROJECTILE_SPEED * projectile_multiplier
        self.projectiles.append({
            'x': start_x,
            'y': start_y,
            'dx': (dx / length) * projectile_speed,
            'dy': (dy / length) * projectile_speed,
            'speed': projectile_speed,
            'damage': config.PROJECTILE_DAMAGE * projectile_multiplier,
            'dist': 0,
            'max_distance': self.tile_size * config.PROJECTILE_MAX_TILES,
            'angle': math.degrees(math.atan2(dy, dx))
        })

    def _load_bullet_sprite(self):
        bullet_path = Path(__file__).resolve().parent.parent / "assets" / "players" / "gunman" / "bullet.png"
        try:
            image = pg.image.load(str(bullet_path)).convert_alpha()
        except Exception:
            image = pg.Surface((16, 16), pg.SRCALPHA)
            pg.draw.circle(image, (255, 220, 90), (8, 8), 6)
        return pg.transform.scale(image, (12, 12))

    def _can_move_player(self, next_x, next_y):
        future_rect = self.player.get_collision_rect(next_x, next_y)

        for monster in self.monsters:
            if future_rect.colliderect(monster.rect):
                return False

        corners = [
            (future_rect.left, future_rect.top),
            (future_rect.right - 1, future_rect.top),
            (future_rect.left, future_rect.bottom - 1),
            (future_rect.right - 1, future_rect.bottom - 1),
        ]

        for corner_x, corner_y in corners:
            row = int(corner_y // self.tile_size)
            col = int(corner_x // self.tile_size)
            if self._is_collidable_tile(self.world.tile_at(row, col)):
                return False

            door_row = int(self.world.door["row"])
            door_col = int(self.world.door["col"])
            if self.world.door.get("state") != "open" and row == door_row and col == door_col:
                return False

        return True

    def _resolve_world_interactions(self):
        center_row, center_col = self._player_center_tile()
        self._collect_tile_items(center_row, center_col)
        self._open_door_if_possible(center_row, center_col)
        self._open_treasures_if_possible(center_row, center_col)

    def _collect_tile_items(self, center_row, center_col):
        for key in self.world.keys:
            if key.get("collected"):
                continue
            if not self._is_near_tile(center_row, center_col, key["row"], key["col"]):
                continue

            key["collected"] = True
            self.world.set_tile(key["row"], key["col"], TILE_FLOOR)
            add_item(self.game_state.setdefault("items", []), key["kind"], label_for_kind(key["kind"]), 1)

        for scroll in self.world.scrolls:
            if scroll.get("collected"):
                continue
            if not self._is_near_tile(center_row, center_col, scroll["row"], scroll["col"]):
                continue

            scroll["collected"] = True
            self.world.set_tile(scroll["row"], scroll["col"], TILE_FLOOR)
            self._start_scroll_pickup(scroll)
            add_item(self.game_state.setdefault("items", []), scroll["kind"], label_for_kind(scroll["kind"]), 1)
        self.client.commit_inventory_state(self.game_state)

    def _open_door_if_possible(self, center_row, center_col):
        if self.world.door.get("state") == "open":
            return

        door_row = int(self.world.door["row"])
        door_col = int(self.world.door["col"])
        if not self._is_near_tile(center_row, center_col, door_row, door_col):
            return

        if count_item(self.game_state.setdefault("items", []), "door_key") <= 0:
            return

        if consume_item(self.game_state["items"], "door_key", 1):
            self.world.door["state"] = "open"
            self._commit_run_progress()
            self.level_complete = True

    def _open_treasures_if_possible(self, center_row, center_col):
        for treasure in self.world.treasures:
            if treasure.get("state") == "open":
                continue
            if not self._is_near_tile(center_row, center_col, treasure["row"], treasure["col"]):
                continue

            required_key = treasure["required_key"]
            if count_item(self.game_state.setdefault("items", []), required_key) <= 0:
                continue

            if consume_item(self.game_state["items"], required_key, 1):
                treasure["state"] = "open"
                self.world.set_tile(treasure["row"], treasure["col"], TILE_FLOOR)
                reward = treasure.get("reward_item")
                if reward:
                    if reward["id"] == "coins":
                        profile = self.game_state.setdefault("profile", {})
                        profile["coins"] = int(profile.get("coins", 0)) + 100
                    else:
                        add_item(self.game_state["items"], reward["id"], reward["name"], int(reward.get("quantity", 1)))
                reward_image = treasure.get("reward_image")
                if reward_image:
                    self._start_item_pickup(reward_image, treasure["row"], treasure["col"])
                if treasure.get("open_variant") == "debuff":
                    self.active_debuffs.append({"remaining": 5.0})
                self.client.commit_inventory_state(self.game_state)

    def _apply_scroll_effect(self, kind):
        if kind == "basic_scroll":
            resource = random.choice(("health", "stamina"))
            self.active_regens.append({"resource": resource, "remaining": 250.0})
        elif kind == "rare_scroll":
            self.player.health = self.player.max_health
            self.player.stamina = self.player.max_stamina

    def _player_center_tile(self):
        center_x = self.player.world_x + self.player.size / 2
        center_y = self.player.world_y + self.player.size / 2
        return int(center_y // self.tile_size), int(center_x // self.tile_size)

    def _monster_from_data(self, monster_data):
        kind = monster_data.get("kind", "monster1")
        if kind == "monster2":
            return Monster2(monster_data, self.tile_size)
        if kind == "monster3":
            return Monster3(monster_data, self.tile_size)
        return Monster1(monster_data, self.tile_size)

    def _sync_monsters(self):
        for monster in self.monsters:
            monster.sync_rect()

    def _terrain_speed_multiplier(self):
        center_row, center_col = self._player_center_tile()
        tile_id = self.world.tile_at(center_row, center_col)
        if tile_id == TILE_LAVA:
            return config.PLAYER_LAVA_SPEED_MULTIPLIER
        if tile_id == TILE_TRAP:
            return config.PLAYER_TRAP_SPEED_MULTIPLIER
        return 1.0

    def _apply_survival_effects(self, dt, sprinting):
        center_row, center_col = self._player_center_tile()
        tile_id = self.world.tile_at(center_row, center_col)

        if tile_id == TILE_LAVA:
            self.player.health = max(0, self.player.health - config.PLAYER_LAVA_LIFE_DRAIN_PER_SEC * dt)
        elif tile_id == TILE_TRAP:
            self.player.health = max(0, self.player.health - config.PLAYER_TRAP_LIFE_DRAIN_PER_SEC * dt)

        if sprinting:
            self.player.stamina = max(0, self.player.stamina - config.PLAYER_RUN_STAMINA_DRAIN_PER_SEC * dt)
        else:
            self.player.stamina = min(self.player.max_stamina, self.player.stamina + config.PLAYER_STAMINA_REGEN_PER_SEC * dt)

        for effect in self.active_regens[:]:
            amount = min(effect.get("rate", 20.0) * dt, effect["remaining"])
            if effect["resource"] == "health":
                self.player.health = min(self.player.max_health, self.player.health + amount)
            else:
                self.player.stamina = min(self.player.max_stamina, self.player.stamina + amount)
            effect["remaining"] -= amount
            if effect["remaining"] <= 0:
                self.active_regens.remove(effect)

    def _apply_pending_item_effects(self):
        pending_effects = self.game_state.setdefault("pending_item_effects", [])
        for effect in pending_effects:
            resource = effect["resource"]
            amount = effect["amount"]
            if amount == "full":
                if resource == "health":
                    self.player.health = self.player.max_health
                else:
                    self.player.stamina = self.player.max_stamina
                continue
            if amount == 50.0:
                if resource == "health":
                    self.player.health = min(self.player.max_health, self.player.health + 50.0)
                else:
                    self.player.stamina = min(self.player.max_stamina, self.player.stamina + 50.0)
                continue
            self.active_regens.append(
                {
                    "resource": resource,
                    "remaining": float(amount),
                    "rate": float(effect.get("rate", 20.0)),
                }
            )
        pending_effects.clear()

        for effect in self.active_debuffs[:]:
            amount = 20.0 * dt / 5.0
            self.player.health = max(0, self.player.health - amount)
            self.player.stamina = max(0, self.player.stamina - amount)
            effect["remaining"] -= dt
            if effect["remaining"] <= 0:
                self.active_debuffs.remove(effect)

        self.game_state["health"] = self.player.health
        self.game_state["stamina"] = self.player.stamina

    def _apply_monster_terrain_effects(self, dt):
        for monster in self.monsters[:]:
            row = int((monster.world_y + monster.size / 2) // self.tile_size)
            col = int((monster.world_x + monster.size / 2) // self.tile_size)
            tile_id = self.world.tile_at(row, col)
            if tile_id == TILE_LAVA:
                damage = config.MONSTER_LAVA_DAMAGE_PER_SEC
            elif tile_id == TILE_WATER:
                damage = config.MONSTER_WATER_DAMAGE_PER_SEC
            elif tile_id == TILE_TRAP:
                damage = config.MONSTER_TRAP_DAMAGE_PER_SEC
            else:
                continue

            monster.health -= damage * dt
            if monster.health <= 0:
                self._record_monster_kill(monster)
                self.monsters.remove(monster)

    def _is_near_tile(self, center_row, center_col, row, col):
        return abs(center_row - row) <= 1 and abs(center_col - col) <= 1

    def _is_collidable_tile(self, tile_id):
        return tile_id in (TILE_WALL, TILE_TREASURE, TILE_BASIC_SCROLL, TILE_KEY, TILE_RARE_SCROLL)

    def _projectile_hits_blocker(self, x, y):
        row = int(y // self.tile_size)
        col = int(x // self.tile_size)
        return self._is_collidable_tile(self.world.tile_at(row, col))

    def _projectile_hits_monster(self, x, y, projectile):
        projectile_rect = pg.Rect(int(x) - 4, int(y) - 4, 8, 8)
        for monster in self.monsters[:]:
            if not projectile_rect.colliderect(monster.rect):
                continue
            if not monster.is_active:
                self._wake_monster(monster)
            monster.health -= projectile.get("damage", config.PROJECTILE_DAMAGE)
            if monster.health <= 0:
                self._record_monster_kill(monster)
                self.monsters.remove(monster)
            return True
        return False

    def _record_monster_kill(self, monster):
        profile = self.game_state.setdefault("profile", {})
        profile["level"] = max(1, int(profile.get("level", self.player.level)))
        profile["experience"] = max(0, int(profile.get("experience", self.player.experience)))
        profile["experience_required"] = max(
            1,
            int(profile.get("experience_required", self.player.experience_required)),
        )
        kills = profile.setdefault("monster_kills", {})
        kind = getattr(monster, "kind", "monster")
        kills[kind] = int(kills.get(kind, 0)) + 1
        profile["experience"] += getattr(monster, "experience_reward", config.MONSTER_EXPERIENCE.get(kind, 300))

        while profile["experience"] >= profile["experience_required"]:
            profile["experience"] -= profile["experience_required"]
            profile["level"] += 1
            profile["experience_required"] = max(
                profile["experience_required"] + 1,
                int(profile["experience_required"] * config.EXPERIENCE_REQUIREMENT_GROWTH),
            )

        self.player.apply_progression(profile)
        if kind == "monster3":
            self._drop_door_key(monster)

    def _update_monsters(self, dt):
        for monster in self.monsters[:]:
            distance = self._distance_to_player(monster)
            if not monster.is_active and distance <= self.tile_size * config.MONSTER_WAKE_RADIUS_TILES:
                self._wake_monster(monster)
            if not monster.is_active:
                continue

            if monster.kind == "monster1":
                if self.world.door.get("state") == "open":
                    continue
                self._move_monster_toward(monster)
                if self._distance_to_player(monster) <= self.tile_size and self.elapsed >= monster.next_attack_at:
                    self.player.health = max(0, self.player.health - config.MONSTER_CONTACT_DAMAGE)
                    monster.next_attack_at = self.elapsed + 0.8
            elif monster.kind == "monster2":
                if distance <= self.tile_size * config.MONSTER_CHASE_RADIUS_TILES:
                    self._move_monster_toward(monster)
                    if self.elapsed >= monster.next_attack_at:
                        self._create_monster_projectile(monster)
                        monster.next_attack_at = self.elapsed + config.MONSTER2_PROJECTILE_COOLDOWN
                else:
                    self._move_monster_home(monster)
            elif monster.kind == "monster3":
                if distance <= self.tile_size * config.MONSTER_CHASE_RADIUS_TILES:
                    self._move_monster_toward(monster)
                    if self.elapsed >= monster.next_attack_at:
                        self._create_monster_projectile(monster)
                        monster.next_attack_at = self.elapsed + config.MONSTER2_PROJECTILE_COOLDOWN
                else:
                    self._move_monster_home(monster)

    def _wake_monster(self, monster):
        monster.is_active = True
        monster.next_attack_at = self.elapsed

    def _distance_to_player(self, monster):
        player_center_x = self.player.world_x + self.player.size / 2
        player_center_y = self.player.world_y + self.player.size / 2
        monster_center_x = monster.world_x + monster.size / 2
        monster_center_y = monster.world_y + monster.size / 2
        return math.hypot(player_center_x - monster_center_x, player_center_y - monster_center_y)

    def _move_monster_toward(self, monster):
        player_center_x = self.player.world_x + self.player.size / 2
        player_center_y = self.player.world_y + self.player.size / 2
        target_row = int(player_center_y // self.tile_size)
        target_col = int(player_center_x // self.tile_size)
        self._move_monster_to_tile(monster, target_row, target_col, avoid_player=True)

    def _move_monster_home(self, monster):
        self._move_monster_to_tile(monster, monster.spawn_row, monster.spawn_col)

    def _move_monster_to_tile(self, monster, target_row, target_col, avoid_player=False):
        if self.elapsed < monster.next_move_at:
            return

        monster_row = int((monster.world_y + monster.size / 2) // self.tile_size)
        monster_col = int((monster.world_x + monster.size / 2) // self.tile_size)
        path = find_path(self.world.tiles, (monster_row, monster_col), (target_row, target_col))
        if len(path) < 2:
            return

        next_row, next_col = path[1]
        if avoid_player and self._is_player_tile(next_row, next_col):
            return
        if monster.kind == "monster3" and (
                abs(next_row - monster.spawn_row) + abs(next_col - monster.spawn_col)
                > config.MONSTER3_LEASH_TILES
        ):
            return
        target_x = next_col * self.tile_size + (self.tile_size - monster.size) // 2
        target_y = next_row * self.tile_size + (self.tile_size - monster.size) // 2
        if not self._can_move_monster(monster, target_x, target_y):
            return
        monster.world_x = target_x
        monster.world_y = target_y
        monster.row = next_row
        monster.col = next_col
        monster.sync_rect()
        tiles_per_second = max(1.0, monster.speed * 60 / self.tile_size)
        monster.next_move_at = self.elapsed + 1.0 / tiles_per_second

    def _is_player_tile(self, row, col):
        player_row, player_col = self._player_center_tile()
        return row == player_row and col == player_col

    def _can_move_monster(self, monster, next_x, next_y):
        next_rect = pg.Rect(int(next_x), int(next_y), monster.size, monster.size)
        for other_monster in self.monsters:
            if other_monster is not monster and next_rect.colliderect(other_monster.rect):
                return False
        corners = (
            (next_rect.left, next_rect.top),
            (next_rect.right - 1, next_rect.top),
            (next_rect.left, next_rect.bottom - 1),
            (next_rect.right - 1, next_rect.bottom - 1),
        )
        for corner_x, corner_y in corners:
            row = int(corner_y // self.tile_size)
            col = int(corner_x // self.tile_size)
            if self.world.tile_at(row, col) == TILE_WALL:
                return False
        return True

    def _create_monster_projectile(self, monster):
        player_center_x = self.player.world_x + self.player.size / 2
        player_center_y = self.player.world_y + self.player.size / 2
        monster_center_x = monster.world_x + monster.size / 2
        monster_center_y = monster.world_y + monster.size / 2
        dx = player_center_x - monster_center_x
        dy = player_center_y - monster_center_y
        distance = math.hypot(dx, dy) or 1
        speed = config.PROJECTILE_SPEED * 0.75
        self.monster_projectiles.append(
            {
                "x": monster_center_x,
                "y": monster_center_y,
                "dx": dx / distance * speed,
                "dy": dy / distance * speed,
                "dist": 0,
                "max_distance": self.tile_size * config.MONSTER_CHASE_RADIUS_TILES,
                "damage": config.MONSTER2_PROJECTILE_DAMAGE,
            }
        )

    def _update_monster_projectiles(self):
        player_rect = self.player.get_collision_rect()
        for projectile in self.monster_projectiles[:]:
            next_x = projectile["x"] + projectile["dx"]
            next_y = projectile["y"] + projectile["dy"]
            if self._projectile_hits_blocker(next_x, next_y):
                self.monster_projectiles.remove(projectile)
                continue

            projectile["x"] = next_x
            projectile["y"] = next_y
            projectile["dist"] += math.hypot(projectile["dx"], projectile["dy"])
            projectile_rect = pg.Rect(int(next_x) - 5, int(next_y) - 5, 10, 10)
            if projectile_rect.colliderect(player_rect):
                self.player.health = max(0, self.player.health - projectile["damage"])
                self.monster_projectiles.remove(projectile)
                continue
            if projectile["dist"] >= projectile["max_distance"]:
                self.monster_projectiles.remove(projectile)

    def _draw_monster_health_bars(self, surface, camera_x, camera_y):
        for monster in self.monsters:
            width = 36
            height = 5
            x = int(monster.rect.centerx - camera_x - width / 2)
            y = int(monster.rect.top - camera_y - 9)
            background = pg.Rect(x, y, width, height)
            fill = background.copy()
            fill.width = int(width * max(0.0, min(1.0, monster.health / monster.max_health)))
            pg.draw.rect(surface, (45, 20, 25), background)
            if fill.width > 0:
                pg.draw.rect(surface, config.COLOR_RED, fill)
            pg.draw.rect(surface, config.COLOR_WHITE, background, width=1)

    def _drop_door_key(self, monster):
        monster_row = int(monster.rect.centery // self.tile_size)
        monster_col = int(monster.rect.centerx // self.tile_size)
        key = next((item for item in self.world.keys if item.get("kind") == "door_key"), None)
        if key is None:
            key = {
                "row": monster_row,
                "col": monster_col,
                "kind": "door_key",
                "image": "src/shared/tiles/items/door_key.png",
                "collected": False,
            }
            self.world.keys.append(key)
        else:
            self.world.set_tile(int(key["row"]), int(key["col"]), TILE_FLOOR)
            key["row"] = monster_row
            key["col"] = monster_col
            key["collected"] = False
        self.world.set_tile(monster_row, monster_col, TILE_KEY)

    def _is_touching_tile(self, row, col):
        player_rect = self.player.get_collision_rect()
        tile_rect = pg.Rect(col * self.tile_size, row * self.tile_size, self.tile_size, self.tile_size)
        return player_rect.colliderect(tile_rect)