import tkinter

from browser.constants import WIDTH, HEIGHT, VSTEP, SCROLL_STEP
from browser.url import URL
from browser.html_parser.html_parser import HTMLParser
from browser.html_parser.nodes import Element
from browser.css.common import style, cascade_priority
from browser.css.default import DEFAULT_STYLE_SHEET
from browser.css.css_parser import CSSParser
from browser.layout.document_layout import DocumentLayout
from browser.layout.base import BaseDrawCommand
from browser.layout.common import paint_tree
from browser.utils.common import tree_to_list


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, width=WIDTH, height=HEIGHT, bg="white"
        )
        self.canvas.pack()

        self.scroll: float = 0
        self.window.bind("<Down>", self.scroll_down)

        self.document: DocumentLayout | None = None
        self.display_list: list[BaseDrawCommand] = []

    def load(self, url: URL) -> None:
        """Fetch and display content from the given URL."""
        # ===== HTML =====
        # ================
        # Fetch and parse HTML
        body = url.request()
        tree = HTMLParser(body).parse()

        # ==== CSS =====
        # ==============
        # Collect default CSS rules
        css_rules = DEFAULT_STYLE_SHEET.copy()

        # Download and parse external stylesheets
        links = [
            node.attributes["href"]
            for node in tree_to_list(tree, nodes=[])
            if isinstance(node, Element)
            and node.tag == "link"
            and node.attributes.get("rel") == "stylesheet"
            and "href" in node.attributes
        ]
        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
                css_rules.extend(CSSParser(body).parse())
            except:
                continue  # Ignore failed style sheets

        # Apply cascade sorting:
        # - Sort rules by priority (specificity). Preserve source order if there's a tie.
        # - Effect: later rules override earlier ones for the same property.
        sorted_rules = sorted(css_rules, key=cascade_priority)

        # Apply style rules to the HTML tree
        style(tree, sorted_rules)

        # ===== Layout =====
        # ==================
        # Build layout tree
        self.document = DocumentLayout(tree)
        self.document.layout()

        # Collect draw commands (display list)
        paint_tree(self.document, self.display_list)

        # ===== Render =====
        # ==================
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

    def scroll_down(self, e) -> None:
        """Scroll downward without exceeding document's height"""
        if self.document is None:
            raise ValueError("Document has not been initialized. Call load() first.")

        max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()
