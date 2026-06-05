from __future__ import annotations
from typing import TYPE_CHECKING
import skia

from browser.html.nodes import Text
from browser.layout.base import BaseLayout
from browser.render.base import BaseDrawCommand
from browser.render.draw_commands import DrawText
from browser.utils.font import linespace

if TYPE_CHECKING:
    from browser.layout.line_layout import LineLayout
    from browser.layout.input_layout import InputLayout


class TextLayout(BaseLayout):
    """Layout for a word."""

    def __init__(
        self,
        node: Text,
        word: str,
        font: skia.Font,
        parent: LineLayout,
        previous: TextLayout | InputLayout | None,
    ):
        self.node: Text = node
        self.parent: LineLayout = parent
        self.previous: TextLayout | InputLayout | None = previous
        self.children = []  # always empty

        self.word = word
        self.font = font

    def layout(self):
        """Compute display info."""
        self._width = self.font.measureText(self.word)

        if self.previous:
            self._x = (
                self.previous.x
                + self.previous.width
                + self.previous.font.measureText(" ")
            )
        else:
            self._x = self.parent.x

        self._height = linespace(self.font)

        # The y position depends on the other items in the same line,
        # so we’ll compute that inside LineLayout’s layout() method.

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        # Add a single DrawText comment
        text_color = self.node.style["color"]
        return [
            DrawText(
                left=self.x,
                top=self.y,
                text=self.word,
                font=self.font,
                color=text_color,
            )
        ]

    def set_y(self, value: float):
        """
        Set the y coordinate for current word.
        Called by LineLayout to align items along the baseline.
        """
        self._y = value
