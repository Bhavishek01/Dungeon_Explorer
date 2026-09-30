from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .bfs import evaluate, find_spawn_tile, reachable_tiles, repair_connectivity
from .cellular_automata import smooth
from .constants import DEFAULT_GENERATIONS, DEFAULT_MAP_HEIGHT, DEFAULT_MAP_WIDTH, DEFAULT_POPULATION_SIZE
from .decision_tree import choose_best_candidate
from .genetic_algorithm import crossover, generate_population, mutate
from .layout import carve_nine_sector_maze
from .placement import place_entities
from .types import GeneratedWorld


def generate_map(
    width: int = DEFAULT_MAP_WIDTH,
    height: int = DEFAULT_MAP_HEIGHT,
    profile: Dict[str, object] | None = None,
    seed: object | None = None,
) -> GeneratedWorld:
    rng = random.Random(seed)
    profile = profile or {}

    population = generate_population(width, height, population_size=DEFAULT_POPULATION_SIZE, rng=rng)
    candidates: List[Dict[str, object]] = []

    for generation in range(DEFAULT_GENERATIONS):
        scored_population: List[Dict[str, object]] = []
        for grid in population:
            maze_grid = carve_nine_sector_maze(grid, rng)
            smoothed = smooth(maze_grid, steps=1 + generation // 2)
            repaired = repair_connectivity(smoothed)
            metrics = evaluate(repaired)
            scored_population.append({"grid": repaired, "metrics": metrics})

        candidates.extend(scored_population)
        scored_population.sort(key=lambda candidate: score_key(candidate["metrics"], profile), reverse=True)
        population = breed_next_population(scored_population, rng, generation)

    best = choose_best_candidate(candidates, profile)
    tiles = [row[:] for row in best["grid"]]
    spawn = find_spawn_tile(tiles)
    reachable = reachable_tiles(tiles, spawn)
    entities = place_entities(tiles, spawn, sorted(reachable), rng)
    active_monsters = [monster for monster in entities["monsters"] if monster.get("spawn_at") is None]
    spawn_schedule = [
        {"spawn_at": monster["spawn_at"], "monster": monster}
        for monster in entities["monsters"]
        if monster.get("spawn_at") is not None
    ]

    return GeneratedWorld(
        width=width,
        height=height,
        tiles=tiles,
        player_spawn=spawn,
        door_key=entities["door_key"],
        door=entities["door"],
        treasures=entities["treasures"],
        keys=entities["keys"],
        scrolls=entities["scrolls"],
        monsters=active_monsters,
        wall_lights=entities["wall_lights"],
        decorations=entities["decorations"],
        spawn_schedule=spawn_schedule,
        reachable_tiles=reachable,
    )


def score_key(metrics: Dict[str, float], profile: Dict[str, object]) -> float:
    level = int(profile.get("level", 1) or 1)
    kills = profile.get("monster_kills", {}) or {}
    skills = profile.get("items_used", {}) or {}
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
    scored_population: List[Dict[str, object]],
    rng: random.Random,
    generation: int,
) -> List[List[List[int]]]:
    survivors = [candidate["grid"] for candidate in scored_population[:2]]
    if len(survivors) == 1:
        survivors = survivors * 2

    children: List[List[List[int]]] = [survivors[0], survivors[1]]
    mutation_rate = 0.06 + generation * 0.02

    while len(children) < DEFAULT_POPULATION_SIZE:
        parent_a, parent_b = rng.sample(survivors, 2)
        child = crossover(parent_a, parent_b, rng)
        child = mutate(child, rng, mutation_rate)
        children.append(child)

    return children
