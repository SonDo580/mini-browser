from __future__ import annotations
from typing import TYPE_CHECKING

from browser.html_parser.nodes import Text, Element
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.text_layout import TextLayout

if TYPE_CHECKING:
    from browser.layout.block_layout import BlockLayout


class LineLayout(BaseLayout):
    """Layout for a line of text."""

    def __init__(
        self, node: Text | Element, parent: BlockLayout, previous: LineLayout | None
    ):
        self.node = node  # unused
        self.parent = parent
        self.previous = previous
        self.children: list[TextLayout] = []

    def layout(self):
        """Compute display info and recursively layout children."""
        # Horizontal position and width:
        # - Each line starts at its parent's left edge.
        # - Each line spans the full width of its parent.
        self._x = self.parent.x
        self._width = self.parent.width

        # Vertical position:
        # - If there's a previous line, starts right after it.
        # - Otherwise, starts at the parent's top edge.
        if self.previous:
            self._y = self.previous.y + self.previous.height
        else:
            self._y = self.parent.y

        # Layout each word in the line
        for text_layout in self.children:
            text_layout.layout()

        # Calculate baseline for current line
        max_ascent = max(
            [text_layout.font.metrics("ascent") for text_layout in self.children]
        )
        baseline = self.y + max_ascent * 1.25

        # Align all words along the baseline
        for text_layout in self.children:
            text_layout.y = baseline - text_layout.font.metrics("ascent")

        # Compute line's height
        # = height of the tallest word multiplied with a factor to add space between lines
        max_descent = max(
            [text_layout.font.metrics("descent") for text_layout in self.children]
        )
        self._height = (max_ascent + max_descent) * 1.25

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        return []
