import tkinter

from browser.constants import WIDTH, HEIGHT, VSTEP, SCROLL_STEP
from browser.url import URL
from browser.html_parser.html_parser import HTMLParser
from browser.html_parser.nodes import Element
from browser.css.common import style, cascade_priority
from browser.css.default import DEFAULT_STYLE_SHEET
from browser.css.css_parser import CSSParser
from browser.layout.document_layout import DocumentLayout
from browser.layout.base import BaseDrawCommand, BaseLayout
from browser.layout.common import paint_tree
from browser.utils.common import tree_to_list


class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, width=WIDTH, height=HEIGHT, bg="white"
        )
        self.canvas.pack()

        self.window.bind("<Down>", self.scroll_down)  # press down key
        self.window.bind("<Up>", self.scroll_up)  # press up key
        self.window.bind("<Button-1>", self.handle_click)  # press left mouse button

        self.scroll: float = 0
        self.display_list: list[BaseDrawCommand] = []

        self._document: DocumentLayout | None = None
        self._url: URL | None = None

    @property
    def document(self) -> DocumentLayout:
        """Return the Document layout."""
        if self._document is None:
            raise ValueError("Document has not been initialized. Call load() first.")
        return self._document

    @property
    def url(self) -> URL:
        """Return the URL manager."""
        if self._url is None:
            raise ValueError("URL manager has not been initialized. Call load() first.")
        return self._url

    def load(self, url: URL) -> None:
        """Fetch and display content from the given URL."""
        self._url = url

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
        self._document = DocumentLayout(tree)
        self.document.layout()

        # Reset display list and scroll offset
        # (ensure clean state when navigating to a new page)
        self.display_list = []
        self.scroll = 0

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

    def scroll_down(self, e: tkinter.Event) -> None:
        """Scroll downward without exceeding document's height."""
        max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()

    def scroll_up(self, e: tkinter.Event) -> None:
        """Scroll upward without passing the top of the document."""
        self.scroll = max(self.scroll - SCROLL_STEP, 0)
        self.draw()

    def handle_click(self, e: tkinter.Event) -> None:
        x, y = e.x, e.y  # Extract screen coordinates
        y += self.scroll  # Convert to page coordinate

        # Collect layouts that contain the click position
        layouts = [
            layout
            for layout in tree_to_list(self.document, nodes=[])
            if isinstance(layout, BaseLayout)
            and layout.x <= x <= layout.x + layout.width
            and layout.y <= y <= layout.y + layout.height
        ]
        if not layouts:
            return

        # Find the most specific node that was clicked
        # (Real browsers have to compute stacking contexts to decide)
        clicked_node = layouts[-1].node

        # Climb back up the HTML tree to find a link element
        current_node = clicked_node
        while current_node:
            if (
                isinstance(current_node, Element)
                and current_node.tag == "a"
                and "href" in current_node.attributes
            ):
                # Navigate to the linked page
                linked_url = self.url.resolve(current_node.attributes["href"])
                return self.load(linked_url)
            
            current_node = current_node.parent
