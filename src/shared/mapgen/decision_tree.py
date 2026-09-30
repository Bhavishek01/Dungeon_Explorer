from __future__ import annotations

from typing import Dict, Sequence


def score_candidate(metrics: Dict[str, float], profile: Dict[str, object]) -> float:
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


def choose_best_candidate(candidates: Sequence[Dict[str, object]], profile: Dict[str, object]) -> Dict[str, object]:
    return max(
        candidates,
        key=lambda candidate: (
            score_candidate(candidate["metrics"], profile),
            candidate["metrics"]["reachable_ratio"],
        ),
    )
