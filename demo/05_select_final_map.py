from __future__ import annotations

from decisiontree import choose_best_candidate
from pipeline_io import read_grid, read_json, stage_dir, write_grid, write_json


if __name__ == "__main__":
    source = stage_dir(4, "repaired_layouts")
    output = stage_dir(5, "selected_map")
    profile = {"level": 9, "monster_kills": {"slime": 5, "bat": 2}, "skill_usage": {"slash": 12, "fireball": 4}}
    candidates = []
    for source_path in sorted(source.glob("candidate_*.txt")):
        candidates.append({"grid": read_grid(source_path), "metrics": read_json(source / f"{source_path.stem}_metrics.json")})
    best = choose_best_candidate(candidates, profile)
    write_grid(output / "selected_grid.txt", best["grid"])
    write_json(output / "selection.json", {"profile": profile, "metrics": best["metrics"]})
    print(f"Wrote selected map to {output}")
