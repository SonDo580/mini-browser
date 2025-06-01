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
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
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
    def __init__(self, text):
        self.text = text


class Tag:
    def __init__(self, tag):
        self.tag = tag


def lex(body):
    """Gather tokens (Tag/Text objects) from HTML document"""
    output = []
    buffer = ""
    in_tag = False

    for c in body:
        if c == "<":
            in_tag = True
            if buffer:
                output.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            output.append(Tag(buffer))  # allow <> tag
            buffer = ""
        else:
            buffer += c

    if not in_tag and buffer:
        output.append(Text(buffer))

    return output


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
    def __init__(self, tokens):
        self.display_list = []

        # buffer to store words in a line
        # entries have x but not y (not computed in the first pass)
        self.line = []

        self.cursor_x = HSTEP
        self.cursor_y = VSTEP

        self.weight = "normal"
        self.style = "roman"
        self.size = 12

        # Process the tokens
        for token in tokens:
            self.handle_token(token)

        # Flush the line buffer once more
        self.flush()

    def handle_token(self, token):
        if isinstance(token, Text):
            for word in token.text.split():
                self.handle_word(word)
        elif token.tag == "i":
            self.style = "italic"
        elif token.tag == "/i":
            self.style = "roman"
        elif token.tag == "b":
            self.weight = "bold"
        elif token.tag == "/b":
            self.weight = "normal"
        elif token.tag == "small":
            self.size -= 2
        elif token.tag == "/small":
            self.size += 2
        elif token.tag == "big":
            self.size += 4
        elif token.tag == "/big":
            self.size -= 4
        elif token.tag == "br":
            self.flush()
        elif token.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP

    def handle_word(self, word):
        font = get_font(self.size, self.weight, self.style)
        width = font.measure(word)
        self.line.append((self.cursor_x, word, font))
        self.cursor_x += width + font.measure(" ")

        # Flush the line buffer when reaching right edge
        if self.cursor_x + width > WIDTH - HSTEP:
            self.flush()

    def flush(self):
        """
        Flush the line buffer:
        - Align words along baseline.
        - Update cursor_x and cursor_y.
        - Add all words (on the line) to display list.
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
        tokens = lex(body)
        self.display_list = Layout(tokens).display_list
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
