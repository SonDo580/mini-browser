from __future__ import annotations
from typing import TYPE_CHECKING

from browser.constants import WIDTH, DEFAULT_LINK
from browser.url import URL
from browser.layout.base import BaseDrawCommand, Rect
from browser.layout.draw_commands import DrawOutline, DrawText, DrawLine, DrawRect
from browser.utils.font import get_font

if TYPE_CHECKING:
    from browser.browser import Browser


class Chrome:
    """
    Chrome refers to the parts of a web browser's interface
    that are not part of the web page itself.
    Example: tab bar, address bar, back/forward/refresh buttons, etc.
    """

    def __init__(self, browser: Browser):
        self.browser = browser

        self.font = get_font(size=20, weight="normal", style="roman")
        self.font_height = self.font.metrics("linespace")

        self.padding = 5
        self.tabbar_bottom = self.font_height + 2 * self.padding
        self.new_tab_button_rect = self.get_new_tab_button_rect()

        self.bottom = self.tabbar_bottom

    def get_new_tab_button_rect(self) -> Rect:
        """Get rectangular boundary of the add-tag button."""
        button_width = self.font.measure("+") + 2 * self.padding
        button_height = self.font_height
        return Rect(
            left=self.padding,
            top=self.padding,
            right=self.padding + button_width,
            bottom=self.padding + button_height,
        )

    def get_tab_rect(self, i: int) -> Rect:
        """Get rectangular boundary of a tab."""
        tabs_start = self.new_tab_button_rect.right + self.padding
        tab_width = (
            self.font.measure(f"Tab X") + 2 * self.padding
        )  # X's width ~ digit's width
        return Rect(
            left=tabs_start + tab_width * i,
            top=0,
            right=tabs_start + tab_width * (i + 1),
            bottom=self.tabbar_bottom,
        )

    def paint(self) -> list[BaseDrawCommand]:
        """Return the draw commands (display list) to render the chrome."""
        commands: list[BaseDrawCommand] = []

        # Chrome's background and bottom border
        commands.extend(
            [
                DrawRect(
                    rect=Rect(left=0, top=0, right=WIDTH, bottom=self.bottom),
                    color="white",
                ),
                # DrawLine(
                #     rect=Rect(left=0, top=self.bottom, right=WIDTH, bottom=self.bottom),
                #     color="black",
                #     thickness=1,
                # ),
            ]
        )

        # New-Tab button
        commands.extend(
            [
                DrawOutline(rect=self.new_tab_button_rect, color="black", thickness=1),
                DrawText(
                    left=self.new_tab_button_rect.left + self.padding,
                    top=self.new_tab_button_rect.top,
                    text="+",
                    font=self.font,
                    color="black",
                ),
            ]
        )

        # Tabs
        for i, tab in enumerate(self.browser.tabs):
            tab_rect = self.get_tab_rect(i)
            # Add left/right borders and tag name
            commands.extend(
                [
                    DrawLine(
                        rect=Rect(
                            left=tab_rect.left,
                            top=tab_rect.top,
                            right=tab_rect.left,
                            bottom=tab_rect.bottom,
                        ),
                        color="black",
                        thickness=1,
                    ),
                    DrawLine(
                        rect=Rect(
                            left=tab_rect.right,
                            top=tab_rect.top,
                            right=tab_rect.right,
                            bottom=tab_rect.bottom,
                        ),
                        color="black",
                        thickness=1,
                    ),
                    DrawText(
                        left=tab_rect.left + self.padding,
                        top=tab_rect.top + self.padding,
                        text=f"Tab {i}",
                        font=self.font,
                        color="black",
                    ),
                ]
            )

            # Distinguish the active tab
            if tab == self.browser.active_tab:
                commands.extend(
                    [
                        DrawLine(
                            rect=Rect(
                                left=0,
                                top=tab_rect.bottom,
                                right=tab_rect.left,
                                bottom=tab_rect.bottom,
                            ),
                            color="black",
                            thickness=1,
                        ),
                        DrawLine(
                            rect=Rect(
                                left=tab_rect.right,
                                top=tab_rect.bottom,
                                right=WIDTH,
                                bottom=tab_rect.bottom,
                            ),
                            color="black",
                            thickness=1,
                        ),
                    ]
                )

        return commands

    def click(self, x: int, y: int) -> None:
        """Handle click events inside the chrome area."""
        if self.new_tab_button_rect.contains_point(x, y):
            # Create a new tab (with default URL)
            self.browser.new_tab(URL(DEFAULT_LINK))
        else:
            # Switch to the tab being clicked on
            for i, tab in enumerate(self.browser.tabs):
                if self.get_tab_rect(i).contains_point(x, y):
                    self.browser.set_active_tab(tab)
                    break
