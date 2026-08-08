import math
import sys
import secrets
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
from ui import draw_label
from shared.mapgen import TILE_BASIC_SCROLL, TILE_FLOOR, TILE_KEY, TILE_LAVA, TILE_RARE_SCROLL, TILE_TREASURE, TILE_TRAP, TILE_WALL, generate_map


class GameScreen(Screen):
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.hud_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)
        self.tile_size = max(32, config.TILE_SIZE - 16)
        self.elapsed = 0.0

        self.player = Player(game_state)
        self.projectiles = []
        self.bullet_image = self._load_bullet_sprite()
        self.world = None
        self.monsters = []
        self.renderer = WorldRenderer(self.tile_size)

    def on_enter(self, **kwargs):
        resumed = bool(kwargs.get("resumed", False))
        if not resumed or self.world is None:
            self._generate_new_world()
        self.projectiles.clear()

    def _generate_new_world(self):
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
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_p:
                self.manager.switch_to(config.SCREEN_PAUSE)
            if event.key == pg.K_e:
                self.manager.switch_to(config.SCREEN_INVENTORY)
            if event.key == pg.K_SPACE:
                self._resolve_world_interactions()

        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pg.mouse.get_pos()
            self.player.handle_attack(mouse_pos)

            # Spawn projectile from the player's center
            start_x = self.player.world_x + self.player.size // 2
            start_y = self.player.world_y + self.player.size // 2
            dx = mouse_pos[0] - (config.SCREEN_WIDTH // 2)
            dy = mouse_pos[1] - (config.SCREEN_HEIGHT // 2)
            self._create_projectile(start_x, start_y, dx, dy)

    def update(self, dt):
        if self.world is None:
            self._generate_new_world()
        self.elapsed += dt
        keys = pg.key.get_pressed()
        class_key = self.game_state.get("player_class", config.DEFAULT_CLASS)
        stats = config.PLAYER_CLASSES.get(class_key, {})
        self.player.speed = stats.get("speed", config.PLAYER_DEFAULT_SPEED)
        self.player.apply_class_stats(stats)

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
        self._apply_survival_effects(dt, sprinting)
        self.client.poll_events()

        # Update bullets
        for p in self.projectiles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['dist'] += config.PROJECTILE_SPEED
            if p['dist'] > config.PROJECTILE_MAX_DISTANCE:
                self.projectiles.remove(p)

    def draw(self, surface):
        if self.world is None:
            self._generate_new_world()
        surface.fill((10, 10, 18))

        # === CAMERA CENTER ===
        cam_x = self.player.world_x - config.SCREEN_WIDTH // 2 + self.player.size // 2
        cam_y = self.player.world_y - config.SCREEN_HEIGHT // 2 + self.player.size // 2

        self.renderer.draw(surface, self.world, cam_x, cam_y, self.elapsed)

        # Draw Player (centered)
        self.player.draw(surface)

        # Draw Projectiles
        for p in self.projectiles:
            sx = p['x'] - cam_x
            sy = p['y'] - cam_y
            rotated = pg.transform.rotate(self.bullet_image, p['angle'])
            rect = rotated.get_rect(center=(int(sx), int(sy)))
            surface.blit(rotated, rect)

        # HUD
        draw_label(surface,
            "WASD/Arrows: Move | Shift: Run | Mouse: Shoot | P: Pause | E: Inventory",
            (10, config.SCREEN_HEIGHT - 30),
            font=self.hud_font, color=config.COLOR_GRAY)
        draw_label(surface, f"HP {int(self.player.health)}/{int(self.player.max_health)}", (16, 12), font=self.hud_font, color=config.COLOR_RED)
        draw_label(surface, f"STA {int(self.player.stamina)}/{int(self.player.max_stamina)}", (16, 32), font=self.hud_font, color=config.COLOR_CYAN)

    def on_exit(self):
        self.game_state["health"] = self.player.health
        self.game_state["stamina"] = self.player.stamina
        self.client.commit_game_state(self.game_state)

    def _create_projectile(self, start_x, start_y, dx, dy):
        length = math.hypot(dx, dy) or 1
        self.projectiles.append({
            'x': start_x,
            'y': start_y,
            'dx': (dx / length) * config.PROJECTILE_SPEED,
            'dy': (dy / length) * config.PROJECTILE_SPEED,
            'dist': 0,
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
            if self.world.tile_at(row, col) == TILE_WALL:
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
            if not self._is_touching_tile(key["row"], key["col"]):
                continue

            key["collected"] = True
            self.world.set_tile(key["row"], key["col"], TILE_FLOOR)
            add_item(self.game_state.setdefault("items", []), key["kind"], label_for_kind(key["kind"]), 1)

        for scroll in self.world.scrolls:
            if scroll.get("collected"):
                continue
            if not self._is_touching_tile(scroll["row"], scroll["col"]):
                continue

            scroll["collected"] = True
            self.world.set_tile(scroll["row"], scroll["col"], TILE_FLOOR)
            add_item(self.game_state.setdefault("items", []), scroll["kind"], label_for_kind(scroll["kind"]), 1)

    def _open_door_if_possible(self, center_row, center_col):
        if self.world.door.get("state") == "open":
            return

        door_row = int(self.world.door["row"])
        door_col = int(self.world.door["col"])
        if not self._is_touching_tile(door_row, door_col):
            return

        if count_item(self.game_state.setdefault("items", []), "door_key") <= 0:
            return

        if consume_item(self.game_state["items"], "door_key", 1):
            self.world.door["state"] = "open"

    def _open_treasures_if_possible(self, center_row, center_col):
        for treasure in self.world.treasures:
            if treasure.get("state") == "open":
                continue
            if not self._is_touching_tile(treasure["row"], treasure["col"]):
                continue

            required_key = treasure["required_key"]
            if count_item(self.game_state.setdefault("items", []), required_key) <= 0:
                continue

            if consume_item(self.game_state["items"], required_key, 1):
                treasure["state"] = "open"
                self.world.set_tile(treasure["row"], treasure["col"], TILE_FLOOR)
                reward = treasure.get("reward_item")
                if reward:
                    add_item(self.game_state["items"], reward["id"], reward["name"], int(reward.get("quantity", 1)))

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

        self.game_state["health"] = self.player.health
        self.game_state["stamina"] = self.player.stamina

    def _is_near_tile(self, center_row, center_col, row, col):
        return abs(center_row - row) <= 1 and abs(center_col - col) <= 1

    def _is_touching_tile(self, row, col):
        player_rect = self.player.get_collision_rect()
        tile_rect = pg.Rect(col * self.tile_size, row * self.tile_size, self.tile_size, self.tile_size)
        return player_rect.colliderect(tile_rect)