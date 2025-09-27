from __future__ import annotations


class Text:
    """Represent a text node"""

    def __init__(self, text: str, parent: Element | None):
        self.text = text
        self.children = []  # always empty since text node is a leaf
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    """Represent an HTML element"""

    def __init__(self, tag: str, attributes: dict[str, str], parent: Element | None):
        self.tag = tag
        self.attributes = attributes
        self.children: list[Element | Text] = []
        self.parent = parent

    def __repr__(self):
        return f"<{self.tag}>"
