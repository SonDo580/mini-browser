from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
import skia

from browser.constants import WIDTH, DEFAULT_LINK
from browser.url import URL
from browser.render.base import BaseDrawCommand
from browser.render.draw_commands import DrawOutline, DrawText, DrawLine, DrawRect
from browser.utils.font import get_font, linespace

if TYPE_CHECKING:
    from browser.browser import Browser


class ChromeComponent(Enum):
    ADDRESS_BAR = "address_bar"


class Chrome:
    """
    Chrome refers to the parts of a web browser's interface
    that are not part of the web page itself.
    Example: tab bar, address bar, back/forward/refresh buttons, etc.
    """

    def __init__(self, browser: Browser):
        self.browser = browser

        self.font: skia.Font = get_font(size=20, weight="normal", style="roman")
        self.font_height = linespace(self.font)

        # Tab bar (new-tab button + tabs)
        self.padding = 5
        self.tabbar_bottom = self.font_height + 2 * self.padding
        self.new_tab_button_rect = self._get_new_tab_button_rect()

        # URL bar (navigation buttons + address bar)
        self.url_bar_top = self.tabbar_bottom
        self.url_bar_bottom = self.url_bar_top + self.font_height + 2 * self.padding
        self.back_button_rect = self._get_back_button_rect()
        self.address_bar_rect = self._get_address_bar_rect()

        # Address editing
        self.focused_component: ChromeComponent | None = None
        self.address_input: str = ""

        self.bottom = self.url_bar_bottom

    def _get_new_tab_button_rect(self) -> skia.Rect:
        """Get rectangular boundary of the add-tag button."""
        button_width = self.font.measureText("+") + 2 * self.padding
        button_height = self.font_height
        return skia.Rect.MakeLTRB(
            l=self.padding,
            t=self.padding,
            r=self.padding + button_width,
            b=self.padding + button_height,
        )

    def _get_tab_rect(self, i: int) -> skia.Rect:
        """Get rectangular boundary of a tab."""
        tabs_start = self.new_tab_button_rect.right() + self.padding
        tab_width = (
            self.font.measureText(f"Tab X") + 2 * self.padding
        )  # X's width ~ digit's width
        return skia.Rect.MakeLTRB(
            l=tabs_start + tab_width * i,
            t=0,
            r=tabs_start + tab_width * (i + 1),
            b=self.tabbar_bottom,
        )

    def _get_back_button_rect(self) -> skia.Rect:
        """Get rectangular boundary of the go-back button."""
        button_width = self.font.measureText("<") + 2 * self.padding
        return skia.Rect.MakeLTRB(
            l=self.padding,
            t=self.url_bar_top + self.padding,
            r=self.padding + button_width,
            b=self.url_bar_bottom - self.padding,
        )

    def _get_address_bar_rect(self) -> skia.Rect:
        """Get rectangular boundary of the address bar."""
        return skia.Rect.MakeLTRB(
            l=self.back_button_rect.right() + self.padding,
            t=self.url_bar_top + self.padding,
            r=WIDTH - self.padding,
            b=self.url_bar_bottom - self.padding,
        )

    def paint(self) -> list[BaseDrawCommand]:
        """Return the draw commands (display list) to render the chrome."""
        commands: list[BaseDrawCommand] = []

        # Chrome's background and border
        commands.extend(self._paint_background_and_border())

        # New-Tab button
        commands.extend(self._paint_new_tab_button())

        # Tabs
        commands.extend(self._paint_tabs())

        # Go-back button
        commands.extend(self._paint_back_button())

        # Address bar
        commands.extend(self._paint_address_bar())

        return commands

    def _paint_background_and_border(self) -> list[BaseDrawCommand]:
        return [
            DrawRect(
                rect=skia.Rect.MakeLTRB(l=0, t=0, r=WIDTH, b=self.bottom),
                color="white",
            ),
            DrawLine(
                rect=skia.Rect.MakeLTRB(l=0, t=self.bottom, r=WIDTH, b=self.bottom),
                color="black",
                thickness=1,
            ),
        ]

    def _paint_new_tab_button(self) -> list[BaseDrawCommand]:
        return [
            DrawOutline(rect=self.new_tab_button_rect, color="black", thickness=1),
            DrawText(
                left=self.new_tab_button_rect.left() + self.padding,
                top=self.new_tab_button_rect.top(),
                text="+",
                font=self.font,
                color="black",
            ),
        ]

    def _paint_tabs(self) -> list[BaseDrawCommand]:
        commands: list[BaseDrawCommand] = []

        for i, tab in enumerate(self.browser.tabs):
            # Add left/right borders and tag name
            commands.extend(self._paint_tab(i))

            # Distinguish the active tab
            if tab == self.browser.active_tab:
                commands.extend(self._paint_active_tab_indicator(i))

        return commands

    def _paint_tab(self, tab_index: int) -> list[BaseDrawCommand]:
        tab_rect = self._get_tab_rect(tab_index)
        return [
            DrawLine(
                rect=skia.Rect.MakeLTRB(
                    l=tab_rect.left(),
                    t=tab_rect.top(),
                    r=tab_rect.left(),
                    b=tab_rect.bottom(),
                ),
                color="black",
                thickness=1,
            ),
            DrawLine(
                rect=skia.Rect.MakeLTRB(
                    l=tab_rect.right(),
                    t=tab_rect.top(),
                    r=tab_rect.right(),
                    b=tab_rect.bottom(),
                ),
                color="black",
                thickness=1,
            ),
            DrawText(
                left=tab_rect.left() + self.padding,
                top=tab_rect.top() + self.padding,
                text=f"Tab {tab_index}",
                font=self.font,
                color="black",
            ),
        ]

    def _paint_active_tab_indicator(self, tab_index: int) -> list[BaseDrawCommand]:
        tab_rect = self._get_tab_rect(tab_index)
        return [
            DrawLine(
                rect=skia.Rect.MakeLTRB(
                    l=0,
                    t=tab_rect.bottom(),
                    r=tab_rect.left(),
                    b=tab_rect.bottom(),
                ),
                color="black",
                thickness=1,
            ),
            DrawLine(
                rect=skia.Rect.MakeLTRB(
                    l=tab_rect.right(),
                    t=tab_rect.bottom(),
                    r=WIDTH,
                    b=tab_rect.bottom(),
                ),
                color="black",
                thickness=1,
            ),
        ]

    def _paint_back_button(self) -> list[BaseDrawCommand]:
        return [
            DrawOutline(rect=self.back_button_rect, color="black", thickness=1),
            DrawText(
                left=self.back_button_rect.left() + self.padding,
                top=self.back_button_rect.top(),
                text="<",
                font=self.font,
                color="black",
            ),
        ]

    def _paint_address_bar(self) -> list[BaseDrawCommand]:
        commands: list[BaseDrawCommand] = [
            DrawOutline(rect=self.address_bar_rect, color="black", thickness=1),
            self._paint_address_text(),
        ]

        if self.focused_component == ChromeComponent.ADDRESS_BAR:
            # Draw a cursor in editing mode
            commands.append(self._paint_address_input_cursor())

        return commands

    def _paint_address_text(self) -> DrawText:
        # Show current url by default
        text = str(self.browser.active_tab.url)

        if self.focused_component == ChromeComponent.ADDRESS_BAR:
            # Show user input in editing mode
            text = self.address_input

        return DrawText(
            left=self.address_bar_rect.left() + self.padding,
            top=self.address_bar_rect.top(),
            text=text,
            font=self.font,
            color="black",
        )

    def _paint_address_input_cursor(self) -> DrawLine:
        address_input_width = self.font.measureText(self.address_input)
        return DrawLine(
            rect=skia.Rect.MakeLTRB(
                l=self.address_bar_rect.left() + self.padding + address_input_width,
                t=self.address_bar_rect.top(),
                r=self.address_bar_rect.left() + self.padding + address_input_width,
                b=self.address_bar_rect.bottom(),
            ),
            color="red",
            thickness=1,
        )

    def click(self, x: int, y: int) -> bool:
        """Handle click events inside the chrome area. Return True if handled."""
        if self.new_tab_button_rect.contains(x, y):
            # Create a new tab (with default URL)
            self.browser.new_tab(URL(DEFAULT_LINK))
            return True

        if self.back_button_rect.contains(x, y):
            # Go back to the previous page
            self.browser.active_tab.go_back()
            return True

        if self.address_bar_rect.contains(x, y):
            # Focus and clear address bar contents to start editing
            self.focused_component = ChromeComponent.ADDRESS_BAR
            self.address_input = ""
            return True

        # Switch to the tab being clicked on
        for i, tab in enumerate(self.browser.tabs):
            if self._get_tab_rect(i).contains(x, y):
                self.browser.set_active_tab(tab)
                return True

        # Clicked on empty area -> blur address bar
        # - don't have to restore address input,
        #   since url is shown if address bar is not focused,
        #   and address input is reset to "" when address bar is clicked.
        return self.blur()

    def keypress(self, char: str) -> bool:
        """Handle keypress event. Return True if handled."""
        if self.focused_component == ChromeComponent.ADDRESS_BAR:
            # Append character to address input
            self.address_input += char
            return True
        return False

    def enter(self) -> bool:
        """Handle pressing Enter. Return True if handled."""
        if self.focused_component == ChromeComponent.ADDRESS_BAR:
            # Go to the new address
            self.browser.active_tab.load(URL(self.address_input))
            self.focused_component = None
            return True
        return False

    def backspace(self) -> bool:
        """Handle pressing BackSpace. Return True if handled."""
        if (
            self.focused_component == ChromeComponent.ADDRESS_BAR
            and len(self.address_input) > 0
        ):
            # Remove the last character from address input
            self.address_input = self.address_input[:-1]
            return True
        return False

    def blur(self) -> bool:
        """Unfocus the chrome. Return True if handled."""
        if self.focused_component:
            self.focused_component = None
            return True
        return False
