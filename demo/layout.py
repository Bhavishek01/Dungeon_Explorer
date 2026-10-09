from __future__ import annotations

import random
from typing import List, Sequence, Tuple

TILE_WALL = 0
TILE_TRAP = 1
TILE_FLOOR = 2
TILE_WATER = 3
SECTOR_COUNT = 3
Coordinate = Tuple[int, int]


def carve_nine_sector_maze(seed_grid: Sequence[Sequence[int]], rng: random.Random) -> List[List[int]]:
    height = len(seed_grid)
    width = len(seed_grid[0]) if height else 0
    grid = [[TILE_WALL for _ in range(width)] for _ in range(height)]
    sector_h = height // SECTOR_COUNT
    sector_w = width // SECTOR_COUNT
    for sector_row in range(SECTOR_COUNT):
        for sector_col in range(SECTOR_COUNT):
            carve_sector(grid, seed_grid, sector_row, sector_col, sector_h, sector_w, rng)
    connect_sector_centers(grid, sector_h, sector_w, rng)
    seed_traps(grid, sector_h, sector_w, rng)
    return grid


def carve_sector(grid, seed_grid, sector_row, sector_col, sector_h, sector_w, rng):
    top, left = sector_row * sector_h, sector_col * sector_w
    bottom = min(len(grid), top + sector_h)
    right = min(len(grid[0]), left + sector_w)
    row, col = top + sector_h // 2, left + sector_w // 2
    for _ in range(max(40, (sector_h * sector_w) // 2)):
        for delta_row in range(-1, 2):
            for delta_col in range(-1, 2):
                next_row, next_col = row + delta_row, col + delta_col
                if top + 1 <= next_row < bottom - 1 and left + 1 <= next_col < right - 1:
                    if seed_grid[next_row][next_col] in (TILE_FLOOR, TILE_WATER) or rng.random() < 0.24:
                        grid[next_row][next_col] = TILE_WATER if rng.random() < 0.10 else TILE_FLOOR
        delta_row, delta_col = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        row = max(top + 1, min(bottom - 2, row + delta_row))
        col = max(left + 1, min(right - 2, col + delta_col))
        grid[row][col] = TILE_FLOOR


def connect_sector_centers(grid, sector_h, sector_w, rng):
    order = [(0, 0), (0, 1), (0, 2), (1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2)]
    centers = {(r, c): (r * sector_h + sector_h // 2, c * sector_w + sector_w // 2) for r in range(3) for c in range(3)}
    for start, end in zip(order, order[1:]):
        carve_corridor(grid, centers[start], centers[end], rng)


def carve_corridor(grid, start: Coordinate, end: Coordinate, rng):
    row, col = start
    target_row, target_col = end
    for axis in (("col", "row") if rng.random() < 0.5 else ("row", "col")):
        if axis == "col":
            while col != target_col:
                col += 1 if col < target_col else -1
                carve_band(grid, row, col)
        else:
            while row != target_row:
                row += 1 if row < target_row else -1
                carve_band(grid, row, col)
    carve_band(grid, target_row, target_col)


def carve_band(grid, row, col):
    for delta_row in range(-1, 2):
        for delta_col in range(-1, 2):
            next_row, next_col = row + delta_row, col + delta_col
            if 0 < next_row < len(grid) - 1 and 0 < next_col < len(grid[0]) - 1:
                grid[next_row][next_col] = TILE_FLOOR


def seed_traps(grid, sector_h, sector_w, rng):
    for sector_row in range(SECTOR_COUNT):
        for sector_col in range(SECTOR_COUNT):
            top, left = sector_row * sector_h, sector_col * sector_w
            bottom, right = min(len(grid), top + sector_h), min(len(grid[0]), left + sector_w)
            for row in range(top + 2, bottom - 2):
                for col in range(left + 2, right - 2):
                    if grid[row][col] == TILE_FLOOR and rng.random() < 0.05:
                        grid[row][col] = TILE_TRAP
