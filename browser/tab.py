import skia
import urllib.parse

from browser.constants import VSTEP, SCROLL_STEP
from browser.url import URL
from browser.html.html_parser import HTMLParser
from browser.html.nodes import Element, Text
from browser.css.utils import style, cascade_priority
from browser.css.default import DEFAULT_STYLE_SHEET
from browser.css.css_parser import CSSParser
from browser.layout.document_layout import DocumentLayout
from browser.layout.base import BaseLayout
from browser.layout.utils import paint_tree
from browser.render.base import BaseDrawCommand
from browser.utils.common import tree_to_list
from browser.js.js_context import JSContext
from browser.tasks import TaskRunner, Task


class Tab:
    def __init__(self, tab_height: float):
        self._url: URL | None = None
        self.tab_height = tab_height  # visible content's height
        self.history: list[URL] = []  # track visited pages
        self.js_context: JSContext | None = None
        self.task_runner = TaskRunner(self)

        # Origins that we are allowed to make requests to
        # (None means allow all)
        self.allowed_origins: list[str] | None = None

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

        # Start at the top when navigating to a new page
        self.scroll = 0

        # ===== HTML =====
        # ================

        # Fetch the main page
        response_headers, html_body = url.request(referrer=url, payload=payload)

        # Decide allowed origins
        if "content-security-policy" in response_headers:
            content_security_policy = response_headers[
                "content-security-policy"
            ].split()
            if (
                len(content_security_policy) > 0
                and content_security_policy[0] == "default-src"
            ):
                self.allowed_origins = []
                for origin in content_security_policy[1:]:
                    self.allowed_origins.append(URL(origin).origin())

        # Parse HTML
        self.html_tree = HTMLParser(html_body).parse()
        self.nodes: list[Element | Text] = tree_to_list(self.html_tree, nodes=[])

        # ===== CSS =====
        # ===============

        # Collect default CSS rules
        css_rules = DEFAULT_STYLE_SHEET.copy()

        # Download and parse external stylesheets
        links = [
            node.attributes["href"]
            for node in self.nodes
            if isinstance(node, Element)
            and node.tag == "link"
            and node.attributes.get("rel") == "stylesheet"
            and "href" in node.attributes
        ]
        for link in links:
            style_url = url.resolve(link)
            if not self.allowed_request(style_url):
                print(f"Block link {style_url} due to CSP")
                continue

            try:
                _, css_body = style_url.request(referrer=url)
                css_rules.extend(CSSParser(css_body).parse())
            except:
                continue  # Ignore failed style sheets

        # Apply cascade sorting:
        # - Sort rules by priority (specificity). Preserve source order if there's a tie.
        # - Effect: later rules override earlier ones for the same property.
        self.sorted_css_rules = sorted(css_rules, key=cascade_priority)

        # ===== JavaScript =====
        # ======================
        
        # Discard existing JS context then create a new one
        if self.js_context:
            self.js_context.discard()
        self.js_context = JSContext(self)

        # Download and run all scripts
        script_sources = [
            node.attributes["src"]
            for node in self.nodes
            if isinstance(node, Element)
            and node.tag == "script"
            and "src" in node.attributes
        ]
        for script_src in script_sources:
            script_url = url.resolve(script_src)
            if not self.allowed_request(script_url):
                print(f"Block script {script_url} due to CSP")
                continue

            try:
                _, js_body = script_url.request(referrer=url)
            except:
                continue  # Ignored failed requests

            # Schedule a task to execute the script
            task = Task(self.js_context.run, script_src, js_body)
            self.task_runner.schedule_task(task)

        # ===== Rendering =====
        self.render()

    def render(self) -> None:
        """Apply style and layout the document."""
        # Reset display list before re-rendering
        self.display_list = []

        # Apply style rules to the HTML tree
        style(self.html_tree, self.sorted_css_rules)

        # Build layout tree
        self._document = DocumentLayout(self.html_tree)
        self.document.layout()

        # Collect draw commands (display list)
        paint_tree(self.document, self.display_list)

    def raster(self, canvas: skia.Canvas) -> None:
        """Draw the whole tab onto the canvas."""
        for draw_command in self.display_list:
            draw_command.execute(canvas)

    def scroll_down(self) -> bool:
        """
        Scroll downward without exceeding document's height.
        Return True if scroll value changed.
        """
        # . content_height = tab_height - padding
        #   max_y = document_height - content_height
        # . If document is shorter than content area,
        #   scrolling should happen at all -> max_y stays at 0
        max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)

        old_scroll = self.scroll
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        return self.scroll != old_scroll

    def scroll_up(self) -> bool:
        """
        Scroll upward without passing the top of the document.
        Return True if scroll value changed.
        """
        old_scroll = self.scroll
        self.scroll = max(self.scroll - SCROLL_STEP, 0)
        return self.scroll != old_scroll

    def click(self, x: int, tab_y: int) -> bool:
        """Handle click events inside the tab content area. Return True if handled."""
        # Clear focus
        cleared_focus = False
        if self.focused_element:
            self.focused_element.is_focused = False
            self.focused_element = None
            cleared_focus = True

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
            if not cleared_focus:
                return False
            self.render()
            return True

        # Find the most specific node that was clicked
        # (Real browsers have to compute stacking contexts to decide)
        clicked_node = layouts[-1].node

        # Climb back up the HTML tree
        element = (
            clicked_node if isinstance(clicked_node, Element) else clicked_node.parent
        )
        while element:
            if element.tag == "a" and "href" in element.attributes:
                if self.js_context.dispatch_event("click", element):
                    return True  # e.preventDefault() is called in JS

                # Navigate to the linked page
                linked_url = self.url.resolve(element.attributes["href"])
                self.load(linked_url)  # reload
                return True
            elif element.tag == "input":
                if self.js_context.dispatch_event("click", element):
                    return True  # e.preventDefault() is called in JS

                # Focus on the input and clear existing value
                self.focused_element = element
                element.is_focused = True
                element.attributes["value"] = ""
                self.render()  # re-render
                return True
            elif element.tag == "button":
                if self.js_context.dispatch_event("click", element):
                    return True  # e.preventDefault() is called in JS

                # Submit the form that contains the button
                while element:
                    if element.tag == "form" and "action" in element.attributes:
                        self.submit_form(element)
                        return True
                    element = element.parent
                break

            element = element.parent

        if not cleared_focus:
            return False
        self.render()
        return True

    def keypress(self, char: str) -> bool:
        """Handle keypress event. Return True if handled."""
        if self.focused_element and self.focused_element.tag == "input":
            if self.js_context.dispatch_event("keydown", self.focused_element):
                return True  # e.preventDefault() is called in JS

            # Append character to input
            self.focused_element.attributes["value"] += char
            self.render()  # re-render
            return True
        return False

    def backspace(self) -> bool:
        """Handle pressing BackSpace. Return True if handled."""
        if self.focused_element and self.focused_element.tag == "input":
            if self.js_context.dispatch_event("keydown", self.focused_element):
                return True  # e.preventDefault() is called in JS

            # Remove the last character from input
            new_value = self.focused_element.attributes["value"][:-1]
            self.focused_element.attributes["value"] = new_value
            self.render()  # re-render
            return True

    def go_back(self) -> None:
        """Go back to the previous page."""
        # Pop the urls before calling 'load', since 'load' adds to history
        if len(self.history) >= 2:
            self.history.pop()
            previous_url = self.history.pop()
            self.load(previous_url)

    def submit_form(self, form: Element) -> None:
        """Submit the form."""
        if self.js_context.dispatch_event("submit", form):
            return  # e.preventDefault() is called in JS

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

    def allowed_request(self, url: URL) -> bool:
        return self.allowed_origins is None or url.origin() in self.allowed_origins
