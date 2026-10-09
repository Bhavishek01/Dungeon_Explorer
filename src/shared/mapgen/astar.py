from __future__ import annotations

import math
import heapq
from typing import List, Sequence, Set, Tuple

from .constants import WALKABLE_TILES


Coordinate = Tuple[int, int]


def find_path(grid: Sequence[Sequence[int]], start: Coordinate, goal: Coordinate) -> List[Coordinate]:
    if start == goal:
        return [start]

    height = len(grid)
    width = len(grid[0]) if height else 0
    open_set: List[Tuple[int, int, Coordinate]] = [(0, 0, start)]
    came_from: dict[Coordinate, Coordinate] = {}
    g_score = {start: 0}
    sequence = 0

    while open_set:
        _, _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        row, col = current
        for next_row, next_col in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if not (0 <= next_row < height and 0 <= next_col < width):
                continue
            if grid[next_row][next_col] not in WALKABLE_TILES:
                continue

            neighbor = (next_row, next_col)
            tentative_g = g_score[current] + 1
            if tentative_g >= g_score.get(neighbor, math.inf):
                continue

            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            sequence += 1
            heuristic = abs(goal[0] - next_row) + abs(goal[1] - next_col)
            heapq.heappush(open_set, (tentative_g + heuristic, sequence, neighbor))

    return []


def path_exists(grid: Sequence[Sequence[int]], start: Coordinate, goal: Coordinate) -> bool:
    if start == goal:
        return True

    height = len(grid)
    width = len(grid[0]) if height else 0
    open_set: List[Tuple[int, Coordinate]] = [(0, start)]
    g_score = {start: 0}
    closed: Set[Coordinate] = set()

    while open_set:
        open_set.sort(key=lambda entry: entry[0])
        _, current = open_set.pop(0)
        if current in closed:
            continue
        if current == goal:
            return True

        closed.add(current)
        row, col = current
        for next_row, next_col in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
            if not (0 <= next_row < height and 0 <= next_col < width):
                continue
            if grid[next_row][next_col] not in WALKABLE_TILES:
                continue

            neighbor = (next_row, next_col)
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, math.inf):
                g_score[neighbor] = tentative_g
                f_score = tentative_g + abs(goal[0] - next_row) + abs(goal[1] - next_col)
                open_set.append((f_score, neighbor))

    return False
