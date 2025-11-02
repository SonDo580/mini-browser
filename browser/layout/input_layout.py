from __future__ import annotations
from typing import TYPE_CHECKING
import skia

from browser.constants import INPUT_WIDTH_PX
from browser.html.nodes import Text, Element
from browser.layout.base import BaseLayout
from browser.render.base import BaseDrawCommand
from browser.render.draw_commands import DrawRoundedRect, DrawText, DrawLine
from browser.utils.font import get_font_from_css, linespace

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

        self.font: skia.Font = get_font_from_css(node)

    def layout(self):
        """Compute display info."""
        self._width = INPUT_WIDTH_PX

        if self.previous:
            self._x = (
                self.previous.x
                + self.previous.width
                + self.previous.font.measureText(" ")
            )
        else:
            self._x = self.parent.x

        self._height = linespace(self.font)

        # The y position of input/button depends on the other items in the same line,
        # so we’ll compute that inside LineLayout’s 'layout' method.

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        if self.__is_hidden_input():
            return []  # hide hidden input

        commands: list[BaseDrawCommand] = []

        # Draw the background
        bg_color = self.node.style.get("background-color", "transparent")
        if bg_color != "transparent":
            radius = float(self.node.style.get("border-radius", "0px")[:-2])
            commands.append(
                DrawRoundedRect(rect=self.bound_rect(), radius=radius, color=bg_color)
            )

        # Draw the text
        text = self.__extract_text()
        text_color = self.node.style["color"]
        commands.append(
            DrawText(
                left=self.x, top=self.y, text=text, font=self.font, color=text_color
            )
        )

        # Draw a cursor if the input is focused
        if self.node.is_focused:
            text_end_x = self.x + self.font.measureText(text)
            commands.append(
                DrawLine(
                    rect=skia.Rect.MakeLTRB(
                        l=text_end_x,
                        t=self.y,
                        r=text_end_x,
                        b=self.y + self.height,
                    ),
                    color="black",
                    thickness=1,
                )
            )

        return commands

    def __extract_text(self) -> str:
        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")
            if self.node.attributes.get("type") == "password":
                return "*" * len(text)  # mask password
            return text

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

    def __is_hidden_input(self) -> bool:
        return self.node.tag == "input" and self.node.attributes.get("type") == "hidden"
