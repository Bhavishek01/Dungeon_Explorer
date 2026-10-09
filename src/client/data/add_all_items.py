from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

CLIENT_DIR = Path(__file__).resolve().parents[1]
if str(CLIENT_DIR) not in sys.path:
    sys.path.insert(0, str(CLIENT_DIR))

from gameplay.inventory import starter_items


PROFILE_STORE = Path(__file__).resolve().with_name("profiles.json")


def add_missing_items() -> int:
    with PROFILE_STORE.open("r", encoding="utf-8") as handle:
        store = json.load(handle)

    added_count = 0
    changed = False
    for player in store.get("players", []):
        items = player.setdefault("items", [])
        starter_item_ids = {item["id"] for item in starter_items()}
        for item in items:
            if item.get("id") in starter_item_ids:
                if item.get("quantity") != 1:
                    changed = True
                item["quantity"] = 1
        existing_item_ids = {
            item.get("id")
            for item in items
            if isinstance(item, dict)
        }
        missing_items = [
            item
            for item in starter_items()
            if item["id"] not in existing_item_ids
        ]
        items.extend(deepcopy(item) for item in missing_items)
        added_count += len(missing_items)
        changed = changed or bool(missing_items)

    if changed:
        with PROFILE_STORE.open("w", encoding="utf-8") as handle:
            json.dump(store, handle, indent=2)
            handle.write("\n")

    return added_count


if __name__ == "__main__":
    print(f"Added {add_missing_items()} missing items to player profiles.")
