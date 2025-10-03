from __future__ import annotations
import tkinter.font
from enum import Enum

from browser.constants import BLOCK_ELEMENTS
from browser.html_parser.nodes import Text, Element
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.draw_commands import DrawText, DrawRectangle
from browser.utils.font import get_font


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

        # Store info needed to display words: (x, y, text, font, color)
        self.words_display_info: list[
            tuple[float, float, str, tkinter.font.Font, str]
        ] = []

        # ***** Initialize display info for words *****
        # **** (only use if layout mode is INLINE) ****
        # *********************************************
        self.cursor_x: float = 0  # relative to the block's x
        self.cursor_y: float = 0  # relative to the block's y

        # Buffer to store words display info in a line: (x, text, font, color)
        # (y will be computed when 'flush')
        self.line: list[tuple[float, str, tkinter.font.Font, str]] = []

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
            for child in self.node.children:
                child_layout = BlockLayout(node=child, parent=self, previous=previous)
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
                self.handle_word(node, word)
        elif isinstance(node, Element):
            if node.tag == "br":
                self.flush()
            for child in node.children:
                self.recurse(child)

    def handle_word(self, node: Text, word: str) -> None:
        """
        Calculate info to display word and store it in the line buffer.
        Flush the line buffer if adding word causes overflow.
        """
        # Extract CSS styles and convert to Tk format
        font_weight = node.style["font-weight"]
        text_color = node.style["color"]

        font_style = node.style["font-style"]
        if font_style == "normal":
            font_style = "roman"  # CSS “normal” -> Tk “roman”

        # CSS pixels -> Tk points
        # - CSS spec assumes 96 DPI (dots per inch),
        #   which means 96 CSS pixels = 1 inch.
        # - Traditional points assume 72 DPI.
        # => 1 px = 72/96 pt = 0.75 pt
        # => slice off the 'px' suffix then multiply with 0.75
        font_size = int(float(node.style["font-size"][:-2]) * 0.75)

        font = get_font(font_size, font_weight, font_style)
        width = font.measure(word)

        # Flush the line buffer if adding 'word' causes overflow
        # (compare by relative positions)
        if self.cursor_x + width > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font, text_color))
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

        metrics = [font.metrics() for _, _, font, _ in self.line]

        # Calculate baseline for current line
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + max_ascent * 1.25

        # Calculate next cursor_y
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + max_descent * 1.25

        # Place each word relative to baseline and collect display info
        # - note that x, y are top-left absolute coordinates
        # - we need to add the block's x and y to relative_x and relative_y
        for relative_x, word, font, color in self.line:
            x = self.x + relative_x
            y = self.y + baseline - font.metrics("ascent")
            self.words_display_info.append((x, y, word, font, color))

        # Reset cursor_x and line buffer
        self.cursor_x = 0
        self.line = []

    def paint(self) -> list[BaseDrawCommand]:
        """Return the drawing commands (display list) for current layout"""
        commands: list[BaseDrawCommand] = []

        # Add DrawRectangle command to draw background
        bg_color = self.node.style.get("background-color", "transparent")
        if bg_color != "transparent":
            commands.append(
                DrawRectangle(
                    x1=self.x,
                    y1=self.y,
                    x2=self.x + self.width,
                    y2=self.y + self.height,
                    color=bg_color,
                )
            )

        if self.layout_mode() == LayoutMode.INLINE:
            # Add DrawText commands using display info computed during 'recurse' and 'flush'
            for x, y, word, font, color in self.words_display_info:
                commands.append(DrawText(x, y, word, font, color))

        return commands
