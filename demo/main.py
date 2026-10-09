from __future__ import annotations

import json
import random
import secrets
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from astar import path_exists
from bfs import distance_map, evaluate, farthest_reachable_tile, find_spawn_tile, repair_connectivity, reachable_tiles
from cellularautomata import smooth
from decisiontree import choose_best_candidate
from geneticalgorithm import crossover, generate_population, mutate


TILE_WALL = 0
TILE_TRAP = 1
TILE_FLOOR = 2
TILE_WATER = 3
TILE_TREASURE = 4
TILE_BASIC_SCROLL = 5
TILE_KEY = 6
TILE_RARE_SCROLL = 7

SECTOR_COUNT = 3
MAP_WIDTH = 81
MAP_HEIGHT = 81
POPULATION_SIZE = 9
GENERATIONS = 4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TILES_ROOT = PROJECT_ROOT / "src" / "shared" / "tiles"
ENV_ROOT = TILES_ROOT / "environment"
ITEM_ROOT = TILES_ROOT / "items"
MONSTER_ROOT = TILES_ROOT / "monster"
OUTPUT_DIR = Path(__file__).with_name("map_output")


def main() -> None:
	seed = secrets.randbits(64)
	rng = random.Random(seed)
	OUTPUT_DIR.mkdir(exist_ok=True)
	profile = {
		"level": 9,
		"monster_kills": {"slime": 5, "bat": 2},
		"skill_usage": {"slash": 12, "fireball": 4},
	}

	population = generate_population(MAP_WIDTH, MAP_HEIGHT, population_size=POPULATION_SIZE, rng=rng)
	candidates: List[Dict[str, object]] = []
	for index, grid in enumerate(population, start=1):
		write_grid(OUTPUT_DIR / f"initial_candidate_{index:02d}.txt", grid)

	for generation in range(GENERATIONS):
		scored_population: List[Dict[str, object]] = []
		for index, grid in enumerate(population):
			maze_grid = carve_nine_sector_maze(grid, rng)
			write_grid(OUTPUT_DIR / f"generation_{generation + 1:02d}_candidate_{index + 1:02d}_carved.txt", maze_grid)
			smoothed = smooth(maze_grid, steps=1 + generation // 2)
			write_grid(OUTPUT_DIR / f"generation_{generation + 1:02d}_candidate_{index + 1:02d}_smoothed.txt", smoothed)
			repaired = repair_connectivity(smoothed)
			write_grid(OUTPUT_DIR / f"generation_{generation + 1:02d}_candidate_{index + 1:02d}_repaired.txt", repaired)
			metrics = evaluate(repaired)
			score = score_key(metrics, profile)
			write_json(
				OUTPUT_DIR / f"generation_{generation + 1:02d}_candidate_{index + 1:02d}_metrics.json",
				{"generation": generation + 1, "candidate": index + 1, "metrics": metrics, "score": score},
			)
			scored_population.append({"grid": repaired, "metrics": metrics, "score": score})

		candidates.extend(scored_population)
		scored_population.sort(key=lambda candidate: score_key(candidate["metrics"], profile), reverse=True)
		write_json(
			OUTPUT_DIR / f"generation_{generation + 1:02d}_ranking.json",
			[
				{"candidate": index + 1, "metrics": candidate["metrics"], "score": candidate["score"]}
				for index, candidate in enumerate(scored_population)
			],
		)
		population = breed_next_population(scored_population, rng, generation)
		for index, grid in enumerate(population, start=1):
			write_grid(OUTPUT_DIR / f"generation_{generation + 1:02d}_next_candidate_{index:02d}.txt", grid)

	best = choose_best_candidate(candidates, profile)
	grid = [row[:] for row in best["grid"]]
	write_grid(OUTPUT_DIR / "selected_grid.txt", grid)
	spawn = find_spawn_tile(grid)
	distances = distance_map(grid, spawn)

	entities = place_entities(grid, spawn, distances, rng)
	write_json(OUTPUT_DIR / "final_entities.json", entities)
	write_json(
		OUTPUT_DIR / "generation_summary.json",
		{
			"seed": seed,
			"size": [MAP_WIDTH, MAP_HEIGHT],
			"population_size": POPULATION_SIZE,
			"generations": GENERATIONS,
			"selected_metrics": best["metrics"],
			"spawn": spawn,
		},
	)
	write_result(OUTPUT_DIR / "final_result.txt", seed, grid, best["metrics"], spawn, entities)
	write_result(Path(__file__).with_name("result.txt"), seed, grid, best["metrics"], spawn, entities)


def carve_nine_sector_maze(grid: Sequence[Sequence[int]], rng: random.Random) -> List[List[int]]:
	current = [[TILE_WALL for _ in range(len(grid[0]))] for _ in range(len(grid))]
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
			carve_sector(current, grid, sector_row, sector_col, sector_h, sector_w, rng)

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
	path_order = [
		(0, 0), (0, 1), (0, 2),
		(1, 2), (1, 1), (1, 0),
		(2, 0), (2, 1), (2, 2),
	]
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
	first_horizontal = rng.random() < 0.5
	segments = ["col", "row"] if first_horizontal else ["row", "col"]

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
					if grid[row][col] == TILE_FLOOR and rng.random() < 0.05:
						grid[row][col] = TILE_TRAP


def score_key(metrics: Dict[str, float], profile: Dict[str, object]) -> float:
	level = int(profile.get("level", 1) or 1)
	kills = profile.get("monster_kills", {}) or {}
	skills = profile.get("skill_usage", {}) or {}
	kill_total = sum(int(value) for value in kills.values()) if isinstance(kills, dict) else 0
	skill_total = sum(int(value) for value in skills.values()) if isinstance(skills, dict) else 0

	open_ratio = metrics["open_ratio"]
	reachable_ratio = metrics["reachable_ratio"]
	reachable_count = metrics["reachable_count"]

	if level <= 2:
		return reachable_ratio * 4.5 + (1.0 - abs(open_ratio - 0.42)) * 2.0 - reachable_count / 1500.0
	if level <= 5:
		return reachable_ratio * 4.0 + (1.0 - abs(open_ratio - 0.52)) * 2.5 + (kill_total + skill_total) / 50.0
	return reachable_ratio * 3.5 + (1.0 - abs(open_ratio - 0.62)) * 2.5 + reachable_count / 1200.0 + (kill_total + skill_total) / 60.0


def breed_next_population(
	scored_population: Sequence[Dict[str, object]],
	rng: random.Random,
	generation: int,
) -> List[List[List[int]]]:
	survivors = [candidate["grid"] for candidate in scored_population[:2]]
	children = [survivors[0], survivors[1]] if len(survivors) > 1 else [survivors[0]]
	mutation_rate = 0.06 + generation * 0.02

	while len(children) < POPULATION_SIZE:
		parent_a, parent_b = rng.sample(survivors, 2) if len(survivors) > 1 else (survivors[0], survivors[0])
		child = crossover(parent_a, parent_b, rng)
		child = mutate(child, rng, mutation_rate)
		children.append(child)

	return children


def place_entities(
	grid: List[List[int]],
	spawn: Tuple[int, int],
	distances: Dict[Tuple[int, int], int],
	rng: random.Random,
) -> Dict[str, object]:
	reachable = sorted(distances, key=lambda coord: (distances[coord], -coord[0], -coord[1]), reverse=True)
	excluded: set[Tuple[int, int]] = {spawn}

	door_key = farthest_reachable_tile(grid, spawn)
	excluded.add(door_key)
	door = farthest_reachable_tile(grid, door_key, exclude=excluded)
	excluded.add(door)

	treasures = place_treasures(grid, reachable, excluded, rng)
	excluded.update((treasure["row"], treasure["col"]) for treasure in treasures)

	keys = place_keys(grid, reachable, excluded, rng, door_key, treasures)
	excluded.update((key["row"], key["col"]) for key in keys)

	scrolls = place_scrolls(grid, reachable, excluded, rng)
	excluded.update((item["row"], item["col"]) for item in scrolls)

	monsters = place_monsters(grid, reachable, excluded, rng, door_key, treasures)
	wall_lights = place_wall_lights(grid, rng)

	return {
		"door_key": {"row": door_key[0], "col": door_key[1], "image": rel_path("items", "key.png")},
		"door": {
			"row": door[0],
			"col": door[1],
			"state": "locked",
			"closed_image": rel_path("items", "door.png"),
			"open_image": rel_path("items", "door open.png"),
		},
		"treasures": treasures,
		"keys": keys,
		"scrolls": scrolls,
		"monsters": monsters,
		"wall_lights": wall_lights,
	}


def place_treasures(
	grid: List[List[int]],
	reachable: Sequence[Tuple[int, int]],
	excluded: set[Tuple[int, int]],
	rng: random.Random,
) -> List[Dict[str, object]]:
	choices = [coord for coord in reachable if coord not in excluded]
	rng.shuffle(choices)
	results: List[Dict[str, object]] = []
	variants = [
		("item", rel_path("items", "treasure_open_item.png")),
		("nothing", rel_path("items", "treasure_open_nothing.png")),
	]

	for index, coord in enumerate(choices[:2]):
		row, col = coord
		variant_name, open_image = variants[index % len(variants)]
		grid[row][col] = TILE_TREASURE
		results.append({
			"row": row,
			"col": col,
			"state": "closed",
			"open_variant": variant_name,
			"closed_image": rel_path("items", "treasure_close.png"),
			"open_image": open_image,
		})

	return results


def place_keys(
	grid: List[List[int]],
	reachable: Sequence[Tuple[int, int]],
	excluded: set[Tuple[int, int]],
	rng: random.Random,
	door_key: Tuple[int, int],
	treasures: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
	results = [{"row": door_key[0], "col": door_key[1], "kind": "door_key", "image": rel_path("items", "key.png")}]
	nearby_targets = [
		(treasure["row"], treasure["col"])
		for treasure in treasures
	]
	choices = [coord for coord in reachable if coord not in excluded]
	rng.shuffle(choices)

	for index, target in enumerate(nearby_targets):
		for coord in choices:
			if coord == target:
				continue
			if abs(coord[0] - target[0]) + abs(coord[1] - target[1]) <= 4:
				results.append({
					"row": coord[0],
					"col": coord[1],
					"kind": f"treasure_key_{index + 1}",
					"image": rel_path("items", "key.png"),
				})
				break

	for key in results[1:]:
		grid[key["row"]][key["col"]] = TILE_KEY

	grid[door_key[0]][door_key[1]] = TILE_KEY
	return results


def place_scrolls(
	grid: List[List[int]],
	reachable: Sequence[Tuple[int, int]],
	excluded: set[Tuple[int, int]],
	rng: random.Random,
) -> List[Dict[str, object]]:
	choices = [coord for coord in reachable if coord not in excluded]
	rng.shuffle(choices)
	results: List[Dict[str, object]] = []
	variants = [
		("basic", rel_path("items", "basic scroll.png"), TILE_BASIC_SCROLL),
		("rare", rel_path("items", "rare scroll.png"), TILE_RARE_SCROLL),
	]

	for index, coord in enumerate(choices[:6]):
		row, col = coord
		kind_name, image_path, tile_id = variants[0 if index < 4 else 1]
		grid[row][col] = tile_id
		results.append({
			"row": row,
			"col": col,
			"kind": f"{kind_name}_scroll",
			"tile": tile_id,
			"image": image_path,
		})

	return results


def place_monsters(
	grid: List[List[int]],
	reachable: Sequence[Tuple[int, int]],
	excluded: set[Tuple[int, int]],
	rng: random.Random,
	door_key: Tuple[int, int],
	treasures: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
	choices = [coord for coord in reachable if coord not in excluded]
	rng.shuffle(choices)
	results: List[Dict[str, object]] = []
	monster_types = [
		("monster1", monster_frames("monster1")),
		("monster2", monster_frames("monster2")),
		("monster3", monster_frames("monster3")),
	]

	guard_targets = [(door_key[0], door_key[1])] + [(treasure["row"], treasure["col"]) for treasure in treasures]
	for index, target in enumerate(guard_targets):
		monster_type, frames = monster_types[index % len(monster_types)]
		position = nearest_free_position(choices, target, excluded)
		if position is None:
			continue
		results.append({
			"row": position[0],
			"col": position[1],
			"kind": monster_type,
			"guarding": True,
			"frames": frames,
		})
		excluded.add(position)

	for index, coord in enumerate(choices):
		if len(results) >= 12:
			break
		if coord in excluded:
			continue
		monster_type, frames = monster_types[(index + 1) % len(monster_types)]
		results.append({
			"row": coord[0],
			"col": coord[1],
			"kind": monster_type,
			"guarding": False,
			"spawn_at": 2.5 + index * 2.5,
			"frames": frames,
		})
		excluded.add(coord)

	return results


def place_wall_lights(grid: List[List[int]], rng: random.Random) -> List[Dict[str, object]]:
	results: List[Dict[str, object]] = []
	height = len(grid)
	width = len(grid[0]) if height else 0
	for row in range(1, height - 1):
		for col in range(1, width - 1):
			if grid[row][col] != TILE_WALL:
				continue
			if grid[row + 1][col] == TILE_FLOOR and rng.random() < 0.12:
				results.append({"row": row, "col": col, "kind": "wall_light", "image": rel_path("items", "wall_light.png")})
	return results


def nearest_free_position(
	choices: Sequence[Tuple[int, int]],
	target: Tuple[int, int],
	excluded: set[Tuple[int, int]],
) -> Tuple[int, int] | None:
	best = None
	best_distance = None
	for coord in choices:
		if coord in excluded:
			continue
		distance = abs(coord[0] - target[0]) + abs(coord[1] - target[1])
		if best is None or distance < best_distance:
			best = coord
			best_distance = distance
	return best


def monster_frames(monster_name: str) -> List[str]:
	return [rel_path("monster", f"{monster_name}_move{i}.png") for i in range(1, 5)]


def rel_path(folder: str, filename: str) -> str:
	return (TILES_ROOT / folder / filename).as_posix()


def write_grid(path: Path, grid: Sequence[Sequence[int]]) -> None:
	path.write_text(
		"\n".join(" ".join(str(tile) for tile in row) for row in grid) + "\n",
		encoding="utf-8",
	)


def write_json(path: Path, value: object) -> None:
	path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_result(
	path: Path,
	seed: int,
	grid: Sequence[Sequence[int]],
	metrics: Dict[str, float],
	spawn: Tuple[int, int],
	entities: Dict[str, object],
) -> None:
	lines: List[str] = []
	lines.append(f"seed={seed}")
	lines.append(f"size={len(grid[0])}x{len(grid)}")
	lines.append(f"sectors={SECTOR_COUNT}x{SECTOR_COUNT}")
	lines.append(f"sector_size={len(grid[0]) // SECTOR_COUNT}x{len(grid) // SECTOR_COUNT}")
	lines.append(f"spawn={spawn}")
	lines.append(f"metrics={json.dumps(metrics, sort_keys=True)}")
	lines.append(f"legend={json.dumps({'0': 'wall', '1': 'trap', '2': 'floor', '3': 'water', '4': 'treasure', '5': 'basic_scroll', '6': 'key', '7': 'rare_scroll'}, sort_keys=True)}")
	lines.append(f"door_key={json.dumps(entities['door_key'], sort_keys=True)}")
	lines.append(f"door={json.dumps(entities['door'], sort_keys=True)}")
	lines.append(f"treasures={json.dumps(entities['treasures'], sort_keys=True)}")
	lines.append(f"keys={json.dumps(entities['keys'], sort_keys=True)}")
	lines.append(f"scrolls={json.dumps(entities['scrolls'], sort_keys=True)}")
	lines.append(f"monsters={json.dumps(entities['monsters'], sort_keys=True)}")
	lines.append(f"wall_lights={json.dumps(entities['wall_lights'], sort_keys=True)}")
	lines.append("matrix=")
	for row in grid:
		lines.append(" ".join(str(tile) for tile in row))
	path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
	main()