from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING

from browser.constants import BLOCK_ELEMENTS
from browser.html_parser.nodes import Text, Element
from browser.utils.font import get_font
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.draw_commands import DrawRectangle
from browser.layout.line_layout import LineLayout
from browser.layout.text_layout import TextLayout

if TYPE_CHECKING:
    from browser.layout.document_layout import DocumentLayout


class LayoutMode(Enum):
    # [!] These layout modes differ from CSS block/inline concepts
    BLOCK = "block"  # a node where children stack vertically
    INLINE = "inline"  # a node where children flow together as text


class BlockLayout(BaseLayout):
    """Represent a layout node"""

    def __init__(
        self,
        node: Text | Element,
        parent: DocumentLayout | BlockLayout,
        previous: BlockLayout | None,
    ):
        super().__init__()
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children: list[BlockLayout] | list[LineLayout] = []

        # Horizontal position for the next word in the current line
        # (only used if layout mode is INLINE)
        self.cursor_x: float = 0  # relative to the block's x

    def layout(self) -> None:
        """Compute display info and recursively layout children."""
        # Horizontal position and width:
        # - Each block starts at its parent's left edge.
        # - Each block spans the full width of its parent.
        self._x = self.parent.x
        self._width = self.parent.width

        # Vertical position:
        # - If there's a previous sibling, starts right after it.
        # - Otherwise, starts at the parent's top edge.
        if self.previous:
            self._y = self.previous.y + self.previous.height
        else:
            self._y = self.parent.y

        mode = self.layout_mode()
        if mode == LayoutMode.BLOCK:
            # Create child blocks in order
            previous: BlockLayout | None = None
            for child in self.node.children:
                child_layout = BlockLayout(
                    node=child, parent=self, previous=previous
                )
                self.children.append(child_layout)
                previous = child_layout

        elif mode == LayoutMode.INLINE:
            # Traverse the HTML tree to add lines
            self.new_line()
            self.recurse(self.node)

        # Recursively laying out children
        for child_layout in self.children:
            child_layout.layout()

        # Compute height after laying out all children
        # = total height of all children
        self._height = sum(child_layout.height for child_layout in self.children)

    def layout_mode(self) -> LayoutMode:
        """Decide layout mode for the current layout object."""
        # The node is a Text node -> inline
        if isinstance(self.node, Text):
            return LayoutMode.INLINE

        # The node is not a Text node, has children that are block elements -> block
        if any(
            [
                isinstance(child, Element) and child.tag in BLOCK_ELEMENTS
                for child in self.node.children
            ]
        ):
            return LayoutMode.BLOCK

        # The node is not a Text node, has children but none of them are block elements -> inline
        if self.node.children:
            return LayoutMode.INLINE

        # The node is not a Text node and has no children -> block
        return LayoutMode.BLOCK

    def recurse(self, node: Text | Element) -> None:
        """Traverse the HTML tree recursively to add lines."""
        if isinstance(node, Text):
            for word in node.text.split():
                self.handle_word(node, word)
        elif isinstance(node, Element):
            if node.tag == "br":
                self.new_line()
            for child in node.children:
                self.recurse(child)

    def new_line(self) -> None:
        """Start a new LineLayout."""
        self.cursor_x = 0
        previous_line_layout: LineLayout | None = (
            self.children[-1] if self.children else None
        )
        line_layout = LineLayout(
            node=self.node, parent=self, previous=previous_line_layout
        )
        self.children.append(line_layout)

    def handle_word(self, node: Text, word: str) -> None:
        """
        Create a TextLayout for a word and place it in the current LineLayout.
        Start a new line if adding word causes overflow.
        """
        # Extract CSS styles and convert to Tk format
        font_weight = node.style["font-weight"]
        font_style = node.style["font-style"]
        if font_style == "normal":
            font_style = "roman"  # CSS “normal” -> Tk “roman”
        font_size = int(
            float(node.style["font-size"][:-2]) * 0.75
        )  # CSS pixels -> Tk points: slice off 'px' then multiply with 0.75

        font = get_font(font_size, font_weight, font_style)
        word_width = font.measure(word)

        # Start a new line if adding word causes overflow
        if self.cursor_x + word_width > self.width:
            self.new_line()

        # Create a TextLayout and place it in the current line
        line_layout: LineLayout = self.children[-1]
        previous_text_layout = (
            line_layout.children[-1] if line_layout.children else None
        )
        text_layout = TextLayout(
            node, word, font, parent=line_layout, previous=previous_text_layout
        )
        line_layout.children.append(text_layout)

        # Update horizontal position for the next word
        self.cursor_x += word_width + font.measure(" ")

    def paint(self) -> list[BaseDrawCommand]:
        """Return the drawing commands (display list) for current layout"""
        # Add DrawRectangle command to draw background
        bg_color = self.node.style.get("background-color", "transparent")
        if bg_color != "transparent":
            return [
                DrawRectangle(
                    x1=self.x,
                    y1=self.y,
                    x2=self.x + self.width,
                    y2=self.y + self.height,
                    color=bg_color,
                )
            ]

        return []
