from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


Coordinate = Tuple[int, int]
WALKABLE_TILES = {2, 3, 4, 5, 6, 7}


def find_spawn_tile(grid: Sequence[Sequence[int]]) -> Coordinate:
	height = len(grid)
	width = len(grid[0]) if height else 0
	center_row = height // 2
	center_col = width // 2
	candidates: List[Tuple[int, int, int]] = []

	for row in range(1, height - 1):
		for col in range(1, width - 1):
			if grid[row][col] in WALKABLE_TILES:
				distance = abs(row - center_row) + abs(col - center_col)
				candidates.append((distance, row, col))

	if not candidates:
		return max(1, center_row), max(1, center_col)

	candidates.sort(key=lambda entry: entry[0])
	_, row, col = candidates[0]
	return row, col


def reachable_tiles(grid: Sequence[Sequence[int]], start: Coordinate) -> Set[Coordinate]:
	height = len(grid)
	width = len(grid[0]) if height else 0
	visited: Set[Coordinate] = set()
	queue: deque[Coordinate] = deque([start])

	while queue:
		row, col = queue.popleft()
		if (row, col) in visited:
			continue
		if not (0 <= row < height and 0 <= col < width):
			continue
		if grid[row][col] not in WALKABLE_TILES:
			continue

		visited.add((row, col))
		queue.append((row - 1, col))
		queue.append((row + 1, col))
		queue.append((row, col - 1))
		queue.append((row, col + 1))

	return visited


def is_playable(grid: Sequence[Sequence[int]], start: Optional[Coordinate] = None) -> bool:
	if start is None:
		start = find_spawn_tile(grid)
	return bool(reachable_tiles(grid, start))


def evaluate(grid: Sequence[Sequence[int]], start: Optional[Coordinate] = None) -> Dict[str, float]:
	if start is None:
		start = find_spawn_tile(grid)
	reachable = reachable_tiles(grid, start)
	height = len(grid)
	width = len(grid[0]) if height else 0
	walkable = sum(1 for row in grid for tile in row if tile in WALKABLE_TILES)

	return {
		"start_row": float(start[0]),
		"start_col": float(start[1]),
		"reachable_count": float(len(reachable)),
		"walkable_count": float(walkable),
		"reachable_ratio": len(reachable) / max(1, walkable),
		"open_ratio": walkable / max(1, width * height),
	}


def repair_connectivity(grid: Sequence[Sequence[int]], start: Optional[Coordinate] = None) -> List[List[int]]:
	current = [list(row) for row in grid]
	if start is None:
		start = find_spawn_tile(current)
	reachable = reachable_tiles(current, start)
	if not reachable:
		return current

	height = len(current)
	width = len(current[0]) if height else 0
	walkable_tiles = {
		(row, col)
		for row in range(height)
		for col in range(width)
		if current[row][col] in WALKABLE_TILES
	}
	unreachable = walkable_tiles - reachable

	for target in sorted(unreachable, key=lambda coord: abs(coord[0] - start[0]) + abs(coord[1] - start[1])):
		anchor = min(reachable, key=lambda coord: abs(coord[0] - target[0]) + abs(coord[1] - target[1]))
		_carve_path(current, anchor, target)
		reachable = reachable_tiles(current, start)

	return current


def _carve_path(grid: List[List[int]], start: Coordinate, end: Coordinate) -> None:
	row, col = start
	target_row, target_col = end
	grid[row][col] = 2
	grid[target_row][target_col] = 2

	while (row, col) != (target_row, target_col):
		if row < target_row:
			row += 1
		elif row > target_row:
			row -= 1
		elif col < target_col:
			col += 1
		elif col > target_col:
			col -= 1
		grid[row][col] = 2
