from __future__ import annotations
from typing import TYPE_CHECKING

from browser.constants import INPUT_WIDTH_PX
from browser.html.nodes import Text, Element
from browser.layout.base import BaseLayout, BaseDrawCommand, Rect
from browser.layout.draw_commands import DrawRect, DrawText, DrawLine
from browser.utils.common import get_font_from_css

if TYPE_CHECKING:
    from browser.layout.line_layout import LineLayout
    from browser.layout.text_layout import TextLayout


class InputLayout(BaseLayout):
    """Layout for an input element or a button element."""

    def __init__(
        self,
        node: Element,
        parent: LineLayout,
        previous: InputLayout | TextLayout | None,
    ):
        super().__init__()
        self.node: Element = node
        self.parent: LineLayout = parent
        self.previous: InputLayout | TextLayout | None = previous
        self.children = []  # always empty (only accept simple text for button)

        self.font = get_font_from_css(node)

    def layout(self):
        """Compute display info."""
        self._width = INPUT_WIDTH_PX

        if self.previous:
            self._x = (
                self.previous.x + self.previous.width + self.previous.font.measure(" ")
            )
        else:
            self._x = self.parent.x

        self._height = self.font.metrics("linespace")

        # The y position of input/button depends on the other items in the same line,
        # so we’ll compute that inside LineLayout’s 'layout' method.

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        commands: list[BaseDrawCommand] = []

        # Draw the background
        bg_color = self.node.style.get("background-color", "transparent")
        if bg_color != "transparent":
            rect = Rect(
                top=self.x,
                left=self.y,
                right=self.x + self.width,
                bottom=self.y + self.height,
            )
            commands.append(DrawRect(rect=rect, color=bg_color))

        # Draw the text
        text = self._extract_text()
        text_color = self.node.style["color"]
        commands.append(
            DrawText(
                left=self.x, top=self.y, text=text, font=self.font, color=text_color
            )
        )

        # Draw a cursor if the input is focused
        if self.node.is_focused:
            text_end_x = self.x + self.font.measure(text)
            commands.append(
                DrawLine(
                    rect=Rect(
                        left=text_end_x,
                        top=self.y,
                        right=text_end_x,
                        bottom=self.y + self.height,
                    ),
                    color="black",
                    thickness=1,
                )
            )

        return commands

    def _extract_text(self) -> str:
        if self.node.tag == "input":
            return self.node.attributes.get("value", "")

        if (
            self.node.tag == "button"
            and len(self.node.children) == 1
            and isinstance(self.node.children[0], Text)
        ):
            # Ignore complex HTML contents inside button to simplify things
            return self.node.children[0].text

        return ""

    def set_y(self, value: float) -> None:
        """
        Set the y coordinate for current input/button.
        Called by LineLayout to align items along the baseline.
        """
        self._y = value
