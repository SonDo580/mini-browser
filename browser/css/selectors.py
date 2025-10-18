from __future__ import annotations

from browser.html.nodes import Text, Element


class TagSelector:
    def __init__(self, tag: str):
        self.tag = tag
        self.priority: int = 1

    def match(self, node: Text | Element) -> bool:
        """Test if this selector matches an element."""
        return isinstance(node, Element) and node.tag == self.tag


class DescendantSelector:
    def __init__(
        self, ancestor: TagSelector | DescendantSelector, descendant: TagSelector
    ) -> bool:
        self.ancestor = ancestor
        self.descendant = descendant
        self.priority: int = ancestor.priority + descendant.priority

    def match(self, node: Text | Element) -> bool:
        """Test if this selector matches an element."""
        if not self.descendant.match(node):
            return False

        parent = node.parent
        while parent:
            if self.ancestor.match(parent):
                return True
            parent = parent.parent

        return False
