import math
from pathlib import Path

import pygame as pg

import config


class Player:
    def __init__(self, game_state):
        self.game_state = game_state
        self.world_x = config.PLAYER_START_X
        self.world_y = config.PLAYER_START_Y
        self.size = max(64, config.TILE_SIZE)
        self.speed = config.PLAYER_DEFAULT_SPEED
        self.direction = "down"
        self.flip = 1          # Animation frame (1 or 2)
        self.count = 0
        self.is_moving = False

        # Shooting state
        self.shooting = False
        self.last_shot_time = 0
        self.shoot_direction = (1, 0)
        self.shoot_sprite_key = "shoot_down"

        self.asset_dir = self._resolve_asset_dir()
        self.sprites = self._load_sprites()
        self.current_image = self.sprites["down"][0]

    def _resolve_asset_dir(self):
        base_dir = Path(__file__).resolve().parent.parent
        candidates = [
            base_dir / "assets" / "player",
            base_dir / "assets" / "players" / "gunman",
            base_dir / "assets" / "players",
        ]

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate

        players_root = base_dir / "assets" / "players"
        if players_root.exists():
            for subdir in sorted(players_root.iterdir()):
                if subdir.is_dir() and (subdir / "up 1.png").exists():
                    return subdir

        return base_dir / "assets" / "players" / "gunman"

    def _load_sprites(self):
        asset_dir = self.asset_dir
        sprites = {
            "up": [], "down": [], "left": [], "right": [], "idle": [],
            "shoot_up": [], "shoot_down": [], "shoot_left": [], "shoot_right": [],
            "shoot_up_left": [], "shoot_up_right": [], "shoot_down_left": [], "shoot_down_right": []
        }

        try:
            # Walking + Idle
            sprites["up"] = [
                pg.image.load(str(asset_dir / "up 1.png")).convert_alpha(),
                pg.image.load(str(asset_dir / "up 2.png")).convert_alpha()
            ]
            sprites["down"] = [
                pg.image.load(str(asset_dir / "down 1.png")).convert_alpha(),
                pg.image.load(str(asset_dir / "down 2.png")).convert_alpha()
            ]
            sprites["left"] = [
                pg.image.load(str(asset_dir / "left 1.png")).convert_alpha(),
                pg.image.load(str(asset_dir / "left 2.png")).convert_alpha()
            ]
            sprites["right"] = [
                pg.image.load(str(asset_dir / "right 1.png")).convert_alpha(),
                pg.image.load(str(asset_dir / "right 2.png")).convert_alpha()
            ]

            # Shooting sprites
            sprites["shoot_up"] = [pg.image.load(str(asset_dir / "shoot up.png")).convert_alpha()]
            sprites["shoot_down"] = [pg.image.load(str(asset_dir / "shoot down.png")).convert_alpha()]
            sprites["shoot_left"] = [pg.image.load(str(asset_dir / "shoot left.png")).convert_alpha()]
            sprites["shoot_right"] = [pg.image.load(str(asset_dir / "shoot right.png")).convert_alpha()]
            sprites["shoot_up_left"] = [pg.image.load(str(asset_dir / "shoot left up.png")).convert_alpha()]
            sprites["shoot_up_right"] = [pg.image.load(str(asset_dir / "shoot right up.png")).convert_alpha()]
            sprites["shoot_down_left"] = [pg.image.load(str(asset_dir / "shoot left down.png")).convert_alpha()]
            sprites["shoot_down_right"] = [pg.image.load(str(asset_dir / "shoot right down.png")).convert_alpha()]

        except Exception as e:
            print(f"Sprite load error: {e}. Using fallback.")
            fallback = pg.Surface((self.size, self.size), pg.SRCALPHA)
            pg.draw.rect(fallback, (60, 140, 255), (0, 0, self.size, self.size))
            for key in sprites:
                sprites[key] = [fallback] * 2

        # Scale all images to tile size
        for key in sprites:
            for i in range(len(sprites[key])):
                sprites[key][i] = pg.transform.scale(sprites[key][i], (self.size, self.size))

        sprites["idle"] = sprites["down"]
        return sprites

    def update(self, dt, keys):
        now = pg.time.get_ticks()
        shooting_active = self.shooting and now - self.last_shot_time < config.FIRE_COOLDOWN_MS
        if self.shooting and not shooting_active:
            self.shooting = False

        self.is_moving = False
        dx = dy = 0

        if not shooting_active:
            if keys[pg.K_w] or keys[pg.K_UP]:    dy -= 1; self.direction = "up"; self.is_moving = True
            if keys[pg.K_s] or keys[pg.K_DOWN]:  dy += 1; self.direction = "down"; self.is_moving = True
            if keys[pg.K_a] or keys[pg.K_LEFT]:  dx -= 1; self.direction = "left"; self.is_moving = True
            if keys[pg.K_d] or keys[pg.K_RIGHT]: dx += 1; self.direction = "right"; self.is_moving = True

            # Normalize diagonal movement
            if dx != 0 and dy != 0:
                length = math.hypot(dx, dy)
                dx /= length
                dy /= length

            self.world_x += dx * self.speed
            self.world_y += dy * self.speed

            # Animation timing
            if self.is_moving:
                self.count += 1
                if self.count > 10:   # tweak for animation speed
                    self.flip = 3 - self.flip
                    self.count = 0
            else:
                self.flip = 1
        else:
            self.count = 0
            self.flip = 1

        if shooting_active:
            self.current_image = self.sprites.get(self.shoot_sprite_key, self.sprites["down"])[0]
        elif self.is_moving:
            frame = 0 if self.flip == 1 else 1
            self.current_image = self.sprites[self.direction][frame]
        else:
            self.current_image = self.sprites[self.direction][0]

    def handle_attack(self, mouse_pos):
        """Calculate direction and trigger shoot sprite"""
        now = pg.time.get_ticks()
        if now - self.last_shot_time < config.FIRE_COOLDOWN_MS:
            return

        cx = config.SCREEN_WIDTH // 2
        cy = config.SCREEN_HEIGHT // 2
        dx = mouse_pos[0] - cx
        dy = mouse_pos[1] - cy

        angle = math.atan2(dy, dx)
        if -math.pi / 8 <= angle <= math.pi / 8:
            self.direction = "right"
            self.shoot_sprite_key = "shoot_right"
        elif math.pi / 8 < angle <= 3 * math.pi / 8:
            self.direction = "down"
            self.shoot_sprite_key = "shoot_down_right"
        elif 3 * math.pi / 8 < angle <= 5 * math.pi / 8:
            self.direction = "down"
            self.shoot_sprite_key = "shoot_down"
        elif 5 * math.pi / 8 < angle <= 7 * math.pi / 8:
            self.direction = "down"
            self.shoot_sprite_key = "shoot_down_left"
        elif angle > 7 * math.pi / 8 or angle < -7 * math.pi / 8:
            self.direction = "left"
            self.shoot_sprite_key = "shoot_left"
        elif -7 * math.pi / 8 <= angle < -5 * math.pi / 8:
            self.direction = "up"
            self.shoot_sprite_key = "shoot_up_left"
        elif -5 * math.pi / 8 <= angle < -3 * math.pi / 8:
            self.direction = "up"
            self.shoot_sprite_key = "shoot_up"
        else:
            self.direction = "up"
            self.shoot_sprite_key = "shoot_up_right"

        self.shooting = True
        self.last_shot_time = now
        self.shoot_direction = (dx, dy)

    def get_screen_pos(self):
        """Player stays in center"""
        return (config.SCREEN_WIDTH // 2 - self.size // 2,
                config.SCREEN_HEIGHT // 2 - self.size // 2)

    def draw(self, surface):
        x, y = self.get_screen_pos()
        surface.blit(self.current_image, (x, y))