from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING

from browser.constants import BLOCK_ELEMENTS, INPUT_WIDTH_PX
from browser.html.nodes import Text, Element
from browser.utils.common import get_font_from_css
from browser.layout.base import BaseLayout, BaseDrawCommand, Rect
from browser.layout.draw_commands import DrawRect
from browser.layout.line_layout import LineLayout
from browser.layout.text_layout import TextLayout
from browser.layout.input_layout import InputLayout

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
        self.node: Text | Element = node
        self.parent: DocumentLayout | BlockLayout = parent
        self.previous: BlockLayout | None = previous
        self.children: list[BlockLayout] | list[LineLayout] = []

        # Horizontal position for the next item in the current line
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
                child_layout = BlockLayout(node=child, parent=self, previous=previous)
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
        # Text node -> inline
        if isinstance(self.node, Text):
            return LayoutMode.INLINE

        # Element node with any block-element child -> block
        if any(
            [
                isinstance(child, Element) and child.tag in BLOCK_ELEMENTS
                for child in self.node.children
            ]
        ):
            return LayoutMode.BLOCK

        # Element node with children but none of them are block elements -> inline
        # Special case: input element -> inline
        if self.node.children or self.node.tag == "input":
            return LayoutMode.INLINE

        # Element node without children (except input) -> block
        return LayoutMode.BLOCK

    def recurse(self, node: Text | Element) -> None:
        """Traverse the HTML tree recursively to add lines."""
        if isinstance(node, Text):
            for word in node.text.split():
                self.handle_word(node, word)
        elif isinstance(node, Element):
            if node.tag == "br":
                self.new_line()
            elif node.tag in ["input", "button"]:
                self.handle_input(node)
            else:
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
        Create a TextLayout and place it in the current LineLayout.
        Start a new line if adding word causes overflow.
        """
        font = get_font_from_css(node)
        word_width = font.measure(word)

        # Start a new line if adding word causes overflow
        if self.cursor_x + word_width > self.width:
            self.new_line()

        # Create a TextLayout and place it in the current line
        line_layout: LineLayout = self.children[-1]
        previous_layout = line_layout.children[-1] if line_layout.children else None
        text_layout = TextLayout(
            node, word, font, parent=line_layout, previous=previous_layout
        )
        line_layout.children.append(text_layout)

        # Update horizontal position for the next item
        self.cursor_x += word_width + font.measure(" ")

    def handle_input(self, node: Element) -> None:
        """
        Create an InputLayout and place it in the current LineLayout.
        Start a new line if adding the input/button causes overflow.
        """
        font = get_font_from_css(node)
        input_width = INPUT_WIDTH_PX

        # Start a new line if adding input/button causes overflow
        if self.cursor_x + input_width > self.width:
            self.new_line()

        # Create an InputLayout and place it in the current line
        line_layout: LineLayout = self.children[-1]
        previous_layout = line_layout.children[-1] if line_layout.children else None
        input_layout = InputLayout(node, parent=line_layout, previous=previous_layout)
        line_layout.children.append(input_layout)

        # Update horizontal position for the next item
        self.cursor_x += input_width + font.measure(" ")

    def paint(self) -> list[BaseDrawCommand]:
        """Return the drawing commands (display list) for current layout"""
        # Add DrawRect command to draw background
        bg_color = self.node.style.get("background-color", "transparent")
        if bg_color != "transparent":
            rect = Rect(
                top=self.x,
                left=self.y,
                right=self.x + self.width,
                bottom=self.y + self.height,
            )
            return [DrawRect(rect=rect, color=bg_color)]

        return []

    # override
    def should_paint(self) -> bool:
        """Whether to collect draw commands from current layout."""
        # Due to block siblings, sometimes an input or button element
        # will create a BlockLayout (then an InputLayout inside)
        # -> avoid painting the background twice in this case
        return not (
            isinstance(self.node, Element)
            and self.node.tag
            in [
                "input",
                "button",
            ]
        )
