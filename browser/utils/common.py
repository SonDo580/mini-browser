import skia

from browser.html.nodes import Element
from browser.utils.font import get_font


def tree_to_list(tree, nodes: list) -> list:
    """Convert a tree structure to a list of nodes. Use in-order DFS."""
    assert hasattr(tree, "children") and isinstance(tree.children, list)

    nodes.append(tree)
    for child in tree.children:
        tree_to_list(child, nodes)
    return nodes


def get_font_from_css(node: Element) -> skia.Font:
    """
    Extract font-related CSS properties from a node and
    return the corresponding skia.Font object.
    """
    font_weight = node.style["font-weight"]

    font_style = node.style["font-style"]
    if font_style == "normal":
        font_style = "roman"
    elif font_style == "oblique":
        font_style = "italic"

    font_size = int(
        float(node.style["font-size"][:-2]) * 0.75
    )  # pixels -> points

    return get_font(font_size, font_weight, font_style)
