from __future__ import annotations

import json
import random
import secrets
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from astar import path_exists
from bfs import evaluate, find_spawn_tile, repair_connectivity, reachable_tiles
from cellularautomata import smooth
from decisiontree import choose_best_candidate
from geneticalgorithm import crossover, generate_population, mutate


TILE_WALL = 0
TILE_STONE = 1
TILE_GROUND = 2
TILE_WATER = 3
TILE_TREASURE = 4
TILE_POTION = 5
TILE_KEY = 6
TILE_POWER = 7


def main() -> None:
	width = 40
	height = 30
	seed = secrets.randbits(64)
	rng = random.Random(seed)
	profile = {
		"level": 9,
		"monster_kills": {"slime": 5, "bat": 2},
		"skill_usage": {"slash": 12, "fireball": 4},
	}

	population = generate_population(width, height, population_size=8, rng=rng)
	candidates: List[Dict[str, object]] = []

	for index, grid in enumerate(population):
		# Keep GA + cellular automata explicit in the demo pipeline.
		smoothed = smooth(grid, steps=2 + index // 3)
		repaired = repair_connectivity(smoothed)
		metrics = evaluate(repaired)
		candidates.append({"grid": repaired, "metrics": metrics})

	best = choose_best_candidate(candidates, profile)
	grid = [row[:] for row in best["grid"]]
	spawn = find_spawn_tile(grid)
	reachable = reachable_tiles(grid, spawn)

	grid, items, monsters, door, treasure = place_game_data(grid, spawn, reachable, rng)
	result_path = Path(__file__).with_name("result.txt")
	write_result(result_path, seed, grid, best["metrics"], spawn, door, treasure, items, monsters)


def place_game_data(
	grid: List[List[int]],
	spawn: Tuple[int, int],
	reachable: Sequence[Tuple[int, int]],
	rng: random.Random,
) -> Tuple[List[List[int]], List[Dict[str, int]], List[Dict[str, object]], Tuple[int, int], Tuple[int, int]]:
	reachable_list = list(reachable)
	reachable_list.sort(key=lambda coord: abs(coord[0] - spawn[0]) + abs(coord[1] - spawn[1]), reverse=True)

	treasure = reachable_list[0] if reachable_list else spawn
	door = next((coord for coord in reachable_list[1:] if coord != treasure), treasure)

	items: List[Dict[str, int]] = []
	item_tiles = [TILE_KEY, TILE_POTION, TILE_POWER]
	for index, coord in enumerate(reachable_list[2:8]):
		row, col = coord
		if coord in (spawn, treasure, door):
			continue
		tile_id = item_tiles[index % len(item_tiles)]
		grid[row][col] = tile_id
		items.append({"kind": tile_id, "row": row, "col": col})

	grid[treasure[0]][treasure[1]] = TILE_TREASURE
	monsters: List[Dict[str, object]] = []

	for coord in reachable_list[3:7]:
		if coord in (spawn, treasure, door):
			continue
		if path_exists(grid, coord, spawn):
			monsters.append({
				"kind": "blue_circle",
				"row": coord[0],
				"col": coord[1],
				"guarding": True,
			})

	for offset, coord in enumerate(reachable_list[7:15]):
		if coord in (spawn, treasure, door):
			continue
		if path_exists(grid, coord, spawn):
			monsters.append({
				"kind": "blue_circle",
				"row": coord[0],
				"col": coord[1],
				"guarding": False,
				"spawn_at": 2.5 + offset * 3.0,
			})

	return grid, items, monsters, door, treasure


def write_result(
	path: Path,
	seed: int,
	grid: Sequence[Sequence[int]],
	metrics: Dict[str, float],
	spawn: Tuple[int, int],
	door: Tuple[int, int],
	treasure: Tuple[int, int],
	items: Sequence[Dict[str, int]],
	monsters: Sequence[Dict[str, object]],
) -> None:
	lines = []
	lines.append(f"seed={seed}")
	lines.append("matrix=")
	for row in grid:
		lines.append(" ".join(str(tile) for tile in row))
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
	main()