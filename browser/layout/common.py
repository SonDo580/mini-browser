from browser.layout.base import BaseDrawCommand, BaseLayout


def paint_tree(layout: BaseLayout, display_list: list[BaseDrawCommand]):
    """
    Recursively walk the layout tree and collect all drawing commands (display list).
    Each layout object generates its own drawing commands via the `paint` method.
    """
    # [!] Nested layouts should be painted on top of parent layout (z-axis)
    #     -> call 'paint' on current layout before recursing into subtree
    display_list.extend(layout.paint())
    for child_layout in layout.children:
        paint_tree(child_layout, display_list)
