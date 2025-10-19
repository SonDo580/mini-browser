from __future__ import annotations
import dukpy
from typing import Any, TYPE_CHECKING
from pathlib import Path

from browser.html.nodes import Element
from browser.html.html_parser import HTMLParser
from browser.css.css_parser import CSSParser

if TYPE_CHECKING:
    from browser.tab import Tab


# Load JS runtime code
runtime_js_path: Path = Path(__file__).parent / "runtime.js"
RUNTIME_JS: str = open(runtime_js_path).read()

# JS code to dispatch event
# (JS object 'dukpy' stores the named arguments to 'evaljs')
EVENT_DISPATCH_JS = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"


class JSContext:
    """Environment to run JS code."""

    def __init__(self, tab: Tab):
        self.tab = tab
        self.interpreter = dukpy.JSInterpreter()

        # Each Element is assigned a unique numeric ID called handle.
        # JS layer can only see handles and call back to Python using them.
        self.node_to_handle: dict[Element, int] = {}
        self.handle_to_node: dict[int, Element] = {}

        # Export Python functions to the JS layer (see usage in runtime.js)
        self.interpreter.export_function("print", print)
        self.interpreter.export_function("querySelectorAll", self.__query_selector_all)
        self.interpreter.export_function("getAttribute", self.__get_attribute)
        self.interpreter.export_function("innerHTML_set", self.__set_inner_html)

        # Execute JS runtime code before any user code
        self.interpreter.evaljs(RUNTIME_JS)

    def run(self, script_src: str, code: str) -> Any:
        """Execute JS code."""
        try:
            return self.interpreter.evaljs(code)
        except dukpy.JSRuntimeError as e:
            print(f"Script {script_src} crashed: {e}")

    def dispatch_event(self, event_type: str, element: Element) -> bool:
        """
        Ask JS to dispatch an event for the given element.
        Return True if default action is prevented, False otherwise.
        """
        handle = self.node_to_handle.get(element, -1)
        do_default = self.interpreter.evaljs(
            code=EVENT_DISPATCH_JS, type=event_type, handle=handle
        )
        return not do_default

    def __query_selector_all(self, selector_text: str) -> list[int]:
        """Find all elements matching a CSS selector and return their handles."""
        selector = CSSParser(selector_text).parse_selector()

        # Find all elements matching the selector
        matched_elements: list[Element] = [
            node for node in self.tab.nodes if selector.match(node)
        ]

        # Convert the elements to handles
        return [self.__get_handle(element) for element in matched_elements]

    def __get_handle(self, element: Element) -> int:
        """
        Assign and return the handle for an Element.

        Why do we need this:
        - JS cannot directly reference Python objects.
        -> We need to map each Element to an integer.
           When JS needs to access an element, it passes this handle back to Python.
        """
        if element not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[element] = handle
            self.handle_to_node[handle] = element
        return self.node_to_handle[element]

    def __get_attribute(self, handle: int, attribute: str) -> str:
        """Return an element's attribute value."""
        element = self.handle_to_node[handle]
        return element.attributes.get(attribute, "")

    def __set_inner_html(self, handle: int, html: str) -> None:
        """innerHTML setter for an element."""
        # Our HTML parser only handle full document
        # -> wrap the snippet in html and body element
        sudo_html_root = HTMLParser(f"<html><body>{html}</body></html>").parse()

        # Extract the actual new nodes
        new_nodes = sudo_html_root.children[0].children

        # Make new nodes children of element innerHTML_set was called on
        element = self.handle_to_node[handle]
        element.children = new_nodes
        for child in element.children:
            child.parent = element

        # Re-render the page
        self.tab.render()
