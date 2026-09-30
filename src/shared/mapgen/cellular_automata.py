from __future__ import annotations

from typing import List, Sequence

from .constants import TILE_FLOOR, TILE_TRAP, TILE_WALL, TILE_WATER


def smooth(grid: Sequence[Sequence[int]], steps: int = 2) -> List[List[int]]:
    current = [list(row) for row in grid]
    height = len(current)
    width = len(current[0]) if height else 0

    for _ in range(steps):
        next_grid = [row[:] for row in current]
        for row in range(1, height - 1):
            for col in range(1, width - 1):
                wall_neighbors = 0
                trap_neighbors = 0
                for neighbor_row in range(row - 1, row + 2):
                    for neighbor_col in range(col - 1, col + 2):
                        if neighbor_row == row and neighbor_col == col:
                            continue
                        tile = current[neighbor_row][neighbor_col]
                        if tile == TILE_WALL:
                            wall_neighbors += 1
                        elif tile == TILE_TRAP:
                            trap_neighbors += 1

                if wall_neighbors >= 5:
                    next_grid[row][col] = TILE_WALL
                elif current[row][col] == TILE_WATER and wall_neighbors <= 2:
                    next_grid[row][col] = TILE_FLOOR
                elif current[row][col] == TILE_TRAP and wall_neighbors <= 1:
                    next_grid[row][col] = TILE_FLOOR
        current = next_grid

    return current
