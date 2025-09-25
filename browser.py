import socket
import ssl
import sys
import tkinter
import tkinter.font


class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

        # Separate host and path
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # Default port
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        # Separate host and custom port
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        """Send HTTP request and return response body"""

        # Establish TCP connection
        s = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))

        # Upgrade to TLS for HTTPS
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # Send HTTP GET request
        request = f"GET {self.path} HTTP/1.0\r\n"
        request += f"Host: {self.host}\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))

        # Parse response status line and headers
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # Reject chunked or compressed responses
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # Return response body and close connection
        content = response.read()
        s.close()
        return content


class Text:
    """Represent a text node"""

    def __init__(self, text, parent):
        self.text = text
        self.children = []  # this is always empty since text node is a leaf
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    """Represent a node in the HTML tree"""

    def __init__(self, tag, attributes, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        return f"<{self.tag}>"


class HTMLParser:
    def __init__(self, body):
        self.body = body
        self.unfinished = []

        self.SELF_CLOSING_TAGS = [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        ]

        self.HEAD_TAGS = [
            "base",
            "basefont",
            "bgsound",
            "noscript",
            "link",
            "meta",
            "title",
            "style",
            "script",
        ]

    def parse(self):
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

    def add_text(self, text):
        """Add a text node as the child of the last unfinished node"""
        # Skip whitespace-only text nodes for simplicity
        if text.isspace():
            return

        self.implicit_tags(tag=None)

        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag):
        # Skip doctype declaration and comments
        # <!DOCTYPE html>
        # <!-- example comment -->
        if tag.startswith("!"):
            return

        self.implicit_tags(tag)

        # Handle close tag: add the finished node to the previous unfinished node
        if tag.startswith("/"):
            # Keep the root node on the stack
            if len(self.unfinished) == 1:
                return

            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
            return

        tag, attributes = self.get_tag_and_attributes(tag)

        # Handle self-closing tag: auto-close and add to the previous unfinished node
        if tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
            return

        # Handle open tag: add an unfinished node to the end of the list
        parent = (
            self.unfinished[-1] if self.unfinished else None
        )  # The root node has no parent
        node = Element(tag, attributes, parent)
        self.unfinished.append(node)

    def implicit_tags(self, tag):
        """Insert missing implicit tags (html, head, body) to keep the tree valid"""
        while True:
            open_tags = [node.tag for node in self.unfinished]

            # Ensure <html> is the root
            if open_tags == [] and tag != "html":
                self.add_tag("html")

            # If only <html> is open, insert <head> or <body>
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")

            # If we're inside <head>, but encounter a tag that should not be in <head>,
            # auto-close <head> to continue parsing inside <body>
            elif (
                open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS
            ):
                self.add_tag("/head")

            # Technically </body> and </html> tags can also be implicit,
            # but 'finish' method already closes any unfinished tags

            else:
                break

    def get_tag_and_attributes(self, raw_tag):
        parts = raw_tag.split()
        tag = parts[0].casefold()

        attributes = {}
        for attribute in parts[1:]:
            if "=" in attribute:
                # Attribute with an explicit value (key=value)
                key, value = attribute.split("=", 1)

                # Remove surrounding quotes from the value if present
                if len(value) > 2 and value[0] in ["'", '"']:
                    value = value[1:-1]
            else:
                # Attribute without value (e.g. disabled, checked)
                key, value = attribute, ""

            attributes[key.casefold()] = value

        return tag, attributes

    def finish(self):
        """Turn the incomplete tree into a complete tree by finishing any unfinished nodes"""
        if not self.unfinished:
            self.implicit_tags(tag=None)

        # - Keep popping nodes and attach them as children to their parent
        # - Continue until only the root node remains
        # -> auto-close any tags that weren't explicitly closed in HTML
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)

        # Return the root node
        return self.unfinished.pop()


# Global font cache
FONTS = {}


def get_font(size, weight, style):
    """Return a cached font object"""

    # Note:
    # - The label widget is used for performance reason
    #   (For better performance, create a dummy widget using a font before calling 'metrics')
    # - Document: https://github.com/python/cpython/blob/main/Lib/tkinter/font.py#L163

    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18


class Layout:
    def __init__(self, tree):
        self.display_list = []

        # buffer to store words in a line
        # entries have x but not y (not computed in the first pass)
        self.line = []

        self.cursor_x = HSTEP
        self.cursor_y = VSTEP

        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        # Wark the HTML tree recursively
        self.recurse(tree)

        # Flush the line buffer once more
        self.flush()

    def recurse(self, node):
        """Wark the HTML tree recursively"""
        if isinstance(node, Text):
            for word in node.text.split():
                self.handle_word(word)
        elif isinstance(node, Element):
            self.open_tag(node.tag)
            for child in node.children:
                self.recurse(child)
            self.close_tag(node.tag)

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "br":
            self.flush()

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP

    def handle_word(self, word):
        font = get_font(self.size, self.weight, self.style)
        width = font.measure(word)

        # Flush the line buffer when reaching right edge
        if self.cursor_x + width > WIDTH - HSTEP:
            self.flush()

        self.line.append((self.cursor_x, word, font))
        self.cursor_x += width + font.measure(" ")

    def flush(self):
        """
        Flush the line buffer:
        - Calculate baseline for current line.
        - Align words along baseline and add to display list.
        - Calculate cursor_y for next line.
        - Reset cursor_x and line buffer for next line.

        Why we need this:
        - We want to align the characters along their baseline.
        - Characters on the same line may have different sizes.
        - We can only finalize the positions after we know the max ascent.
        """
        if not self.line:
            return

        # Calculate baseline for current line
        metrics = [font.metrics() for _, _, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])
        baseline = self.cursor_y + max_ascent * 1.25

        # Calculate next cursor_y
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + max_descent * 1.25

        # Place each word relative to baseline and add to display list
        # (note that we use x, y as the top-left coordinates)
        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        # Reset cursor_x and line buffer
        self.cursor_x = HSTEP
        self.line = []


SCROLL_STEP = 100


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        self.scroll = 0
        self.window.bind("<Down>", self.scroll_down)

    def load(self, url):
        """Fetch and display content from the given URL"""
        body = url.request()
        tree = HTMLParser(body).parse()
        self.display_list = Layout(tree).display_list
        self.draw()

    def draw(self):
        """Draw the visible content on the screen"""
        self.canvas.delete("all")

        for x, y, word, font in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue

            self.canvas.create_text(
                x, y - self.scroll, text=word, anchor="nw", font=font
            )

    def scroll_down(self, e):
        """Scroll downward and redraw the screen"""
        self.scroll += SCROLL_STEP
        self.draw()


if __name__ == "__main__":
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
