from __future__ import annotations

import json
import queue
import threading
from copy import deepcopy
from pathlib import Path

import config


class ClientSession:
    def __init__(self):
        self.connected = False
        self.events = queue.Queue()
        self._lock = threading.Lock()
        self._store_path = Path(__file__).resolve().parent / config.PROFILE_STORE_FILE
        self._store = {"players": []}

        self.player_id = None
        self.player_name = None
        self.player_class = None
        self._active_player = None

        self.connect()

    def connect(self, *_args, **_kwargs):
        self._load_store()
        self.connected = True
        return True

    def disconnect(self):
        self.clear_temporary_keys()
        self._save_store()
        self.connected = False

    def clear_temporary_keys(self, game_state=None):
        if game_state is not None:
            game_state["items"] = [
                item for item in game_state.get("items", [])
                if not str(item.get("id", "")).endswith("key")
                and not str(item.get("id", "")).startswith("treasure_key_")
            ]
        if self._active_player is not None:
            self._active_player["items"] = [
                item for item in self._active_player.get("items", [])
                if not str(item.get("id", "")).endswith("key")
                and not str(item.get("id", "")).startswith("treasure_key_")
            ]

    def discard_game_run(self, game_state):
        current_profile = deepcopy(game_state.get("profile", {}))
        baseline_profile = deepcopy(game_state.get("_run_start_profile", current_profile))
        baseline_profile["items_used"] = current_profile.get("items_used", {})
        baseline_profile["coins"] = current_profile.get("coins", baseline_profile.get("coins", 0))
        game_state["profile"] = baseline_profile
        game_state["active_item_effects"] = []
        self.clear_temporary_keys(game_state)
        self.commit_inventory_state(game_state)

    def commit_inventory_state(self, game_state):
        if self._active_player is None:
            return

        persistent_items = [
            deepcopy(item) for item in game_state.get("items", [])
            if not str(item.get("id", "")).endswith("key")
            and not str(item.get("id", "")).startswith("treasure_key_")
        ]
        self._active_player["items"] = persistent_items
        stored_profile = deepcopy(self._active_player.get("profile", {}))
        run_profile = game_state.get("profile", {})
        stored_profile["items_used"] = deepcopy(run_profile.get("items_used", stored_profile.get("items_used", {})))
        stored_profile["coins"] = int(run_profile.get("coins", stored_profile.get("coins", 0)))
        self._active_player["profile"] = stored_profile
        self._save_store()

    def send(self, message: str):
        tag, _, payload = message.partition("|")
        tag = tag.upper()

        if tag == "LOGIN":
            self.login(payload)
        elif tag == "REGISTER":
            self.register(payload)
        elif tag == "CLASS":
            self.send_class(payload)
        elif tag == "ENTER_GAME":
            self.enter_game()

    def reset_active_profile(self):
        self._store["players"] = []
        self._active_player = None
        self.player_id = None
        self.player_name = None
        self.player_class = None
        self._save_store()

    def has_players(self):
        return bool(self._store["players"])

    def list_players(self):
        return [deepcopy(player) for player in self._store["players"]]

    def select_player(self, player_id: str):
        player = self._find_player_by_id(player_id.strip())
        if player is None:
            return False
        self._set_active_player(player)
        self._save_store()
        return True

    def login(self, player_id: str):
        if self.select_player(player_id):
            player = self._active_player
        else:
            player = None
        if player is None:
            self.events.put({"type": "LOGIN_FAILED"})
            return

        self._set_active_player(player)
        self._save_store()
        self.events.put(self._snapshot_event("LOGIN_SUCCESS"))

    def register(self, player_name: str):
        player_name = player_name.strip()
        if not player_name:
            self.events.put({"type": "REGISTER_FAILED"})
            return

        existing = self._find_player_by_name(player_name)
        if existing is not None:
            self._set_active_player(existing)
            self._save_store()
            self.events.put(self._snapshot_event("REGISTER_SUCCESS"))
            return

        player = self._default_player(player_name)
        self._store["players"].append(player)
        self._set_active_player(player)
        self._save_store()
        self.events.put(self._snapshot_event("REGISTER_SUCCESS"))

    def send_class(self, class_name: str):
        class_key = class_name.strip()
        if not self._active_player or class_key not in config.PLAYER_CLASSES:
            return

        self._active_player["player_class"] = class_key
        self.player_class = class_key
        self._save_store()
        self.events.put(self._snapshot_event("CLASS_SUCCESS"))

    def enter_game(self):
        if self._active_player is None:
            return
        self._save_store()
        self.events.put(self._snapshot_event("ENTER_GAME_OK"))

    def commit_game_state(self, game_state):
        if self._active_player is None:
            return

        self._active_player["items"] = deepcopy(game_state.get("items", []))
        self._active_player["equipped"] = deepcopy(game_state.get("equipped", [0, 0, 0]))
        self._active_player["profile"] = deepcopy(game_state.get("profile", self._active_player.get("profile", {})))
        self._save_store()

    def get_active_profile_snapshot(self):
        if self._active_player is None:
            return {
                "player_id": self.player_id,
                "player_name": self.player_name,
                "player_class": self.player_class,
                "items": [],
                "equipped": [0, 0, 0],
                "profile": {
                    "level": 1,
                    "experience": 0,
                    "experience_required": config.PLAYER_INITIAL_EXPERIENCE_REQUIRED,
                    "monster_kills": {},
                    "items_used": {},
                    "coins": 0,
                    "items_used": {},
                },
            }

        return {
            "player_id": self._active_player["player_id"],
            "player_name": self._active_player["player_name"],
            "player_class": self._active_player.get("player_class"),
            "items": deepcopy(self._active_player.get("items", [])),
            "equipped": deepcopy(self._active_player.get("equipped", [0, 0, 0])),
            "profile": deepcopy(self._active_player.get("profile", {})),
        }

    def poll_events(self):
        drained = []
        while True:
            try:
                drained.append(self.events.get_nowait())
            except queue.Empty:
                break
        return drained

    def _snapshot_event(self, event_type: str):
        snapshot = self.get_active_profile_snapshot()
        return {
            "type": event_type,
            "id": snapshot["player_id"],
            "name": snapshot["player_name"],
            "class": snapshot["player_class"],
            "items": snapshot["items"],
            "equipped": snapshot["equipped"],
            "profile": snapshot["profile"],
        }

    def _default_player(self, player_name: str):
        player_id = self._new_player_id(player_name)
        return {
            "player_id": player_id,
            "player_name": player_name,
            "player_class": None,
            "items": [],
            "equipped": [0, 0, 0],
            "profile": {
                "level": 1,
                "experience": 0,
                "experience_required": config.PLAYER_INITIAL_EXPERIENCE_REQUIRED,
                "monster_kills": {},
                "items_used": {},
                "coins": 0,
                "items_used": {},
            },
        }

    def _set_active_player(self, player):
        self._active_player = player
        self.player_id = player["player_id"]
        self.player_name = player["player_name"]
        self.player_class = player.get("player_class")

    def _find_player_by_id(self, player_id: str):
        for player in self._store["players"]:
            if player.get("player_id") == player_id:
                return player
        return None

    def _find_player_by_name(self, player_name: str):
        for player in self._store["players"]:
            if player.get("player_name") == player_name:
                return player
        return None

    def _new_player_id(self, player_name: str):
        slug = "".join(character for character in player_name.upper() if character.isalnum())
        slug = slug[:8] or "PLAYER"

        suffix = 1
        while True:
            candidate = f"{slug}_{suffix:03d}"
            if self._find_player_by_id(candidate) is None:
                return candidate
            suffix += 1

    def _load_store(self):
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._store_path.exists():
            self._save_store()
            return

        try:
            with self._store_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            data = None

        if isinstance(data, dict):
            self._store["players"] = list(data.get("players", []))

    def _save_store(self):
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._store_path.open("w", encoding="utf-8") as handle:
                json.dump(self._store, handle, indent=2)