from browser.html_parser.nodes import Text, Element
from browser.css.css_parser import CSSParser, CSSRule
from browser.css.default import INHERITED_PROPERTIES


def style(node: Text | Element, rules: list[CSSRule]) -> None:
    """
    Apply CSS rules to a HTML node.

    The cascade is applied in the following order:
    - Inherited rules from parent (or default values for the root).
    - Stylesheet rules.
    - Inline 'style' attribute.

    After processing all sources, resolve computed values.
    Then recursively apply styles to the children.
    """
    # Inherit rules from parent (use default values for the root).
    # (note that Text node only has inherited style)
    for prop, default_val in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[prop] = node.parent.style[prop]
        else:
            node.style[prop] = default_val

    # Stylesheet rules override inherited rules
    for selector, rule_body in rules:
        if not selector.match(node):
            continue
        for prop, val in rule_body.items():
            node.style[prop] = val

    # Inline styles override inherited and stylesheet rules
    if isinstance(node, Element) and "style" in node.attributes:
        rule_body = CSSParser(node.attributes["style"]).parse_body()
        for prop, val in rule_body.items():
            node.style[prop] = val

    # Resolve computed styles after all sources have been applied,
    # before those values are inherited by children.
    #
    # [!] What if we don't resolve?
    # - h1 { font-size: 150%} makes h1 headings 50% bigger than surrounding text.
    # - a code element inside an h1 tag would inherit { font-size: 150% },
    #   making it 50% bigger than the surrounding text in the h1 tag
    #   -> not desirable

    # - Resolve percentaged font size to absolute pixel units:
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]

        percentage = float(node.style["font-size"][:-1]) / 100  # strip '%'
        parent_px = float(parent_font_size[:-2])  # strip 'px'
        node.style["font-size"] = f"{percentage * parent_px}px"

    # Recursively apply the same logic to the children
    for child in node.children:
        style(child, rules)


def cascade_priority(rule: CSSRule) -> int:
    """
    Return the selector's priority value as the cascade priority of a CSS rule.
    Higher values represent more specific selectors,
    which take precedence when multiple rules apply to the same element.
    """
    selector, _ = rule
    return selector.priority
