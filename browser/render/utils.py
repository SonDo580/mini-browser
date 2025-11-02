import skia

from browser.html.nodes import Element, Text
from browser.render.base import BaseDrawCommand
from browser.render.draw_commands import DrawRoundedRect
from browser.render.effect_commands import Blend


def paint_visual_effects(
    node: Text | Element, commands: list[BaseDrawCommand], rect: skia.Rect
) -> list[BaseDrawCommand]:
    """Wrap drawing commands with visual effects."""
    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = node.style.get("mix-blend-mode")

    # Handle "overflow: clip"
    # - Create a new surface and draw a rounded rectangle mask.
    #   The mask color doesn't matter as long as it's opaque.
    # - Blend using destination-in mode to keep only destination content inside the shape.
    #   + Content outside mask -> multiplied by alpha 0 -> becomes transparent.
    #   + Content inside mask -> multiplied by alpha 1 -> stays visible.
    if node.style.get("overflow", "visible") == "clip":
        radius = float(node.style.get("border-radius", "0px")[:-2])
        commands.append(
            Blend(
                opacity=1.0,
                blend_mode="destination-in",
                commands=[DrawRoundedRect(rect, radius, "white")],
            )
        )

        # Blend operation also isolates element contents
        # -> always set blend mode if we need clipping
        if not blend_mode:
            blend_mode = "source-over"

    return [Blend(opacity, blend_mode, commands)]
