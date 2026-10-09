from __future__ import annotations

from bfs import evaluate, repair_connectivity
from pipeline_io import read_grid, stage_dir, write_grid, write_json


if __name__ == "__main__":
    source = stage_dir(3, "smoothed_layouts")
    output = stage_dir(4, "repaired_layouts")
    for source_path in sorted(source.glob("candidate_*.txt")):
        repaired = repair_connectivity(read_grid(source_path))
        write_grid(output / source_path.name, repaired)
        write_json(output / f"{source_path.stem}_metrics.json", evaluate(repaired))
    print(f"Wrote repaired layouts and BFS metrics to {output}")
