from __future__ import annotations
import tkinter.font
from typing import TYPE_CHECKING

from browser.html_parser.nodes import Text
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.draw_commands import DrawText

if TYPE_CHECKING:
    from browser.layout.line_layout import LineLayout


class TextLayout(BaseLayout):
    """Layout for a word."""

    def __init__(
        self,
        node: Text,
        word: str,
        font: tkinter.font.Font,
        parent: LineLayout,
        previous: TextLayout | None,
    ):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []  # always empty since text layout is a leaf

        self.word = word
        self.font = font

    def layout(self):
        """Compute display info."""
        self._width = self.font.measure(self.word)

        if self.previous:
            self._x = (
                self.previous.x + self.previous.width + self.previous.font.measure(" ")
            )
        else:
            self._x = self.parent.x

        self._height = self.font.metrics("linespace")

        # The y position of a word depends on the other words in the same line,
        # so we’ll compute that inside LineLayout’s 'layout' method.

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

    @BaseLayout.y.setter
    def y(self, value: float) -> None:
        """
        Set the y coordinate for current word.
        Called by LineLayout to align words along the baseline.
        """
        self._y = value
