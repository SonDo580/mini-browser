from __future__ import annotations
import urllib.parse
from typing import TYPE_CHECKING

from browser.constants import VSTEP
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

if TYPE_CHECKING:
    from browser.browser import Browser


class CommitData:
    """Data needed for raster and draw."""

    def __init__(
        self,
        url: URL,
        scroll: float | None,
        height: float,
        display_list: list[BaseDrawCommand],
    ):
        self.url = url
        self.scroll = scroll
        self.height = height
        self.display_list = display_list


class Tab:
    def __init__(self, browser: Browser, tab_height: float):
        self._url: URL | None = None
        self.history: list[URL] = []  # visited pages
        self.js_context: JSContext | None = None
        self.allowed_origins: list[str] | None = None  # None <-> allow all
        self.browser = browser

        self.tab_height = tab_height  # portion on screen
        self._document: DocumentLayout | None = None
        self.display_list: list[BaseDrawCommand] = []
        self.focused_element: Element | None = None
        self.scroll: float = 0

        self.scroll_changed_in_tab: bool = False
        self.needs_render: bool = False

        self.task_runner = TaskRunner(tab=self)
        self.task_runner.start_thread()

    @property
    def document(self) -> DocumentLayout:
        """Return the Document layout."""
        if not self._document:
            raise Exception("Document has not been initialized. Call load() first.")
        return self._document

    @property
    def url(self) -> URL:
        """Return the URL manager."""
        if not self._url:
            raise Exception("URL manager has not been initialized. Call load() first.")
        return self._url

    def load(self, url: URL, payload: str | None = None):
        """Fetch and display content from the given URL."""
        self._url = url
        self.history.append(url)  # record visited page

        # Start at the top when navigating to a new page
        self.scroll = 0
        self.scroll_changed_in_tab = True

        # ===== HTML =====
        # ================

        # Fetch the main page
        response_headers, html_body = url.request(referrer=url, payload=payload)

        # Decide allowed origins
        if "content-security-policy" in response_headers:
            csp_directives = response_headers["content-security-policy"].split(";")

            self.allowed_origins = []
            for directive in csp_directives:
                tokens = directive.strip().split()

                # Only handle "default-src" for now
                if tokens and tokens[0] == "default-src":
                    for origin in tokens[1:]:
                        normalized_origin = (
                            self.url.origin()
                            if origin == "'self'"
                            else URL(origin).origin()
                        )
                        self.allowed_origins.append(normalized_origin)
                    break

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

        self.set_needs_render()

    def clamp_scroll(self, scroll: float) -> float:
        """Restrict scroll offset between 0 and max_scroll."""
        content_height = self.tab_height - 2 * VSTEP
        max_scroll = self.document.height - content_height
        return max(0, min(scroll, max_scroll))

    def run_animation_frame(self, scroll: float):
        if not self.scroll_changed_in_tab:
            self.scroll = scroll  # scroll offset calculated by browser thread

        # Run callbacks requested by requestAnimationFrame()
        self.js_context.interpreter.evaljs("__runRAFHandlers()")

        # Render
        self.render()

        # May override scroll offset calculated by browser thread
        scroll = self.scroll if self.scroll_changed_in_tab else None

        # Commit
        commit_data = CommitData(
            url=self.url,
            scroll=scroll,
            height=self.document.height,
            display_list=self.display_list,
        )
        self.browser.commit(tab=self, data=commit_data)
        self.scroll_changed_in_tab = False

    def render(self):
        """Apply style and layout the document."""
        if not self.needs_render:
            return

        # Apply style rules to the HTML tree
        style(self.html_tree, self.sorted_css_rules)

        # Build layout tree
        self._document = DocumentLayout(self.html_tree)
        self.document.layout()

        # Collect draw commands (display list)
        self.display_list = []  # reset
        paint_tree(self.document, self.display_list)

        self.needs_render = False

        # May override scroll offset calculated by browser thread
        clamped_scroll = self.clamp_scroll(self.scroll)
        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True
        self.scroll = clamped_scroll

    def set_needs_render(self):
        self.needs_render = True
        self.browser.set_needs_animation_frame(tab=self)

    def click(self, x: int, tab_y: int):
        """Handle click events inside the tab content area."""
        # Ensure the layout tree is up to date
        self.render()

        # Clear focus if needed
        if self.focused_element:
            self.focused_element.is_focused = False
            self.focused_element = None
            self.set_needs_render()

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
                if self.js_context.dispatch_event("click", element):
                    return  # e.preventDefault() is called in JS

                # Navigate to the linked page
                linked_url = self.url.resolve(element.attributes["href"])
                self.load(linked_url)
                return

            elif element.tag == "input":
                if self.js_context.dispatch_event("click", element):
                    return  # e.preventDefault() is called in JS

                # Focus on the input and clear existing value
                self.focused_element = element
                element.is_focused = True
                element.attributes["value"] = ""
                self.set_needs_render()
                return

            elif element.tag == "button":
                if self.js_context.dispatch_event("click", element):
                    return  # e.preventDefault() is called in JS

                # Submit the form that contains the button
                # and navigate to the form's action URL
                while element:
                    if element.tag == "form" and "action" in element.attributes:
                        self.submit_form(element)
                        break
                    element = element.parent
                return

            element = element.parent

    def keypress(self, char: str):
        """Handle keypress event."""
        if self.focused_element and self.focused_element.tag == "input":
            if self.js_context.dispatch_event("keydown", self.focused_element):
                return  # e.preventDefault() is called in JS

            # Append character to input
            self.focused_element.attributes["value"] += char
            self.set_needs_render()

    def backspace(self):
        """Handle pressing BackSpace."""
        if self.focused_element and self.focused_element.tag == "input":
            if self.js_context.dispatch_event("keydown", self.focused_element):
                return  # e.preventDefault() is called in JS

            # Remove the last character from input
            new_value = self.focused_element.attributes["value"][:-1]
            self.focused_element.attributes["value"] = new_value
            self.set_needs_render()

    def go_back(self):
        """Go back to the previous page."""
        if len(self.history) >= 2:
            self.history.pop()
            # Pop the url before calling load(), since load() adds to history
            previous_url = self.history.pop()
            self.load(previous_url)

    def submit_form(self, form: Element):
        """Submit the form and navigate to action URL."""
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
