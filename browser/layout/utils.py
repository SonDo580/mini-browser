from browser.layout.base import BaseLayout
from browser.render.base import BaseDrawCommand


def paint_tree(layout: BaseLayout, display_list: list[BaseDrawCommand]) -> None:
    """Recursively walk the layout tree and collect drawing commands (display list)."""
    should_paint = layout.should_paint()
    commands: list[BaseDrawCommand] = []

    # Nested layouts are painted on top of their parent (z-axis)
    # -> paint current layout before recursing into children
    if should_paint:
        commands.extend(layout.paint())

    for child_layout in layout.children:
        paint_tree(child_layout, commands)

    # Visual effects apply to the entire subtree's display list,
    # -> paint visual effects after recursing into children
    if should_paint:
        commands = layout.paint_effects(commands)

    display_list.extend(commands)
