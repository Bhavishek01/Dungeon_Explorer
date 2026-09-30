from __future__ import annotations

import random
from typing import List, Sequence, Tuple

from .constants import SECTOR_COUNT, TILE_FLOOR, TILE_TRAP, TILE_WALL, TILE_WATER


def carve_nine_sector_maze(seed_grid: Sequence[Sequence[int]], rng: random.Random) -> List[List[int]]:
    current = [[TILE_WALL for _ in range(len(seed_grid[0]))] for _ in range(len(seed_grid))]
    height = len(current)
    width = len(current[0]) if height else 0
    sector_h = height // SECTOR_COUNT
    sector_w = width // SECTOR_COUNT

    for row in range(height):
        current[row][0] = TILE_WALL
        current[row][width - 1] = TILE_WALL
    for col in range(width):
        current[0][col] = TILE_WALL
        current[height - 1][col] = TILE_WALL

    for sector_row in range(SECTOR_COUNT):
        for sector_col in range(SECTOR_COUNT):
            carve_sector(current, seed_grid, sector_row, sector_col, sector_h, sector_w, rng)

    connect_sector_centers(current, sector_h, sector_w, rng)
    seed_traps(current, sector_h, sector_w, rng)
    return current


def carve_sector(
    grid: List[List[int]],
    seed_grid: Sequence[Sequence[int]],
    sector_row: int,
    sector_col: int,
    sector_h: int,
    sector_w: int,
    rng: random.Random,
) -> None:
    top = sector_row * sector_h
    left = sector_col * sector_w
    bottom = min(len(grid), top + sector_h)
    right = min(len(grid[0]), left + sector_w)
    center_row = top + sector_h // 2
    center_col = left + sector_w // 2
    row = center_row
    col = center_col
    steps = max(40, (sector_h * sector_w) // 2)
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for _ in range(steps):
        for delta_row in range(-1, 2):
            for delta_col in range(-1, 2):
                next_row = row + delta_row
                next_col = col + delta_col
                if top + 1 <= next_row < bottom - 1 and left + 1 <= next_col < right - 1:
                    seed_tile = seed_grid[next_row][next_col]
                    if seed_tile in (TILE_FLOOR, TILE_WATER) or rng.random() < 0.24:
                        grid[next_row][next_col] = TILE_WATER if rng.random() < 0.10 else TILE_FLOOR

        delta_row, delta_col = rng.choice(directions)
        row = max(top + 1, min(bottom - 2, row + delta_row))
        col = max(left + 1, min(right - 2, col + delta_col))
        grid[row][col] = TILE_FLOOR

    if rng.random() < 0.30:
        for delta_row in range(-2, 3):
            for delta_col in range(-2, 3):
                next_row = center_row + delta_row
                next_col = center_col + delta_col
                if top + 1 <= next_row < bottom - 1 and left + 1 <= next_col < right - 1:
                    grid[next_row][next_col] = TILE_FLOOR


def connect_sector_centers(grid: List[List[int]], sector_h: int, sector_w: int, rng: random.Random) -> None:
    path_order = [(0, 0), (0, 1), (0, 2), (1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2)]
    centers = {
        (sector_row, sector_col): (sector_row * sector_h + sector_h // 2, sector_col * sector_w + sector_w // 2)
        for sector_row in range(SECTOR_COUNT)
        for sector_col in range(SECTOR_COUNT)
    }

    for start_sector, end_sector in zip(path_order, path_order[1:]):
        carve_corridor(grid, centers[start_sector], centers[end_sector], rng)

    for sector_row in range(SECTOR_COUNT):
        for sector_col in range(SECTOR_COUNT):
            if sector_col < SECTOR_COUNT - 1 and rng.random() < 0.55:
                carve_corridor(grid, centers[(sector_row, sector_col)], centers[(sector_row, sector_col + 1)], rng)
            if sector_row < SECTOR_COUNT - 1 and rng.random() < 0.55:
                carve_corridor(grid, centers[(sector_row, sector_col)], centers[(sector_row + 1, sector_col)], rng)


def carve_corridor(grid: List[List[int]], start: Tuple[int, int], end: Tuple[int, int], rng: random.Random) -> None:
    row, col = start
    target_row, target_col = end
    segments = ["col", "row"] if rng.random() < 0.5 else ["row", "col"]

    for axis in segments:
        if axis == "col":
            while col != target_col:
                col += 1 if col < target_col else -1
                carve_band(grid, row, col)
        else:
            while row != target_row:
                row += 1 if row < target_row else -1
                carve_band(grid, row, col)

    carve_band(grid, target_row, target_col)


def carve_band(grid: List[List[int]], row: int, col: int) -> None:
    for delta_row in range(-1, 2):
        for delta_col in range(-1, 2):
            next_row = row + delta_row
            next_col = col + delta_col
            if 0 <= next_row < len(grid) and 0 <= next_col < len(grid[0]):
                if 0 < next_row < len(grid) - 1 and 0 < next_col < len(grid[0]) - 1:
                    grid[next_row][next_col] = TILE_FLOOR


def seed_traps(grid: List[List[int]], sector_h: int, sector_w: int, rng: random.Random) -> None:
    for sector_row in range(SECTOR_COUNT):
        for sector_col in range(SECTOR_COUNT):
            top = sector_row * sector_h
            left = sector_col * sector_w
            bottom = min(len(grid), top + sector_h)
            right = min(len(grid[0]), left + sector_w)
            for row in range(top + 2, bottom - 2):
                for col in range(left + 2, right - 2):
                    if grid[row][col] == TILE_FLOOR and rng.random() < 0.03 and not has_trap_neighbor(grid, row, col, radius=2):
                        grid[row][col] = TILE_TRAP


def has_trap_neighbor(grid: List[List[int]], row: int, col: int, radius: int) -> bool:
    for next_row in range(max(0, row - radius), min(len(grid), row + radius + 1)):
        for next_col in range(max(0, col - radius), min(len(grid[0]), col + radius + 1)):
            if next_row == row and next_col == col:
                continue
            if grid[next_row][next_col] == TILE_TRAP:
                return True
    return False
