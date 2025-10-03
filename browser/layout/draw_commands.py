import tkinter
import tkinter.font

from browser.layout.base import BaseDrawCommand


class DrawText(BaseDrawCommand):
    """Drawing command to render a text string on a Tkinter canvas"""

    def __init__(
        self, x: float, y: float, text: str, font: tkinter.font.Font, color: str
    ):
        self.top = y
        self.bottom = y + font.metrics("linespace")
        self.left = x
        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
        canvas.create_text(
            self.left,
            self.top - scroll,
            text=self.text,
            font=self.font,
            anchor="nw",  # top-left
            fill=self.color,
        )


class DrawRectangle(BaseDrawCommand):
    """Drawing command to render a filled rectangle on a Tkinter canvas"""

    def __init__(self, x1: float, y1: float, x2: float, y2: float, color: str):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
        canvas.create_rectangle(
            self.left,
            self.top - scroll,
            self.right,
            self.bottom - scroll,
            width=0,  # remove border
            fill=self.color,
        )
