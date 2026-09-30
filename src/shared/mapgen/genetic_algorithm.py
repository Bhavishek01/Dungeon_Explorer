from __future__ import annotations

import random
from typing import List, Sequence

from .constants import TILE_BASIC_SCROLL, TILE_FLOOR, TILE_KEY, TILE_RARE_SCROLL, TILE_TRAP, TILE_WALL, TILE_WATER


TileGrid = List[List[int]]


def seed_layout(width: int, height: int, rng: random.Random) -> TileGrid:
    grid = [[TILE_WALL for _ in range(width)] for _ in range(height)]
    for row in range(1, height - 1):
        for col in range(1, width - 1):
            roll = rng.random()
            if roll < 0.18:
                grid[row][col] = TILE_WALL
            elif roll < 0.52:
                grid[row][col] = TILE_FLOOR
            elif roll < 0.62:
                grid[row][col] = TILE_WATER
            elif roll < 0.75:
                grid[row][col] = TILE_TRAP
            elif roll < 0.87:
                grid[row][col] = TILE_BASIC_SCROLL
            elif roll < 0.95:
                grid[row][col] = TILE_KEY
            else:
                grid[row][col] = TILE_RARE_SCROLL
    return grid


def generate_population(width: int, height: int, population_size: int, rng: random.Random) -> List[TileGrid]:
    return [seed_layout(width, height, rng) for _ in range(population_size)]


def crossover(parent_a: Sequence[Sequence[int]], parent_b: Sequence[Sequence[int]], rng: random.Random) -> TileGrid:
    height = len(parent_a)
    width = len(parent_a[0]) if height else 0
    split_row = rng.randrange(1, max(2, height - 1)) if height > 2 else height // 2
    split_col = rng.randrange(1, max(2, width - 1)) if width > 2 else width // 2

    child = [list(row) for row in parent_a]
    for row in range(height):
        for col in range(width):
            if row >= split_row or col >= split_col:
                child[row][col] = parent_b[row][col]
    return child


def mutate(grid: Sequence[Sequence[int]], rng: random.Random, mutation_rate: float) -> TileGrid:
    mutated = [list(row) for row in grid]
    height = len(mutated)
    width = len(mutated[0]) if height else 0

    for row in range(1, height - 1):
        for col in range(1, width - 1):
            if rng.random() < mutation_rate:
                roll = rng.random()
                if roll < 0.55:
                    mutated[row][col] = TILE_FLOOR
                elif roll < 0.70:
                    mutated[row][col] = TILE_WATER
                elif roll < 0.82:
                    mutated[row][col] = TILE_TRAP
                elif roll < 0.92:
                    mutated[row][col] = TILE_WALL
                else:
                    mutated[row][col] = TILE_RARE_SCROLL

    return mutated
