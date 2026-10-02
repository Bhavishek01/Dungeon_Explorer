from __future__ import annotations

from typing import Dict, Sequence


def mine_recent_rules(profile: Dict[str, object]) -> Dict[str, float]:
    """Mine pair associations from the player's five most recent games."""
    history = profile.get("last_five_games", [])
    if not isinstance(history, list):
        return {}

    transactions = []
    for game in history[-5:]:
        if not isinstance(game, dict):
            continue
        killed = int(game.get("monsters_killed", 0) or 0)
        outcome = "outcome:clear" if game.get("cleared", False) else "outcome:loss"
        performance = "performance:high" if killed >= 8 else "performance:low"
        items = game.get("items", [])
        transaction = {outcome, performance}
        if isinstance(items, list):
            transaction.update(f"item:{item}" for item in items)
        transactions.append(transaction)

    rules = {}
    for antecedent, consequent, name in (
        ("performance:high", "outcome:clear", "high_kill_clear"),
        ("performance:low", "outcome:loss", "low_kill_loss"),
    ):
        antecedent_count = sum(antecedent in transaction for transaction in transactions)
        if not antecedent_count:
            continue
        matching_count = sum(
            antecedent in transaction and consequent in transaction
            for transaction in transactions
        )
        rules[name] = matching_count / antecedent_count
    return rules


def monster_limit_for_profile(profile: Dict[str, object]) -> int:
    """Return the next map's monster limit from recent association rules."""
    history = profile.get("last_five_games", [])
    if not isinstance(history, list) or not history:
        return 12

    rules = mine_recent_rules(profile)
    loss_streak = 0
    for game in reversed(history[-5:]):
        if not isinstance(game, dict) or game.get("cleared", False):
            break
        loss_streak += 1

    multiplier = 1.0
    if loss_streak >= 2 and rules.get("low_kill_loss", 0.0) >= 0.5:
        multiplier = 1.35 + min(0.2, (loss_streak - 2) * 0.05)
    elif rules.get("high_kill_clear", 0.0) >= 0.5:
        multiplier = 1.15

    return max(1, min(18, round(12 * multiplier)))


def score_candidate(metrics: Dict[str, float], profile: Dict[str, object]) -> float:
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


def choose_best_candidate(candidates: Sequence[Dict[str, object]], profile: Dict[str, object]) -> Dict[str, object]:
    return max(
        candidates,
        key=lambda candidate: (
            score_candidate(candidate["metrics"], profile),
            candidate["metrics"]["reachable_ratio"],
        ),
    )
