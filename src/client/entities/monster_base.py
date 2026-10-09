from __future__ import annotations

from pathlib import Path

import pygame as pg

import config


class MonsterBase:
    def __init__(self, data, tile_size: int):
        self.kind = data.get("kind", "monster")
        self.row = int(data.get("row", 0))
        self.col = int(data.get("col", 0))
        self.frames = list(data.get("frames", []))
        self.guarding = bool(data.get("guarding", False))
        self.spawn_at = data.get("spawn_at")
        self.tile_size = tile_size
        self.size = 16
        self.spawn_row = self.row
        self.spawn_col = self.col
        stats = config.MONSTER_STATS.get(self.kind, {})
        self.max_health = int(data.get("max_health", stats.get("health", config.MONSTER_DEFAULT_LIFE)))
        self.health = int(data.get("health", self.max_health))
        self.experience_reward = int(data.get("experience", stats.get("experience", 300)))
        self.speed = config.MONSTER_DEFAULT_SPEED
        self.is_active = False
        self.next_attack_at = 0.0
        self.next_move_at = 0.0
        self.chase_limit_x = None
        self.chase_limit_y = None
        self.world_x = self.col * tile_size + (tile_size - self.size) // 2
        self.world_y = self.row * tile_size + (tile_size - self.size) // 2
        self.rect = pg.Rect(self.world_x, self.world_y, self.size, self.size)

    def sync_rect(self):
        self.rect.topleft = (int(self.world_x), int(self.world_y))
        return self.rect

    def frame_path(self, index: int):
        if not self.frames:
            return None
        return Path(self.frames[index % len(self.frames)])
