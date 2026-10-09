from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pygame as pg

from shared.mapgen import (
    ITEM_ROOT,
    MONSTER_ROOT,
    ENVIRONMENT_ROOT,
    TILE_BASIC_SCROLL,
    TILE_FLOOR,
    TILE_LAVA,
    TILE_KEY,
    TILE_RARE_SCROLL,
    TILE_TRAP,
    TILE_TREASURE,
    TILE_WALL,
    TILE_WATER,
)


class WorldRenderer:
    def __init__(self, tile_size: int):
        self.tile_size = tile_size
        self._cache: Dict[Tuple[str, int], pg.Surface] = {}
        self.floor_variants = self._load_floor_variants()
        self.trap_frames = self._load_scaled_sequence([ENVIRONMENT_ROOT / f"trap{i}.png" for i in range(1, 4)])
        self.wall_image = self._load_scaled_image(ENVIRONMENT_ROOT / "wall.png")
        self.water_image = self._load_scaled_image(ENVIRONMENT_ROOT / "water.png")
        self.key_image = self._load_scaled_image(ITEM_ROOT / "key.png")
        self.door_key_image = self._load_scaled_image(ITEM_ROOT / "door_key.png")
        self.basic_scroll_image = self._load_scaled_image(ITEM_ROOT / "basic scroll.png")
        self.rare_scroll_image = self._load_scaled_image(ITEM_ROOT / "rare scroll.png")
        self.treasure_closed_image = self._load_scaled_image(ITEM_ROOT / "treasure_close.png")
        self.treasure_open_item_image = self._load_scaled_image(ITEM_ROOT / "treasure_open_item.png")
        self.treasure_open_nothing_image = self._load_scaled_image(ITEM_ROOT / "treasure_open_nothing.png")
        self.door_closed_image = self._load_scaled_image(ITEM_ROOT / "door.png")
        self.door_open_image = self._load_scaled_image(ITEM_ROOT / "door open.png")
        self.wall_light_image = self._load_scaled_image(ITEM_ROOT / "wall_light.png", scale=0.7)

    def draw(self, surface: pg.Surface, world, camera_x: float, camera_y: float, elapsed: float) -> None:
        self._draw_decorations(surface, world, camera_x, camera_y)
        self._draw_tiles(surface, world, camera_x, camera_y, elapsed)
        self._draw_ground_items(surface, world, camera_x, camera_y, elapsed)
        self._draw_wall_lights(surface, world, camera_x, camera_y)
        self._draw_door(surface, world, camera_x, camera_y)
        self._draw_monsters(surface, world, camera_x, camera_y, elapsed)

    def _draw_tiles(self, surface: pg.Surface, world, camera_x: float, camera_y: float, elapsed: float) -> None:
        start_col = max(0, int(camera_x // self.tile_size) - 1)
        start_row = max(0, int(camera_y // self.tile_size) - 1)
        end_col = min(world.width, start_col + (surface.get_width() // self.tile_size) + 3)
        end_row = min(world.height, start_row + (surface.get_height() // self.tile_size) + 3)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_id = world.tile_at(row, col)
                screen_x = col * self.tile_size - camera_x
                screen_y = row * self.tile_size - camera_y
                rect = pg.Rect(screen_x, screen_y, self.tile_size, self.tile_size)
                image = self._tile_image(tile_id, row, col, elapsed)
                if image is not None:
                    surface.blit(image, rect)
                else:
                    pg.draw.rect(surface, (40, 40, 40), rect)

    def _tile_image(self, tile_id: int, row: int, col: int, elapsed: float) -> pg.Surface | None:
        if tile_id == TILE_WALL:
            return self.wall_image
        if tile_id == TILE_WATER:
            return self.water_image
        if tile_id == TILE_LAVA:
            return self._load_scaled_image(ENVIRONMENT_ROOT / "lava.png")
        if tile_id == TILE_FLOOR:
            return self.floor_variants[(row * 13 + col * 7) % len(self.floor_variants)]
        if tile_id == TILE_TRAP:
            index = int(elapsed * 6 + row + col) % len(self.trap_frames)
            return self.trap_frames[index]
        if tile_id in (TILE_TREASURE, TILE_BASIC_SCROLL, TILE_KEY, TILE_RARE_SCROLL):
            return self.floor_variants[(row * 13 + col * 7) % len(self.floor_variants)]
        return None

    def _draw_ground_items(self, surface: pg.Surface, world, camera_x: float, camera_y: float, elapsed: float) -> None:
        for key in getattr(world, "keys", []):
            if key.get("collected"):
                continue
            image = self.door_key_image if key.get("kind") == "door_key" else self.key_image
            self._blit_centered(
                surface,
                image,
                int(key["row"]),
                int(key["col"]),
                camera_x,
                camera_y,
                scale=0.7,
                y_offset=-self.tile_size * 0.18,
            )

        for scroll in getattr(world, "scrolls", []):
            if scroll.get("collected"):
                continue
            image = self._load_scaled_image(Path(scroll["image"]), scale=0.72)
            self._blit_centered(
                surface,
                image,
                int(scroll["row"]),
                int(scroll["col"]),
                camera_x,
                camera_y,
                scale=0.72,
                y_offset=-self.tile_size * 0.16 - abs(math.sin(elapsed * 5.0)) * self.tile_size * 0.06,
            )

        for treasure in getattr(world, "treasures", []):
            row = int(treasure["row"])
            col = int(treasure["col"])
            if treasure.get("state") == "open":
                chest_image = self.treasure_open_nothing_image if treasure.get("open_variant") == "nothing" else self.treasure_open_item_image
                self._blit_centered(
                    surface,
                    chest_image,
                    row,
                    col,
                    camera_x,
                    camera_y,
                    scale=1.0,
                    y_offset=-self.tile_size * 0.10,
                )
            else:
                image = self.treasure_closed_image
                y_offset = -self.tile_size * 0.10
                self._blit_centered(surface, image, row, col, camera_x, camera_y, scale=1.0, y_offset=y_offset)

    def _draw_door(self, surface: pg.Surface, world, camera_x: float, camera_y: float) -> None:
        door = world.door
        row = int(door["row"])
        col = int(door["col"])
        image = self.door_open_image if door.get("state") == "open" else self.door_closed_image
        self._blit_centered(surface, image, row, col, camera_x, camera_y, scale=1.0)

    def _draw_decorations(self, surface: pg.Surface, world, camera_x: float, camera_y: float) -> None:
        for decoration in getattr(world, "decorations", []):
            image = self._load_scaled_image(Path(decoration["image"]))
            scale = float(decoration.get("scale", 1.0))
            self._blit_centered(
                surface,
                image,
                int(decoration["row"]),
                int(decoration["col"]),
                camera_x,
                camera_y,
                scale=scale,
                y_offset=0,
            )

    def _draw_wall_lights(self, surface: pg.Surface, world, camera_x: float, camera_y: float) -> None:
        for light in world.wall_lights:
            row = int(light["row"])
            col = int(light["col"])
            x = col * self.tile_size - camera_x + self.tile_size * 0.1
            y = row * self.tile_size - camera_y + self.tile_size * 0.45
            image = pg.transform.scale(self.wall_light_image, (int(self.tile_size * 0.7), int(self.tile_size * 0.7)))
            surface.blit(image, (x, y))

    def _draw_monsters(self, surface: pg.Surface, world, camera_x: float, camera_y: float, elapsed: float) -> None:
        for monster in world.monsters:
            frames = self._monster_attr(monster, "frames", [])
            if not frames:
                continue
            frame_index = int(elapsed * 8) % len(frames)
            image = self._load_scaled_image(Path(frames[frame_index]), scale=0.9)
            row = int(self._monster_attr(monster, "row", 0))
            col = int(self._monster_attr(monster, "col", 0))
            self._blit_centered(surface, image, row, col, camera_x, camera_y, scale=0.9)

    def _blit_centered(
        self,
        surface: pg.Surface,
        image: pg.Surface,
        row: int,
        col: int,
        camera_x: float,
        camera_y: float,
        scale: float = 1.0,
        y_offset: float = 0.0,
    ) -> None:
        if image is None:
            return
        width = int(self.tile_size * scale)
        height = int(self.tile_size * scale)
        scaled = pg.transform.scale(image, (width, height))
        x = col * self.tile_size - camera_x + (self.tile_size - width) / 2
        y = row * self.tile_size - camera_y + (self.tile_size - height) / 2 + y_offset
        surface.blit(scaled, (x, y))

    def _load_floor_variants(self) -> List[pg.Surface]:
        paths = [ENVIRONMENT_ROOT / "floor1.png"] * 5 + [ENVIRONMENT_ROOT / f"floor{i}.png" for i in range(2, 9)]
        return [self._load_scaled_image(path) for path in paths]

    def _load_scaled_sequence(self, paths: Iterable[Path]) -> List[pg.Surface]:
        return [self._load_scaled_image(path) for path in paths]

    def _load_scaled_image(self, path: Path, scale: float = 1.0) -> pg.Surface:
        cache_key = (str(path), int(self.tile_size * scale))
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            image = pg.image.load(str(path)).convert_alpha()
        except Exception:
            image = pg.Surface((self.tile_size, self.tile_size), pg.SRCALPHA)
            image.fill((120, 0, 120))

        size = max(1, int(self.tile_size * scale))
        scaled = pg.transform.scale(image, (size, size))
        self._cache[cache_key] = scaled
        return scaled

    def _monster_attr(self, monster, name: str, default):
        if hasattr(monster, name):
            return getattr(monster, name)
        if isinstance(monster, dict):
            return monster.get(name, default)
        return default
