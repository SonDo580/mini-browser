from browser.constants import WIDTH, HSTEP, VSTEP
from browser.layout.base import BaseLayout, BaseDrawCommand
from browser.layout.block_layout import BlockLayout
from browser.html_parser.nodes import Element


class DocumentLayout(BaseLayout):
    """Represent the root of the layout tree"""

    def __init__(self, html_root: Element):
        super().__init__()
        self.html_root = html_root
        self.children: list[BlockLayout] = []

    def layout(self) -> None:
        """Compute display info and recursively layout children."""
        self._x = HSTEP
        self._y = VSTEP
        self._width = WIDTH - 2 * HSTEP

        child = BlockLayout(node=self.html_root, parent=self, previous=None)
        self.children.append(child)
        child.layout()

        # Compute document's height after child's 'layout' call
        self._height = child.height

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        return []
