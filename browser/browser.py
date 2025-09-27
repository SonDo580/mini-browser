import tkinter

from browser.constants import WIDTH, HEIGHT, VSTEP, SCROLL_STEP
from browser.url import URL
from browser.html_parser.html_parser import HTMLParser
from browser.layout.document_layout import DocumentLayout
from browser.layout.base import BaseDrawCommand
from browser.layout.common import paint_tree


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        self.scroll: float = 0
        self.window.bind("<Down>", self.scroll_down)

        self.document: DocumentLayout | None = None
        self.display_list: list[BaseDrawCommand] = []

    def load(self, url: URL) -> None:
        """Fetch and display content from the given URL."""
        body = url.request()
        tree = HTMLParser(body).parse()

        self.document = DocumentLayout(tree)
        self.document.layout()

        # Collect draw commands
        paint_tree(self.document, self.display_list)

        self.draw()

    def draw(self) -> None:
        """Draw the visible content onto the canvas."""
        self.canvas.delete("all")

        for draw_command in self.display_list:
            # Skip off-screen content
            if (
                draw_command.top > self.scroll + HEIGHT
                or draw_command.bottom < self.scroll
            ):
                continue

            draw_command.execute(self.scroll, self.canvas)

    def scroll_down(self, e: tkinter.Event[tkinter.Misc]) -> None:
        """Scroll downward without exceeding document's height"""
        if self.document is None:
            raise ValueError("Document has not been initialized. Call load() first.")
        
        max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()
