from browser.constants import SELF_CLOSING_TAGS, HEAD_TAGS
from browser.html.nodes import Element, Text


class HTMLParser:
    def __init__(self, body: str):
        self.body = body
        self.unfinished: list[Element] = []

    def parse(self) -> Element:
        """Parse the raw HTML string into a tree. Return the root element."""
        text = ""
        in_tag = False

        for c in self.body:
            if c == "<":
                in_tag = True
                if text:
                    self.add_text(text)
                text = ""
            elif c == ">":
                in_tag = False
                self.add_tag(text)  # allow <> tag
                text = ""
            else:
                text += c

        if not in_tag and text:
            self.add_text(text)

        return self.finish()

    def add_text(self, text: str):
        """Add a text node as the child of the last unfinished element"""
        # Skip whitespace-only text nodes for simplicity
        if text.isspace():
            return

        # Insert implicit tags to keep the tree valid
        self.implicit_tags(tag=None)

        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag: str):
        # Skip doctype declaration and comments
        # (<!DOCTYPE html>, <!-- example comment -->)
        if tag.startswith("!"):
            return

        # Insert implicit tags to keep the tree valid
        self.implicit_tags(tag)

        # Handle close tag: add the finished element to the previous unfinished element
        if tag.startswith("/"):
            # Keep the root node on the stack
            if len(self.unfinished) == 1:
                return

            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
            return

        tag, attributes = self.get_tag_and_attributes(tag)

        # Handle self-closing tag: auto-close and add to the previous unfinished element
        if tag in SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
            return

        # Handle open tag: add an unfinished element to the end of the list
        parent = (
            self.unfinished[-1] if self.unfinished else None
        )  # The root node has no parent
        node = Element(tag, attributes, parent)
        self.unfinished.append(node)

    def implicit_tags(self, tag: str | None):
        """Insert missing implicit tags (html, head, body) to keep the tree valid."""
        while True:
            open_tags = [node.tag for node in self.unfinished]

            # Ensure <html> is the root
            if open_tags == [] and tag != "html":
                self.add_tag("html")

            # If only <html> is open, insert <head> or <body>
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")

            # If we're inside <head>, but encounter a tag that should not be in <head>,
            # auto-close <head> to continue parsing inside <body>
            elif open_tags == ["html", "head"] and tag not in ["/head"] + HEAD_TAGS:
                self.add_tag("/head")

            # Technically </body> and </html> tags can also be implicit,
            # but 'finish' method already closes any unfinished tags,
            # so we don't need to handle them here

            else:
                break

    def get_tag_and_attributes(self, raw_tag: str) -> tuple[str, dict[str, str]]:
        """
        Parse a raw tag string into:
        - the tag name.
        - a dictionary of attribute key/value pairs.
        """
        parts = self.__split_outside_quotes(raw_tag)
        tag = parts[0].casefold()

        attributes: dict[str, str] = {}
        for attribute in parts[1:]:
            if "=" in attribute:
                # Attribute with an explicit value (key=value)
                key, value = attribute.split("=", 1)

                # Remove surrounding quotes from the value if present
                if len(value) >= 2 and value[0] in ["'", '"'] and value[0] == value[-1]:
                    value = value[1:-1]
            else:
                # Attribute without value (e.g. disabled, checked)
                key, value = attribute, ""

            attributes[key.casefold()] = value

        return tag, attributes

    def __split_outside_quotes(self, s: str) -> list[str]:
        """Split a string by whitespace. Preserve quoted values."""
        parts: list[str] = []
        current_part_chars: list[str] = []
        i = 0

        while i < len(s):
            char = s[i]

            # Append all characters between quotes to current part
            if char in ["'", '"']:
                quote = char
                current_part_chars.append(quote)
                i += 1
                while i < len(s):
                    current_part_chars.append(s[i])
                    if s[i] == quote:
                        i += 1
                        break
                    i += 1
                continue

            # Encounter whitespace outside quotes
            if char.isspace():
                # Collect then reset current part if present
                if current_part_chars:
                    parts.append("".join(current_part_chars))
                    current_part_chars = []

                # Skip contiguous spaces
                while i < len(s) and s[i].isspace():
                    i += 1
                continue

            # Add regular characters to current part
            current_part_chars.append(char)
            i += 1

        # Handle the last part if present
        if current_part_chars:
            parts.append("".join(current_part_chars))

        return parts

    def finish(self) -> Element:
        """
        Turn the incomplete tree into a complete tree.
        Return the root element.
        """
        # If no elements were added, insert implicit tags to keep the tree valid
        if not self.unfinished:
            self.implicit_tags(tag=None)

        # - Keep popping elements and attach them as children to their parent
        #   (auto-close any tags that weren't explicitly closed in HTML)
        # - Continue until only the root element remains
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        # Return the root element
        return self.unfinished.pop()
