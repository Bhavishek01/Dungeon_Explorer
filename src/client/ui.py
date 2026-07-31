# ============================================================
# ui.py — tiny reusable widgets shared by every screen.
#
# NOTE: this file isn't in structure.txt. Pygame has no built-in
# button/textbox like Swing's JButton/JTextField, and every single
# screen needs at least a button, so a shared widget module is the
# alternative to copy-pasting rect/click logic into all 8 screens.
# Move it under screens/ or elsewhere if you'd rather keep it there.
# ============================================================

import pygame as pg
import config


class Button:
    """A clickable rectangle with a label and a callback."""

    def __init__(self, rect, text, on_click=None, font=None, enabled=True):
        self.rect = pg.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.font = font or pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_MEDIUM, bold=True)
        self.enabled = enabled
        self.hovered = False

    def handle_event(self, event):
        if not self.enabled:
            return
        if event.type == pg.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.on_click:
                self.on_click()

    def draw(self, surface):
        if not self.enabled:
            color = config.BUTTON_DISABLED_COLOR
        elif self.hovered:
            color = config.BUTTON_HOVER_COLOR
        else:
            color = config.BUTTON_COLOR

        pg.draw.rect(surface, color, self.rect, border_radius=6)
        pg.draw.rect(surface, config.BUTTON_BORDER_COLOR, self.rect, width=2, border_radius=6)

        text_color = config.BUTTON_TEXT_COLOR if self.enabled else config.COLOR_GRAY
        label = self.font.render(self.text, True, text_color)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)


class TextInput:
    """A single-line text field. Click to focus, type to edit, Enter to submit."""

    def __init__(self, rect, font=None, placeholder="", max_length=24, on_submit=None, numeric=False):
        self.rect = pg.Rect(rect)
        self.font = font or pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_MEDIUM)
        self.text = ""
        self.placeholder = placeholder
        self.max_length = max_length
        self.on_submit = on_submit
        self.numeric = numeric
        self.active = False
        self._cursor_visible = True
        self._cursor_timer = 0.0

    def handle_event(self, event):
        if event.type == pg.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pg.KEYDOWN and self.active:
            if event.key == pg.K_RETURN:
                if self.on_submit:
                    self.on_submit(self.text)
            elif event.key == pg.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                ch = event.unicode
                if ch and len(self.text) < self.max_length:
                    if self.numeric and not ch.isdigit():
                        return
                    if ch.isprintable():
                        self.text += ch

    def update(self, dt):
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def draw(self, surface):
        pg.draw.rect(surface, config.INPUT_BG_COLOR, self.rect, border_radius=4)
        border_color = config.INPUT_ACTIVE_BORDER if self.active else config.INPUT_INACTIVE_BORDER
        pg.draw.rect(surface, border_color, self.rect, width=2, border_radius=4)

        display_text = self.text if (self.text or self.active) else self.placeholder
        text_color = config.INPUT_TEXT_COLOR if (self.text or self.active) else config.COLOR_GRAY
        label = self.font.render(display_text, True, text_color)
        surface.blit(label, (self.rect.x + 8, self.rect.y + (self.rect.height - label.get_height()) // 2))

        if self.active and self._cursor_visible:
            cursor_x = self.rect.x + 8 + label.get_width() + 2
            cursor_y = self.rect.y + 6
            pg.draw.line(surface, config.INPUT_TEXT_COLOR,
                         (cursor_x, cursor_y), (cursor_x, self.rect.bottom - 6), 2)


def draw_label(surface, text, pos, font=None, color=None, center=False):
    font = font or pg.font.SysFont(config.FONT_NAME, config.FONT_SIZE_MEDIUM)
    color = color or config.COLOR_WHITE
    label = font.render(text, True, color)
    rect = label.get_rect(center=pos) if center else label.get_rect(topleft=pos)
    surface.blit(label, rect)
    return rect
