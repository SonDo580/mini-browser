import skia

from browser.layout.base import BaseDrawCommand
from browser.utils.font import linespace, ascent
from browser.utils.color import parse_color


class DrawText(BaseDrawCommand):
    """Drawing command to render a text string."""

    def __init__(self, left: float, top: float, text: str, font: skia.Font, color: str):
        bottom = top + linespace(font)
        right = left + font.measureText(text)
        rect = skia.Rect.MakeLTRB(left, top, right, bottom)
        self.rect = rect

        self.text = text
        self.font = font
        self.color = color

    def execute(self, scroll: float, canvas: skia.Canvas) -> None:
        paint = skia.Paint(
            AntiAlias=True,  # draw some semi-transparent pixels to better approximate the shape of the text
            Color=parse_color(self.color),
        )
        baseline = self.rect.top() - scroll - ascent(self.font)
        canvas.drawString(self.text, self.rect.left(), baseline, self.font, paint)


class DrawRect(BaseDrawCommand):
    """Drawing command to render a filled rectangle."""

    def __init__(self, rect: skia.Rect, color: str):
        self.rect = rect
        self.color = color

    def execute(self, scroll: float, canvas: skia.Canvas) -> None:
        paint = skia.Paint(Color=parse_color(self.color))
        offset_rect = self.rect.makeOffset(
            0, -scroll
        )  # shift the rectangle vertically by -scroll
        canvas.drawRect(offset_rect, paint)


class DrawRoundedRect(BaseDrawCommand):
    """Drawing command to render a rounded filled rectangle."""

    def __init__(self, rect: skia.Rect, radius: float, color: str):
        self.rect = rect
        self.radius = radius
        self.color = color

    def execute(self, scroll: float, canvas: skia.Canvas) -> None:
        paint = skia.Paint(Color=parse_color(self.color))
        offset_rect = self.rect.makeOffset(
            0, -scroll
        )  # shift the rectangle vertically by -scroll
        rounded_rect = skia.RRect.MakeRectXY(
            offset_rect, self.radius, self.radius
        )
        canvas.drawRRect(rounded_rect, paint)


class DrawOutline(BaseDrawCommand):
    """Drawing command to render a rectangular outline."""

    def __init__(self, rect: skia.Rect, color: str, thickness: float):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll: float, canvas: skia.Canvas) -> None:
        paint = skia.Paint(
            Color=parse_color(self.color),
            StrokeWidth=self.thickness,
            Style=skia.Paint.kStroke_Style,  # draw along border
        )
        offset_rect = self.rect.makeOffset(
            0, -scroll
        )  # shift the rectangle vertically by -scroll
        canvas.drawRect(offset_rect, paint)


class DrawLine(BaseDrawCommand):
    """Drawing command to render a straight line."""

    def __init__(
        self,
        rect: skia.Rect,
        color: str,
        thickness: float,
    ):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll: float, canvas: skia.Canvas) -> None:
        path = (
            skia.Path()
            .moveTo(self.rect.left(), self.rect.top() - scroll)
            .lineTo(self.rect.right(), self.rect.bottom() - scroll)
        )
        paint = skia.Paint(
            Color=parse_color(self.color),
            StrokeWidth=self.thickness,
            Style=skia.Paint.kStroke_Style,  # draw along border
        )
        canvas.drawPath(path, paint)
