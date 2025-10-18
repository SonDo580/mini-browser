import tkinter
import urllib.parse

from browser.constants import VSTEP, SCROLL_STEP
from browser.url import URL
from browser.html.html_parser import HTMLParser
from browser.html.nodes import Element
from browser.css.common import style, cascade_priority
from browser.css.default import DEFAULT_STYLE_SHEET
from browser.css.css_parser import CSSParser
from browser.layout.document_layout import DocumentLayout
from browser.layout.base import BaseDrawCommand, BaseLayout
from browser.layout.common import paint_tree
from browser.utils.common import tree_to_list


class Tab:
    def __init__(self, tab_height: float):
        self._url: URL | None = None
        self.tab_height = tab_height  # visible content's height
        self.history: list[URL] = []  # track visited pages

        self._document: DocumentLayout | None = None
        self.scroll: float = 0
        self.display_list: list[BaseDrawCommand] = []

        self.focused_element: Element | None = None

    @property
    def document(self) -> DocumentLayout:
        """Return the Document layout."""
        if self._document is None:
            raise Exception("Document has not been initialized. Call load() first.")
        return self._document

    @property
    def url(self) -> URL:
        """Return the URL manager."""
        if self._url is None:
            raise Exception("URL manager has not been initialized. Call load() first.")
        return self._url

    def load(self, url: URL, payload: str | None = None) -> None:
        """Fetch and display content from the given URL."""
        self._url = url
        self.history.append(url)  # record visited page

        # Fetch and parse HTML
        body = url.request(payload)
        self.html_tree = HTMLParser(body).parse()

        # Collect default CSS rules
        css_rules = DEFAULT_STYLE_SHEET.copy()

        # Download and parse external stylesheets
        links = [
            node.attributes["href"]
            for node in tree_to_list(self.html_tree, nodes=[])
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
        self.sorted_css_rules = sorted(css_rules, key=cascade_priority)

        # Apply style and layout the document
        self.render()

    def render(self) -> None:
        """Apply style and layout the document."""
        # Apply style rules to the HTML tree
        style(self.html_tree, self.sorted_css_rules)

        # Build layout tree
        self._document = DocumentLayout(self.html_tree)
        self.document.layout()

        # Reset display list and scroll offset
        # (ensure clean state when navigating to a new page)
        self.display_list = []
        self.scroll = 0

        # Collect draw commands (display list)
        paint_tree(self.document, self.display_list)

    def draw(self, canvas: tkinter.Canvas, offset: float) -> None:
        """Draw the visible content onto the canvas."""
        for draw_command in self.display_list:
            # Skip off-screen content
            if (
                draw_command.rect.top > self.scroll + self.tab_height
                or draw_command.rect.bottom < self.scroll
            ):
                continue

            # Shift content downward by the chrome height (offset)
            draw_command.execute(scroll=self.scroll - offset, canvas=canvas)

    def scroll_down(self) -> None:
        """Scroll downward without exceeding document's height."""
        # - content_height = tab_height - padding
        #   max_y = document_height - content_height
        # - If document is shorter than content area,
        #   scrolling should happen at all -> max_y stays at 0
        max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)

    def scroll_up(self) -> None:
        """Scroll upward without passing the top of the document."""
        self.scroll = max(self.scroll - SCROLL_STEP, 0)

    def click(self, x: int, tab_y: int) -> None:
        """Handle click events inside the tab content area."""
        # Clear focus
        if self.focused_element:
            self.focused_element.is_focused = False
            self.focused_element = None

        # Convert screen coordinates to page coordinates
        y = tab_y + self.scroll

        # Collect layouts that contain the click position
        layouts = [
            layout
            for layout in tree_to_list(self.document, nodes=[])
            if isinstance(layout, BaseLayout)
            and layout.x <= x <= layout.x + layout.width
            and layout.y <= y <= layout.y + layout.height
        ]
        if not layouts:
            # Re-render since we might have unfocused an input element
            self.render()
            return

        # Find the most specific node that was clicked
        # (Real browsers have to compute stacking contexts to decide)
        clicked_node = layouts[-1].node

        # Climb back up the HTML tree
        element = (
            clicked_node if isinstance(clicked_node, Element) else clicked_node.parent
        )
        while element:
            if element.tag == "a" and "href" in element.attributes:
                # Navigate to the linked page
                linked_url = self.url.resolve(element.attributes["href"])
                return self.load(linked_url)  # reload
            elif element.tag == "input":
                # Focus on the input and clear existing value
                self.focused_element = element
                element.is_focused = True
                element.attributes["value"] = ""
                return self.render()  # re-render
            elif element.tag == "button":
                # Submit the form that contains the button
                while element:
                    if element.tag == "form" and "action" in element.attributes:
                        return self.submit_form(element)
                    element = element.parent
                break

            element = element.parent

        # Re-render since we might have unfocused an input element
        self.render()

    def keypress(self, char: str) -> None:
        """Handle keypress event inside tab content area."""
        if self.focused_element and self.focused_element.tag == "input":
            # Edit current input value
            self.focused_element.attributes["value"] += char
            self.render()  # re-render

    def go_back(self) -> None:
        """Go back to the previous page."""
        # Pop the urls before calling 'load', since 'load' adds to history
        if len(self.history) >= 2:
            self.history.pop()
            previous_url = self.history.pop()
            self.load(previous_url)

    def submit_form(self, form: Element) -> None:
        """Submit the form."""
        # Find all input elements in the form
        inputs = [
            node
            for node in tree_to_list(form, nodes=[])
            if isinstance(node, Element)
            and node.tag == "input"
            and "name" in node.attributes
        ]

        # Build request body
        form_data = {
            input.attributes["name"]: input.attributes.get("value", "")
            for input in inputs
        }
        body = urllib.parse.urlencode(form_data)

        # Make a POST request
        url = self.url.resolve(form.attributes["action"])
        self.load(url, body)
