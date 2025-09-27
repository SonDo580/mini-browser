from __future__ import annotations
import tkinter.font
from enum import Enum

from browser.constants import BLOCK_ELEMENTS, VSTEP
from browser.html_parser.nodes import Text, Element
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.draw_commands import DrawText, DrawRectangle
from browser.utils.font import TWeight, TStyle, get_font


class LayoutMode(Enum):
    # [!] These layout modes differ from CSS block/inline concepts
    BLOCK = "block"  # a node where children stack vertically
    INLINE = "inline"  # a node where children flow together as text


class BlockLayout(BaseLayout):
    """Represent a layout node"""

    def __init__(
        self, node: Text | Element, parent: BaseLayout, previous: BlockLayout | None
    ):
        super().__init__()
        self.node = node
        self.parent = parent
        self.previous = previous

        # Store info needed to display words: (x, y, text, font)
        self.words_display_info: list[tuple[float, float, str, tkinter.font.Font]] = []

        # ***** Initialize display info for words *****
        # **** (only use if layout mode is inline) ****
        # *********************************************
        self.cursor_x: float = 0  # relative to the block's x
        self.cursor_y: float = 0  # relative to the block's y
        self.weight: TWeight = "normal"
        self.style: TStyle = "roman"
        self.size: int = 12

        # Buffer to store words display info in a line: (x, text, font)
        # (y will be computed when 'flush')
        self.line: list[tuple[float, str, tkinter.font.Font]] = []

    def layout(self) -> None:
        """Compute display info and recursively layout children."""
        # Horizontal position and width:
        # - Each block starts at its parent's left edge
        # - Each block spans the full width of its parent
        self._x = self.parent.x
        self._width = self.parent.width

        # Vertical position:
        # - If there's a previous sibling, starts right after it.
        # - Otherwise, starts at the parent's top edge.
        if self.previous:
            self._y = self.previous.y + self.previous.height
        else:
            self._y = self.parent.y

        # [!] Height is computed after the children's layout calls (for BLOCK layout mode),
        #     or after all text flushes (for INLINE layout mode).

        mode = self.layout_mode()
        if mode == LayoutMode.BLOCK:
            # Create and layout each child block in order
            previous: BlockLayout | None = None
            for child_node in self.node.children:
                child_layout = BlockLayout(
                    node=child_node, parent=self, previous=previous
                )
                self.children.append(child_layout)
                child_layout.layout()
                previous = child_layout

            # Height = total height of all child layouts
            self._height = sum(child_layout.height for child_layout in self.children)
        elif mode == LayoutMode.INLINE:
            # Walk the HTML tree to collect words' display info
            self.recurse(self.node)

            # Flush the last line buffer
            self.flush()

            # Height = total vertical space for all text lines
            self._height = self.cursor_y

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
        """Walk the HTML tree recursively to collect words' display info"""
        if isinstance(node, Text):
            for word in node.text.split():
                self.handle_word(word)
        elif isinstance(node, Element):
            self.open_tag(node.tag)
            for child in node.children:
                self.recurse(child)
            self.close_tag(node.tag)

    def open_tag(self, tag: str) -> None:
        """
        Handle effects of an opening tag:
        - Change formatting.
        - Layout changes (e.g. <br> forces a line break).
        """
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()

    def close_tag(self, tag: str) -> None:
        """
        Handle effects of a closing tag:
        - Reset formatting.
        - Layout changes (e.g. </p> forces a line break and adds space).
        """
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP

    def handle_word(self, word: str) -> None:
        """
        Calculate info to display word and store it in the line buffer.
        Flush the line buffer if adding word causes overflow.
        """

        font = get_font(self.size, self.weight, self.style)
        width = font.measure(word)

        # Flush the line buffer if adding 'word' causes overflow
        # (compare by relative positions)
        if self.cursor_x + width > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font))
        self.cursor_x += width + font.measure(" ")

    def flush(self):
        """
        Flush the line buffer:
        - Calculate baseline for current line.
        - Align words along baseline and add to display info list.
        - Calculate cursor_y for next line.
        - Reset cursor_x and line buffer for next line.

        Why we need this:
        - We want to align the characters along their baseline.
        - Characters on the same line may have different sizes.
        - We can only finalize the positions after we know the max ascent.
        """
        if not self.line:
            return

        # Calculate baseline for current line
        metrics = [font.metrics() for _, _, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + max_ascent * 1.25

        # Calculate next cursor_y
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + max_descent * 1.25

        # Place each word relative to baseline and collect display info
        # - note that x, y are top-left absolute coordinates
        # - we need to add the block's x and y to relative_x and relative_y
        for relative_x, word, font in self.line:
            x = self.x + relative_x
            y = self.y + baseline - font.metrics("ascent")
            self.words_display_info.append((x, y, word, font))

        # Reset cursor_x and line buffer
        self.cursor_x = 0
        self.line = []

    def paint(self) -> list[BaseDrawCommand]:
        """Return the drawing commands (display list) for current layout"""
        commands: list[BaseDrawCommand] = []

        # Add a gray background to 'pre' tags
        # [!] Background should be drawn below the text (z-axis)
        #     -> do this before adding DrawText commands
        if isinstance(self.node, Element) and self.node.tag == "pre":
            commands.append(
                DrawRectangle(
                    x1=self.x,
                    y1=self.y,
                    x2=self.x + self.width,
                    y2=self.y + self.height,
                    color="gray",
                )
            )

        if self.layout_mode() == LayoutMode.INLINE:
            # Add DrawText commands using display info computed during 'recurse' and 'flush'
            for x, y, word, font in self.words_display_info:
                commands.append(DrawText(x, y, word, font))

        return commands
