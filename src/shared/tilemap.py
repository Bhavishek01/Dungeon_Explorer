from __future__ import annotations

from shared.mapgen import *
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import random
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


TILE_WALL = 0       # collidable
TILE_STONE = 1      # collidable
TILE_GROUND = 2     # walkable
TILE_WATER = 3      # walkable, slows player (see player.iswater in old Java)
TILE_TREASURE = 4   # visual chest marker, not blocking
TILE_POTION = 5
TILE_KEY = 6
TILE_POWER = 7


WALKABLE_TILES = (TILE_GROUND, TILE_WATER, TILE_TREASURE, TILE_POTION, TILE_KEY, TILE_POWER)
COLLIDABLE_TILES = (TILE_WALL, TILE_STONE)

Coordinate = Tuple[int, int]


@dataclass
class GeneratedMap:
	width: int
	height: int
	tiles: List[List[int]]
	player_spawn: Coordinate
	door_position: Coordinate
	treasure_position: Coordinate
	items: List[Dict[str, object]] = field(default_factory=list)
	monsters: List[Dict[str, object]] = field(default_factory=list)
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
			return TILE_WALL
		return self.tiles[row][col]

	def set_tile(self, row: int, col: int, tile_id: int) -> None:
		if self.is_within_bounds(row, col):
			self.tiles[row][col] = tile_id


def generate_map(
	width: int,
	height: int,
	profile: Optional[Dict[str, object]] = None,
	seed: Optional[object] = None,
) -> GeneratedMap:
	rng = random.Random(seed)
	profile = profile or {}

	population_size = 6
	generations = 4
	population = [_seed_layout(width, height, rng) for _ in range(population_size)]
	final_candidates: List[Tuple[List[List[int]], Dict[str, float]]] = []

	for generation in range(generations):
		scored_population = []
		for grid in population:
			smoothed = _cellular_automata(grid, steps=2 + generation // 2)
			metrics = _evaluate_grid(smoothed)
			fitness = _fitness(metrics)
			scored_population.append((fitness, smoothed, metrics))

		scored_population.sort(key=lambda entry: entry[0], reverse=True)
		final_candidates = [(entry[1], entry[2]) for entry in scored_population]

		survivors = [entry[1] for entry in scored_population[:2]]
		children = survivors[:]
		while len(children) < population_size:
			parent_a, parent_b = rng.sample(survivors, 2) if len(survivors) > 1 else (survivors[0], survivors[0])
			child = _crossover(parent_a, parent_b, rng)
			child = _mutate(child, rng, mutation_rate=0.08 + generation * 0.02)
			children.append(child)
		population = children

	if not final_candidates:
		fallback_grid = _seed_layout(width, height, rng)
		fallback_metrics = _evaluate_grid(fallback_grid)
		final_candidates = [(fallback_grid, fallback_metrics)]

	playable_candidates = [
		candidate
		for candidate in final_candidates
		if candidate[1]["reachable_ratio"] >= 0.82 and candidate[1]["walkable_count"] >= (width * height) * 0.16
	]
	if not playable_candidates:
		playable_candidates = final_candidates

	best_grid, best_metrics = max(
		playable_candidates,
		key=lambda candidate: (_profile_tree_score(candidate[1], profile), candidate[1]["reachable_ratio"]),
	)
	best_grid = _enforce_connectivity(best_grid)
	best_metrics = _evaluate_grid(best_grid)

	generated = _build_generated_map(best_grid, best_metrics, profile, rng)
	if not generated.reachable_tiles:
		fallback_grid = _force_connected_layout(width, height, rng)
		fallback_metrics = _evaluate_grid(fallback_grid)
		generated = _build_generated_map(fallback_grid, fallback_metrics, profile, rng)

	return generated


def _seed_layout(width: int, height: int, rng: random.Random) -> List[List[int]]:
	grid = [[TILE_WALL for _ in range(width)] for _ in range(height)]
	for row in range(1, height - 1):
		for col in range(1, width - 1):
			chance = 0.56 + (0.10 if 2 < row < height - 3 and 2 < col < width - 3 else 0.0)
			if rng.random() < chance:
				grid[row][col] = TILE_GROUND
			elif rng.random() < 0.05:
				grid[row][col] = TILE_WATER
			elif rng.random() < 0.03:
				grid[row][col] = TILE_STONE
	return grid


def _force_connected_layout(width: int, height: int, rng: random.Random) -> List[List[int]]:
	grid = [[TILE_WALL for _ in range(width)] for _ in range(height)]
	room_height = max(5, height // 2)
	room_width = max(5, width // 2)
	top = max(1, height // 2 - room_height // 2)
	left = max(1, width // 2 - room_width // 2)
	for row in range(top, min(height - 1, top + room_height)):
		for col in range(left, min(width - 1, left + room_width)):
			grid[row][col] = TILE_GROUND
	for row in range(1, height - 1):
		grid[row][left + room_width // 2] = TILE_GROUND
	for col in range(1, width - 1):
		grid[top + room_height // 2][col] = TILE_GROUND
	return _cellular_automata(grid, steps=1)


def _enforce_connectivity(grid: Sequence[Sequence[int]]) -> List[List[int]]:
	current = [list(row) for row in grid]
	start = _find_spawn_tile(current)
	reachable = _bfs_reachable(current, start)
	if not reachable:
		return _force_connected_layout(len(current[0]), len(current), random.Random(0))

	height = len(current)
	width = len(current[0]) if height else 0
	walkable_tiles = {
		(row, col)
		for row in range(height)
		for col in range(width)
		if current[row][col] in WALKABLE_TILES
	}
	unreachable = walkable_tiles - reachable
	if not unreachable:
		return current

	for target in sorted(unreachable, key=lambda coord: abs(coord[0] - start[0]) + abs(coord[1] - start[1])):
		anchor = min(reachable, key=lambda coord: abs(coord[0] - target[0]) + abs(coord[1] - target[1]))
		_carve_corridor(current, anchor, target)
		reachable = _bfs_reachable(current, start)

	return current


def _carve_corridor(grid: List[List[int]], start: Coordinate, end: Coordinate) -> None:
	row, col = start
	target_row, target_col = end
	grid[row][col] = TILE_GROUND
	grid[target_row][target_col] = TILE_GROUND

	while (row, col) != (target_row, target_col):
		if row < target_row:
			row += 1
		elif row > target_row:
			row -= 1
		elif col < target_col:
			col += 1
		elif col > target_col:
			col -= 1
		grid[row][col] = TILE_GROUND
		for neighbor_row, neighbor_col in _neighbors(row, col):
			if 0 <= neighbor_row < len(grid) and 0 <= neighbor_col < len(grid[0]):
				if grid[neighbor_row][neighbor_col] == TILE_WALL and (neighbor_row + neighbor_col + row + col) % 5 == 0:
					grid[neighbor_row][neighbor_col] = TILE_GROUND


def _cellular_automata(grid: Sequence[Sequence[int]], steps: int = 2) -> List[List[int]]:
	current = [list(row) for row in grid]
	height = len(current)
	width = len(current[0]) if height else 0

	for _ in range(steps):
		next_grid = [row[:] for row in current]
		for row in range(1, height - 1):
			for col in range(1, width - 1):
				wall_neighbors = 0
				water_neighbors = 0
				for neighbor_row in range(row - 1, row + 2):
					for neighbor_col in range(col - 1, col + 2):
						if neighbor_row == row and neighbor_col == col:
							continue
						tile = current[neighbor_row][neighbor_col]
						if tile in COLLIDABLE_TILES:
							wall_neighbors += 1
						elif tile == TILE_WATER:
							water_neighbors += 1

				if wall_neighbors >= 5:
					next_grid[row][col] = TILE_WALL
				elif water_neighbors >= 3 and current[row][col] == TILE_GROUND:
					next_grid[row][col] = TILE_WATER
				elif current[row][col] in COLLIDABLE_TILES and wall_neighbors <= 2:
					next_grid[row][col] = TILE_GROUND
		current = next_grid

	return current


def _crossover(parent_a: Sequence[Sequence[int]], parent_b: Sequence[Sequence[int]], rng: random.Random) -> List[List[int]]:
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


def _mutate(grid: Sequence[Sequence[int]], rng: random.Random, mutation_rate: float) -> List[List[int]]:
	mutated = [list(row) for row in grid]
	height = len(mutated)
	width = len(mutated[0]) if height else 0

	for row in range(1, height - 1):
		for col in range(1, width - 1):
			if rng.random() < mutation_rate:
				roll = rng.random()
				if roll < 0.60:
					mutated[row][col] = TILE_GROUND
				elif roll < 0.82:
					mutated[row][col] = TILE_WATER
				elif roll < 0.93:
					mutated[row][col] = TILE_STONE
				else:
					mutated[row][col] = TILE_WALL

	return mutated


def _neighbors(row: int, col: int) -> Iterable[Coordinate]:
	yield row - 1, col
	yield row + 1, col
	yield row, col - 1
	yield row, col + 1


def _find_spawn_tile(grid: Sequence[Sequence[int]]) -> Coordinate:
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


def _bfs_reachable(grid: Sequence[Sequence[int]], start: Coordinate) -> Set[Coordinate]:
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
		for next_row, next_col in _neighbors(row, col):
			if (next_row, next_col) not in visited:
				queue.append((next_row, next_col))

	return visited


def _a_star_path_exists(grid: Sequence[Sequence[int]], start: Coordinate, goal: Coordinate) -> bool:
	if start == goal:
		return True

	height = len(grid)
	width = len(grid[0]) if height else 0
	open_set: List[Tuple[int, Coordinate]] = [(0, start)]
	g_score: Dict[Coordinate, int] = {start: 0}
	closed: Set[Coordinate] = set()

	while open_set:
		open_set.sort(key=lambda entry: entry[0])
		_, current = open_set.pop(0)
		if current in closed:
			continue
		if current == goal:
			return True

		closed.add(current)
		current_row, current_col = current
		for next_row, next_col in _neighbors(current_row, current_col):
			if not (0 <= next_row < height and 0 <= next_col < width):
				continue
			if grid[next_row][next_col] not in WALKABLE_TILES:
				continue

			tentative_g = g_score[current] + 1
			neighbor = (next_row, next_col)
			if tentative_g < g_score.get(neighbor, math.inf):
				g_score[neighbor] = tentative_g
				f_score = tentative_g + abs(goal[0] - next_row) + abs(goal[1] - next_col)
				open_set.append((f_score, neighbor))

	return False


def _furthest_tiles(reachable: Set[Coordinate], start: Coordinate) -> List[Coordinate]:
	return sorted(reachable, key=lambda coord: abs(coord[0] - start[0]) + abs(coord[1] - start[1]), reverse=True)


def _evaluate_grid(grid: Sequence[Sequence[int]]) -> Dict[str, float]:
	height = len(grid)
	width = len(grid[0]) if height else 0
	start = _find_spawn_tile(grid)
	reachable = _bfs_reachable(grid, start)
	walkable_count = sum(1 for row in grid for tile in row if tile in WALKABLE_TILES)
	open_ratio = walkable_count / max(1, width * height)
	reachable_ratio = len(reachable) / max(1, walkable_count)
	edge_open = sum(
		1
		for row in range(height)
		for col in range(width)
		if (row in (0, height - 1) or col in (0, width - 1)) and grid[row][col] in WALKABLE_TILES
	)

	return {
		"open_ratio": open_ratio,
		"reachable_ratio": reachable_ratio,
		"reachable_count": float(len(reachable)),
		"edge_open": float(edge_open),
		"walkable_count": float(walkable_count),
	}


def _fitness(metrics: Dict[str, float]) -> float:
	open_ratio = metrics["open_ratio"]
	reachable_ratio = metrics["reachable_ratio"]
	reachable_count = metrics["reachable_count"]
	edge_open = metrics["edge_open"]
	target_open = 0.45

	return (
		reachable_ratio * 5.0
		+ reachable_count / 500.0
		- abs(open_ratio - target_open) * 4.0
		- edge_open * 0.15
	)


def _profile_tree_score(metrics: Dict[str, float], profile: Dict[str, object]) -> float:
	level = int(profile.get("level", 1) or 1)
	kills = profile.get("monster_kills", {}) or {}
	skills = profile.get("items_used", {}) or {}
	kill_total = sum(int(value) for value in kills.values()) if isinstance(kills, dict) else 0
	skill_total = sum(int(value) for value in skills.values()) if isinstance(skills, dict) else 0

	open_ratio = metrics["open_ratio"]
	reachable_ratio = metrics["reachable_ratio"]
	reachable_count = metrics["reachable_count"]

	if level <= 2:
		return reachable_ratio * 4.5 + (1.0 - abs(open_ratio - 0.38)) * 2.0 - reachable_count / 1500.0
	if level <= 5:
		return reachable_ratio * 4.0 + (1.0 - abs(open_ratio - 0.48)) * 2.5 + (kill_total + skill_total) / 50.0
	return reachable_ratio * 3.5 + (1.0 - abs(open_ratio - 0.58)) * 2.5 + reachable_count / 1200.0 + (kill_total + skill_total) / 60.0


def _choose_entity_positions(
	reachable: Set[Coordinate],
	start: Coordinate,
	rng: random.Random,
) -> Tuple[Coordinate, Coordinate, List[Coordinate], List[Coordinate], List[Coordinate]]:
	ordered = _furthest_tiles(reachable, start)
	treasure_position = ordered[0] if ordered else start
	door_position = ordered[1] if len(ordered) > 1 else treasure_position

	item_slots = [coord for coord in ordered[2:] if abs(coord[0] - start[0]) + abs(coord[1] - start[1]) >= 8]
	monster_slots = [coord for coord in ordered[3:] if abs(coord[0] - treasure_position[0]) + abs(coord[1] - treasure_position[1]) >= 2]

	rng.shuffle(item_slots)
	rng.shuffle(monster_slots)

	return treasure_position, door_position, item_slots[:8], monster_slots[:12], ordered


def _make_monster(row: int, col: int, guarding: bool, spawn_at: float, treasure_position: Coordinate) -> Dict[str, object]:
	return {
		"kind": "blue_circle",
		"row": row,
		"col": col,
		"hp": 3 if guarding else 2,
		"speed": 1.0 if guarding else 1.4,
		"guarding": guarding,
		"spawn_at": spawn_at,
		"target": treasure_position,
	}


def _build_generated_map(
	grid: Sequence[Sequence[int]],
	metrics: Dict[str, float],
	profile: Dict[str, object],
	rng: random.Random,
) -> GeneratedMap:
	tiles = [list(row) for row in grid]
	start = _find_spawn_tile(tiles)
	reachable = _bfs_reachable(tiles, start)

	if not reachable:
		return GeneratedMap(len(tiles[0]), len(tiles), tiles, start, start, start)

	treasure_position, door_position, item_slots, monster_slots, ordered = _choose_entity_positions(reachable, start, rng)
	items: List[Dict[str, object]] = []
	item_kinds = [TILE_KEY, TILE_POTION, TILE_POWER]

	for index, (row, col) in enumerate(item_slots[: max(3, len(item_slots) // 3)]):
		kind = item_kinds[index % len(item_kinds)]
		items.append({"kind": kind, "row": row, "col": col, "quantity": 1})
		tiles[row][col] = kind

	tiles[treasure_position[0]][treasure_position[1]] = TILE_TREASURE

	guarded_positions = _guard_positions_near_treasure(reachable, treasure_position, start)
	monsters: List[Dict[str, object]] = []
	spawn_schedule: List[Dict[str, object]] = []

	for row, col in guarded_positions[:4]:
		if (row, col) == treasure_position:
			continue
		if _a_star_path_exists(tiles, (row, col), start):
			monsters.append(_make_monster(row, col, True, 0.0, treasure_position))

	if not monsters:
		for row, col in item_slots:
			if (row, col) != treasure_position and _a_star_path_exists(tiles, (row, col), start):
				monsters.append(_make_monster(row, col, True, 0.0, treasure_position))
				break

	spawn_delay = 2.5
	for index, (row, col) in enumerate(monster_slots[:8]):
		if not _a_star_path_exists(tiles, (row, col), start):
			continue
		monster = _make_monster(row, col, False, spawn_delay + index * 3.0, treasure_position)
		spawn_schedule.append({"spawn_at": monster["spawn_at"], "monster": monster})

	if not spawn_schedule and monster_slots:
		row, col = monster_slots[0]
		if _a_star_path_exists(tiles, (row, col), start):
			monster = _make_monster(row, col, False, 4.0, treasure_position)
			spawn_schedule.append({"spawn_at": 4.0, "monster": monster})

	if not monsters and guarded_positions:
		row, col = guarded_positions[0]
		if _a_star_path_exists(tiles, (row, col), start):
			monsters.append(_make_monster(row, col, True, 0.0, treasure_position))

	door_candidates = [coord for coord in ordered if coord != treasure_position]
	for candidate in door_candidates:
		if _a_star_path_exists(tiles, candidate, start):
			door_position = candidate
			break

	if door_position == treasure_position:
		for candidate in reachable:
			if candidate != treasure_position and _a_star_path_exists(tiles, candidate, start):
				door_position = candidate
				break

	return GeneratedMap(
		width=len(tiles[0]),
		height=len(tiles),
		tiles=tiles,
		player_spawn=start,
		door_position=door_position,
		treasure_position=treasure_position,
		items=items,
		monsters=monsters,
		spawn_schedule=spawn_schedule,
		reachable_tiles=reachable,
	)


def _adjacent_walkable_tiles(grid: Sequence[Sequence[int]], origin: Coordinate) -> List[Coordinate]:
	row, col = origin
	result: List[Coordinate] = []
	for next_row, next_col in _neighbors(row, col):
		if 0 <= next_row < len(grid) and 0 <= next_col < len(grid[0]) and grid[next_row][next_col] in WALKABLE_TILES:
			result.append((next_row, next_col))
	if not result:
		result.append(origin)
	return result


def _guard_positions_near_treasure(
	reachable: Set[Coordinate],
	treasure_position: Coordinate,
	start: Coordinate,
) -> List[Coordinate]:
	ordered = sorted(
		reachable,
		key=lambda coord: (
			abs(coord[0] - treasure_position[0]) + abs(coord[1] - treasure_position[1]),
			abs(coord[0] - start[0]) + abs(coord[1] - start[1]),
		),
	)
	return [coord for coord in ordered if coord != treasure_position]
