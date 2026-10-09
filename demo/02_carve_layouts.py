from __future__ import annotations

import random

from layout import carve_nine_sector_maze
from pipeline_io import read_grid, read_json, stage_dir, write_grid


if __name__ == "__main__":
    metadata = read_json(stage_dir(1, "population") / "metadata.json")
    source = stage_dir(1, "population")
    output = stage_dir(2, "carved_layouts")
    rng = random.Random(int(metadata["seed"]) + 2)
    for source_path in sorted(source.glob("candidate_*.txt")):
        grid = carve_nine_sector_maze(read_grid(source_path), rng)
        write_grid(output / source_path.name, grid)
    print(f"Wrote carved layouts to {output}")
