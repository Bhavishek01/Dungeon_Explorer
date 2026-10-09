from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence


DEMO_DIR = Path(__file__).resolve().parent
STAGES_DIR = DEMO_DIR / "stages"


def stage_dir(number: int, name: str) -> Path:
    directory = STAGES_DIR / f"{number:02d}_{name}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def write_grid(path: Path, grid: Sequence[Sequence[int]]) -> None:
    path.write_text(
        "\n".join(" ".join(str(tile) for tile in row) for row in grid) + "\n",
        encoding="utf-8",
    )


def read_grid(path: Path) -> list[list[int]]:
    return [[int(value) for value in line.split()] for line in path.read_text(encoding="utf-8").splitlines()]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))
