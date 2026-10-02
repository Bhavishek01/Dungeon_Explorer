from __future__ import annotations

import random
from typing import Dict, List, Sequence, Set, Tuple

from .astar import path_exists
from .bfs import farthest_reachable_tile
from .constants import (
    ENVIRONMENT_ROOT,
    ITEM_ROOT,
    MONSTER_ROOT,
    TILE_BASIC_SCROLL,
    TILE_FLOOR,
    TILE_LAVA,
    TILE_KEY,
    TILE_RARE_SCROLL,
    TILE_TREASURE,
    TILE_WALL,
    TILE_WATER,
)


Coordinate = Tuple[int, int]


def place_entities(
    grid: List[List[int]],
    spawn: Coordinate,
    reachable: Sequence[Coordinate],
    rng: random.Random,
    monster_limit: int = 12,
) -> Dict[str, object]:
    reachable_list = list(reachable)
    reachable_list.sort(key=lambda coord: abs(coord[0] - spawn[0]) + abs(coord[1] - spawn[1]), reverse=True)

    excluded: Set[Coordinate] = {spawn}
    door_key_coord = farthest_reachable_tile(grid, spawn)
    excluded.add(door_key_coord)
    door_coord = farthest_reachable_tile(grid, door_key_coord, exclude=excluded)
    excluded.add(door_coord)

    treasures = place_treasures(grid, reachable_list, excluded, rng)
    excluded.update((treasure["row"], treasure["col"]) for treasure in treasures)

    keys = place_keys(grid, reachable_list, excluded, rng, door_key_coord, treasures)
    excluded.update((key["row"], key["col"]) for key in keys)

    scrolls = place_scrolls(grid, reachable_list, excluded, rng)
    excluded.update((scroll["row"], scroll["col"]) for scroll in scrolls)

    monsters = place_monsters(
        grid,
        reachable_list,
        excluded,
        rng,
        spawn,
        door_key_coord,
        door_coord,
        treasures,
        monster_limit,
    )
    wall_lights = place_wall_lights(grid, rng)
    decorations = place_environment_decorations(grid, reachable_list, excluded, rng)

    return {
        "door_key": {
            "row": door_key_coord[0],
            "col": door_key_coord[1],
            "kind": "door_key",
            "image": rel_path("items", "door_key.png"),
            "collected": False,
        },
        "door": {
            "row": door_coord[0],
            "col": door_coord[1],
            "state": "locked",
            "closed_image": rel_path("items", "door.png"),
            "open_image": rel_path("items", "door open.png"),
        },
        "treasures": treasures,
        "keys": keys,
        "scrolls": scrolls,
        "monsters": monsters,
        "wall_lights": wall_lights,
        "decorations": decorations,
    }


def place_treasures(
    grid: List[List[int]],
    reachable: Sequence[Coordinate],
    excluded: Set[Coordinate],
    rng: random.Random,
) -> List[Dict[str, object]]:
    candidates = [coord for coord in reachable if coord not in excluded]
    rng.shuffle(candidates)
    treasures: List[Dict[str, object]] = []
    variants = [
        ("bow_gun", rel_path("items", "bow gun.png"), {"id": "bow_gun", "name": "Bow Gun", "quantity": 1}),
        ("light", rel_path("items", "light.png"), {"id": "light", "name": "Light", "quantity": 1}),
    ]

    treasure_count = min(len(candidates), rng.randint(2, 3))
    for index, coord in enumerate(candidates[:treasure_count]):
        row, col = coord
        reward_kind, reward_image, reward_item = rng.choice(variants)
        key_kind = "key"
        grid[row][col] = TILE_TREASURE
        treasures.append(
            {
                "row": row,
                "col": col,
                "state": "closed",
                "open_variant": reward_kind,
                "required_key": key_kind,
                "closed_image": rel_path("items", "treasure_close.png"),
                "open_image": reward_image,
                "reward_image": reward_image,
                "reward_item": reward_item,
            }
        )

    return treasures


def place_keys(
    grid: List[List[int]],
    reachable: Sequence[Coordinate],
    excluded: Set[Coordinate],
    rng: random.Random,
    door_key_coord: Coordinate,
    treasures: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    keys: List[Dict[str, object]] = []

    choices = [coord for coord in reachable if coord not in excluded]
    rng.shuffle(choices)

    for index, treasure in enumerate(treasures):
        target = (treasure["row"], treasure["col"])
        key_kind = treasure["required_key"]
        available = [coord for coord in choices if coord not in excluded]
        position = max(
            available,
            key=lambda coord: abs(coord[0] - target[0]) + abs(coord[1] - target[1]),
            default=None,
        )
        if position is None:
            continue
        row, col = position
        grid[row][col] = TILE_KEY
        excluded.add(position)
        keys.append(
            {
                "row": row,
                "col": col,
                "kind": key_kind,
                "image": rel_path("items", "key.png"),
                "collected": False,
            }
        )

    grid[door_key_coord[0]][door_key_coord[1]] = TILE_FLOOR
    return keys


def place_scrolls(
    grid: List[List[int]],
    reachable: Sequence[Coordinate],
    excluded: Set[Coordinate],
    rng: random.Random,
) -> List[Dict[str, object]]:
    choices = [coord for coord in reachable if coord not in excluded]
    rng.shuffle(choices)
    scrolls: List[Dict[str, object]] = []

    for index, coord in enumerate(choices[:6]):
        row, col = coord
        tile_id = TILE_BASIC_SCROLL if index < 4 else TILE_RARE_SCROLL
        kind, image, name = rng.choice(
            [
                ("health_gradual", rel_path("potions", "health +250 gradually.png"), "Health +250 Gradual"),
                ("stamina_gradual", rel_path("potions", "stamina +50 gradually.png"), "Stamina +250 Gradual"),
                ("stamina_50", rel_path("potions", "stamina +50 gradually.png"), "Stamina +50"),
                ("health_50", rel_path("potions", "health 50.png"), "Health +50"),
                ("health_full", rel_path("potions", "health full.png"), "Health Full"),
                ("stamina_full", rel_path("potions", "stamina full.png"), "Stamina Full"),
                ("stamina_250", rel_path("potions", "stamina +250.png"), "Stamina +250"),
            ]
        )
        grid[row][col] = tile_id
        scrolls.append({"row": row, "col": col, "kind": kind, "name": name, "tile": tile_id, "image": image, "collected": False})

    return scrolls


def place_monsters(
    grid: List[List[int]],
    reachable: Sequence[Coordinate],
    excluded: Set[Coordinate],
    rng: random.Random,
    spawn: Coordinate,
    door_key_coord: Coordinate,
    door_coord: Coordinate,
    treasures: Sequence[Dict[str, object]],
    monster_limit: int = 12,
) -> List[Dict[str, object]]:
    choices = [coord for coord in reachable if coord not in excluded]
    rng.shuffle(choices)
    monsters: List[Dict[str, object]] = []
    monster_types = [
        ("monster1", monster_frames("monster1")),
        ("monster2", monster_frames("monster2")),
        ("monster3", monster_frames("monster3")),
    ]

    guard_targets = [(rng.choice(choices), "monster3")] + [
        ((treasure["row"], treasure["col"]), monster_types[index % 2][0])
        for index, treasure in enumerate(treasures)
    ]
    for target, monster_kind in guard_targets:
        frames = dict(monster_types)[monster_kind]
        if monster_kind == "monster3":
            position = target
        else:
            position = nearest_free_position(choices, target, excluded, radius=6)
        if position is None:
            continue
        monsters.append(
            {
                "row": position[0],
                "col": position[1],
                "kind": monster_kind,
                "guarding": True,
                "frames": frames,
            }
        )
        excluded.add(position)

    for index, coord in enumerate(choices):
        if len(monsters) >= monster_limit:
            break
        if coord in excluded:
            continue
        monster_kind, frames = monster_types[(index + 1) % 2]
        if not path_exists(grid, coord, spawn):
            continue
        monsters.append(
            {
                "row": coord[0],
                "col": coord[1],
                "kind": monster_kind,
                "guarding": False,
                "spawn_at": 2.5 + index * 2.5,
                "frames": frames,
            }
        )
        excluded.add(coord)

    return monsters


def place_wall_lights(grid: List[List[int]], rng: random.Random) -> List[Dict[str, object]]:
    wall_lights: List[Dict[str, object]] = []
    height = len(grid)
    width = len(grid[0]) if height else 0
    for row in range(1, height - 1):
        for col in range(1, width - 1):
            if grid[row][col] == TILE_WALL and grid[row + 1][col] != TILE_WALL and rng.random() < 0.12:
                wall_lights.append({"row": row, "col": col, "kind": "wall_light", "image": rel_path("items", "wall_light.png")})
    return wall_lights


def place_environment_decorations(
    grid: List[List[int]],
    reachable: Sequence[Coordinate],
    excluded: Set[Coordinate],
    rng: random.Random,
) -> List[Dict[str, object]]:
    available = [coord for coord in reachable if coord not in excluded]
    rng.shuffle(available)
    decorations: List[Dict[str, object]] = []

    decorations.extend(place_liquid_cluster(grid, available, excluded, rng, center_image=rel_path("environment", "lava_fountain.png"), liquid_tile=TILE_LAVA, liquid_image=rel_path("environment", "lava.png"), center_count=1, cluster_radius=2, kind="lava"))
    decorations.extend(place_liquid_cluster(grid, available, excluded, rng, center_image=rel_path("environment", "water_fountain.png"), liquid_tile=TILE_WATER, liquid_image=rel_path("environment", "water.png"), center_count=1, cluster_radius=2, kind="water"))
    decorations.extend(place_liquid_cluster(grid, available, excluded, rng, center_image=None, liquid_tile=TILE_LAVA, liquid_image=rel_path("environment", "lava.png"), center_count=2, cluster_radius=1, kind="lava_group"))
    decorations.extend(place_liquid_cluster(grid, available, excluded, rng, center_image=None, liquid_tile=TILE_WATER, liquid_image=rel_path("environment", "water.png"), center_count=2, cluster_radius=1, kind="water_group"))

    return decorations


def place_liquid_cluster(
    grid: List[List[int]],
    available: List[Coordinate],
    excluded: Set[Coordinate],
    rng: random.Random,
    center_image: str | None,
    liquid_tile: int,
    liquid_image: str,
    center_count: int,
    cluster_radius: int,
    kind: str,
) -> List[Dict[str, object]]:
    decorations: List[Dict[str, object]] = []
    centers: List[Coordinate] = []
    candidates = [coord for coord in available if coord not in excluded]
    rng.shuffle(candidates)

    for center in candidates[:center_count]:
        centers.append(center)
        excluded.add(center)

    for center_row, center_col in centers:
        if center_image is not None:
            decorations.append({"row": center_row, "col": center_col, "kind": f"{kind}_fountain", "image": center_image})

        for row in range(center_row - cluster_radius, center_row + cluster_radius + 1):
            for col in range(center_col - cluster_radius, center_col + cluster_radius + 1):
                if not (0 <= row < len(grid) and 0 <= col < len(grid[0])):
                    continue
                if (row, col) in excluded:
                    continue
                if abs(row - center_row) + abs(col - center_col) > cluster_radius:
                    continue
                grid[row][col] = liquid_tile
                decorations.append({"row": row, "col": col, "kind": kind, "image": liquid_image})
                excluded.add((row, col))

    return decorations


def nearest_free_position(
    choices: Sequence[Coordinate],
    target: Coordinate,
    excluded: Set[Coordinate],
    radius: int,
) -> Coordinate | None:
    best = None
    best_distance = None
    for coord in choices:
        if coord in excluded:
            continue
        distance = abs(coord[0] - target[0]) + abs(coord[1] - target[1])
        if distance > radius:
            continue
        if best is None or distance < best_distance:
            best = coord
            best_distance = distance
    return best


def monster_frames(monster_name: str) -> List[str]:
    return [rel_path("monster", f"{monster_name}_move{i}.png") for i in range(1, 5)]


def rel_path(folder: str, filename: str) -> str:
    return (ITEM_ROOT.parent / folder / filename).as_posix()
