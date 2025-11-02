import skia

from browser.render.base import BaseDrawCommand
from browser.utils.effects import parse_blend_mode


class Blend(BaseDrawCommand):
    """Apply blend mode and opacity to a group of objects."""

    def __init__(
        self, opacity: float, blend_mode: str | None, commands: list[BaseDrawCommand]
    ):
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.commands = commands

        # Produce a bounding box that encloses all children
        self.rect = skia.Rect.MakeEmpty()
        for command in commands:
            self.rect.join(command.rect)

    def execute(self, canvas: skia.Canvas) -> None:
        need_extra_layer = self.blend_mode is not None or self.opacity < 1

        if need_extra_layer:
            # Add a temporary surface to draw to
            paint = skia.Paint(
                Alphaf=self.opacity, BlendMode=parse_blend_mode(self.blend_mode)
            )
            canvas.saveLayer(None, paint)

        for command in self.commands:
            command.execute(canvas)

        if need_extra_layer:
            # Composite onto the parent surface
            canvas.restore()
