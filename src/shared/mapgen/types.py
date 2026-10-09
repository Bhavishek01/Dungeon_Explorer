from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


Coordinate = Tuple[int, int]


@dataclass
class GeneratedWorld:
    width: int
    height: int
    tiles: List[List[int]]
    player_spawn: Coordinate
    door_key: Dict[str, object]
    door: Dict[str, object]
    treasures: List[Dict[str, object]] = field(default_factory=list)
    keys: List[Dict[str, object]] = field(default_factory=list)
    scrolls: List[Dict[str, object]] = field(default_factory=list)
    monsters: List[Dict[str, object]] = field(default_factory=list)
    wall_lights: List[Dict[str, object]] = field(default_factory=list)
    decorations: List[Dict[str, object]] = field(default_factory=list)
    spawn_schedule: List[Dict[str, object]] = field(default_factory=list)
    reachable_tiles: Set[Coordinate] = field(default_factory=set)
    elapsed: float = 0.0

    def update(self, dt: float) -> List[Dict[str, object]]:
        self.elapsed += dt
        spawned: List[Dict[str, object]] = []
        self.spawn_schedule.sort(key=lambda event: event["spawn_at"])

        while self.spawn_schedule and self.spawn_schedule[0]["spawn_at"] <= self.elapsed:
            event = self.spawn_schedule.pop(0)
            monster = event["monster"]
            self.monsters.append(monster)
            spawned.append(monster)

        return spawned

    def is_within_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.height and 0 <= col < self.width

    def tile_at(self, row: int, col: int) -> int:
        if not self.is_within_bounds(row, col):
            return 0
        return self.tiles[row][col]

    def set_tile(self, row: int, col: int, tile_id: int) -> None:
        if self.is_within_bounds(row, col):
            self.tiles[row][col] = tile_id
