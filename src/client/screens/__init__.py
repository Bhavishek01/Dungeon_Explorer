# ============================================================
# screens/__init__.py
# Screen base class + ScreenManager — this is the CardLayout equivalent.
#
# Java: cardLayout.show(cardPanel, "gamemenu")
# Here: screen_manager.switch_to("menu", some_kwarg=value)
#
# Every screen module subclasses Screen and implements the four
# lifecycle hooks. ScreenManager owns exactly one active screen at a
# time and forwards events/update/draw to it, same as CardLayout only
# ever shows one card.
# ============================================================


class Screen:
    def __init__(self, manager, client, game_state):
        self.manager = manager        # ScreenManager, for switch_to()
        self.client = client          # ClientSession (shared, persists across screens)
        self.game_state = game_state  # dict shared across screens: player_id, name, class, level, etc.

    def on_enter(self, **kwargs):
        """Called every time this screen becomes active. kwargs = data passed via switch_to()."""
        pass

    def on_exit(self):
        """Called right before switching away from this screen."""
        pass

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class ScreenManager:
    def __init__(self, client, game_state):
        self.client = client
        self.game_state = game_state
        self._screens = {}
        self.current_key = None
        self.current = None

    def register(self, key, screen_cls):
        """Instantiate and register a screen under `key`."""
        self._screens[key] = screen_cls(self, self.client, self.game_state)

    def switch_to(self, key, **kwargs):
        if key not in self._screens:
            raise KeyError(f"No screen registered under '{key}'")
        if self.current is not None:
            self.current.on_exit()
        self.current_key = key
        self.current = self._screens[key]
        self.current.on_enter(**kwargs)

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self, surface):
        if self.current:
            self.current.draw(surface)
