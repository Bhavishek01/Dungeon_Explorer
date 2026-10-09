from __future__ import annotations

import json
import random
import secrets

from geneticalgorithm import generate_population
from pipeline_io import stage_dir, write_grid, write_json

WIDTH = 81
HEIGHT = 81
POPULATION_SIZE = 8


if __name__ == "__main__":
    output = stage_dir(1, "population")
    seed = secrets.randbits(64)
    population = generate_population(WIDTH, HEIGHT, POPULATION_SIZE, random.Random(seed))
    for index, grid in enumerate(population, start=1):
        write_grid(output / f"candidate_{index:02d}.txt", grid)
    write_json(output / "metadata.json", {"seed": seed, "width": WIDTH, "height": HEIGHT, "population_size": POPULATION_SIZE})
    print(f"Wrote {POPULATION_SIZE} candidate layouts to {output}")
