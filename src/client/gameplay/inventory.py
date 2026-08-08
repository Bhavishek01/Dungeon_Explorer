from __future__ import annotations

from typing import Dict, List, Optional


def add_item(items: List[Dict[str, object]], item_id: str, name: str, quantity: int = 1) -> None:
    for item in items:
        if item.get("id") == item_id:
            item["quantity"] = int(item.get("quantity", 0)) + quantity
            return

    items.append({"id": item_id, "name": name, "quantity": quantity})


def count_item(items: List[Dict[str, object]], item_id: str) -> int:
    for item in items:
        if item.get("id") == item_id:
            return int(item.get("quantity", 0))
    return 0


def consume_item(items: List[Dict[str, object]], item_id: str, quantity: int = 1) -> bool:
    for item in items:
        if item.get("id") != item_id:
            continue

        current_quantity = int(item.get("quantity", 0))
        if current_quantity < quantity:
            return False

        remaining = current_quantity - quantity
        if remaining > 0:
            item["quantity"] = remaining
        else:
            items.remove(item)
        return True

    return False


def label_for_kind(kind: str) -> str:
    labels = {
        "door_key": "Door Key",
        "treasure_key_1": "Treasure Key I",
        "treasure_key_2": "Treasure Key II",
        "basic_scroll": "Basic Scroll",
        "rare_scroll": "Rare Scroll",
        "rare_scroll_reward": "Rare Scroll",
        "basic_scroll_reward": "Basic Scroll",
    }
    return labels.get(kind, kind.replace("_", " ").title())
