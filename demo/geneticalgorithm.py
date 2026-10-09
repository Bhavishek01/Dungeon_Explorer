from __future__ import annotations

import random
from typing import List, Sequence


TileGrid = List[List[int]]


def seed_layout(width: int, height: int, rng: random.Random) -> TileGrid:
	grid = [[0 for _ in range(width)] for _ in range(height)]
	for row in range(1, height - 1):
		for col in range(1, width - 1):
			roll = rng.random()
			if roll < 0.58:
				grid[row][col] = 2
			elif roll < 0.68:
				grid[row][col] = 3
			elif roll < 0.80:
				grid[row][col] = 1
			else:
				grid[row][col] = 0
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
				if roll < 0.60:
					mutated[row][col] = 2
				elif roll < 0.82:
					mutated[row][col] = 3
				elif roll < 0.93:
					mutated[row][col] = 1
				else:
					mutated[row][col] = 0

	return mutated
