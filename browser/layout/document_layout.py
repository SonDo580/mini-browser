from browser.constants import WIDTH, HSTEP, VSTEP
from browser.layout.base import BaseLayout
from browser.layout.block_layout import BlockLayout
from browser.render.base import BaseDrawCommand
from browser.html.nodes import Element


class DocumentLayout(BaseLayout):
    """Represent the root of the layout tree"""

    def __init__(self, html_root: Element):
        self.node = html_root
        self.parent = None
        self.previous = None
        self.children: list[BlockLayout] = []

    def layout(self):
        """Compute display info and recursively layout children."""
        self._x = HSTEP
        self._y = VSTEP
        self._width = WIDTH - 2 * HSTEP

        child_layout = BlockLayout(node=self.node, parent=self, previous=None)
        self.children.append(child_layout)
        child_layout.layout()

        # Compute document's height after child's layout() call
        self._height = child_layout.height

    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        return []
