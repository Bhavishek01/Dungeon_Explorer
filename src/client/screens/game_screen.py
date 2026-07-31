import math
import sys
from pathlib import Path

import pygame as pg

import config
from entities.player import Player
from screens import Screen
from ui import draw_label


class GameScreen(Screen):
    def __init__(self, manager, client, game_state):
        self.manager = manager
        self.client = client
        self.game_state = game_state

        self.hud_font = pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_SMALL)
        self.player = Player(game_state)
        self.projectiles = []
        self.bullet_image = self._load_bullet_sprite()
        self.tile_size = max(32, config.TILE_SIZE - 16)

        # Simple map data (replace with real loader later)
        self.map_width = 100
        self.map_height = 80

    def handle_event(self, event):
        if event.type == pg.QUIT:
            sys.exit(0)
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_p:
                self.manager.switch_to(config.SCREEN_PAUSE)
            if event.key == pg.K_e:
                self.manager.switch_to(config.SCREEN_INVENTORY)

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
        keys = pg.key.get_pressed()
        class_key = self.game_state.get("player_class", config.DEFAULT_CLASS)
        stats = config.PLAYER_CLASSES.get(class_key, {})
        self.player.speed = stats.get("speed", config.PLAYER_DEFAULT_SPEED)

        # Run multiplier
        if keys[pg.K_LSHIFT] or keys[pg.K_RSHIFT]:
            self.player.speed *= config.PLAYER_RUN_SPEED_MULTIPLIER

        self.player.update(dt, keys)
        self.client.poll_events()

        # Update bullets
        for p in self.projectiles[:]:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['dist'] += config.PROJECTILE_SPEED
            if p['dist'] > config.PROJECTILE_MAX_DISTANCE:
                self.projectiles.remove(p)

    def draw(self, surface):
        surface.fill((10, 10, 18))

        # === CAMERA CENTER ===
        cam_x = self.player.world_x - config.SCREEN_WIDTH // 2 + config.TILE_SIZE // 2
        cam_y = self.player.world_y - config.SCREEN_HEIGHT // 2 + config.TILE_SIZE // 2

        # Draw map tiles (placeholder - replace with real tile images)
        tile_size = self.tile_size
        start_col = max(0, int(cam_x // tile_size) - 1)
        start_row = max(0, int(cam_y // tile_size) - 1)
        end_col = start_col + (config.SCREEN_WIDTH // tile_size) + 3
        end_row = start_row + (config.SCREEN_HEIGHT // tile_size) + 3

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                screen_x = col * tile_size - cam_x
                screen_y = row * tile_size - cam_y
                # Simple ground / stone pattern
                color = (45, 45, 35) if (row + col) % 2 == 0 else (30, 30, 25)
                pg.draw.rect(surface, color, (screen_x, screen_y, tile_size, tile_size))

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