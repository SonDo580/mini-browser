import tkinter
import tkinter.font

from browser.layout.base import BaseDrawCommand, Rect


class DrawText(BaseDrawCommand):
    """Drawing command to render a text string."""

    def __init__(
        self, left: float, top: float, text: str, font: tkinter.font.Font, color: str
    ):
        bottom = top + font.metrics("linespace")
        right = left + font.measure(text)
        rect = Rect(left, top, right, bottom)
        self.rect = rect

        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
        canvas.create_text(
            self.rect.left,
            self.rect.top - scroll,
            text=self.text,
            font=self.font,
            anchor="nw",  # top-left
            fill=self.color,
        )


class DrawRect(BaseDrawCommand):
    """Drawing command to render a filled rectangle."""

    def __init__(self, rect: Rect, color: str):
        self.rect = rect
        self.color = color

    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
        canvas.create_rectangle(
            self.rect.left,
            self.rect.top - scroll,
            self.rect.right,
            self.rect.bottom - scroll,
            width=0,  # remove border
            fill=self.color,
        )


class DrawOutline(BaseDrawCommand):
    """Drawing command to render a rectangular outline."""

    def __init__(self, rect: Rect, color: str, thickness: float):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
        canvas.create_rectangle(
            self.rect.left,
            self.rect.top - scroll,
            self.rect.right,
            self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color,
        )


class DrawLine(BaseDrawCommand):
    """Drawing command to render a straight line."""

    def __init__(
        self,
        rect: Rect,
        color: str,
        thickness: float,
    ):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
        canvas.create_line(
            self.rect.left,
            self.rect.top - scroll,
            self.rect.right,
            self.rect.bottom - scroll,
            width=self.thickness,
            fill=self.color,
        )
