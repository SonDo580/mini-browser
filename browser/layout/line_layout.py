from __future__ import annotations
from typing import TYPE_CHECKING

from browser.html.nodes import Text, Element
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.text_layout import TextLayout
from browser.layout.input_layout import InputLayout

if TYPE_CHECKING:
    from browser.layout.block_layout import BlockLayout


class LineLayout(BaseLayout):
    """Layout for a line of text."""

    def __init__(
        self, node: Text | Element, parent: BlockLayout, previous: LineLayout | None
    ):
        self.node: Text | Element = node  # unused
        self.parent: BlockLayout = parent
        self.previous: LineLayout | None = previous
        self.children: list[TextLayout | InputLayout] = []

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

        if not self.children:
            self._height = 0
            return

        # Layout each child in the line
        for child_layout in self.children:
            child_layout.layout()            

        # Calculate baseline for current line
        max_ascent = max(
            [child_layout.font.metrics("ascent") for child_layout in self.children]
        )
        baseline = self.y + max_ascent * 1.25

        # Align children along the baseline
        for child_layout in self.children:
            child_layout.set_y(baseline - child_layout.font.metrics("ascent"))

        # Compute line's height
        # = height of the tallest child multiplied with a factor to add space between lines
        max_descent = max(
            [child_layout.font.metrics("descent") for child_layout in self.children]
        )
        self._height = (max_ascent + max_descent) * 1.25

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        return []
