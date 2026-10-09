from __future__ import annotations

from cellularautomata import smooth
from pipeline_io import read_grid, stage_dir, write_grid


if __name__ == "__main__":
    source = stage_dir(2, "carved_layouts")
    output = stage_dir(3, "smoothed_layouts")
    for source_path in sorted(source.glob("candidate_*.txt")):
        write_grid(output / source_path.name, smooth(read_grid(source_path), steps=2))
    print(f"Wrote smoothed layouts to {output}")
