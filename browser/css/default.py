from pathlib import Path

from browser.css.css_parser import CSSParser, CSSRule

# Load and parse default CSS rules
default_css_path: Path = Path(__file__).parent / "browser.css"
DEFAULT_STYLE_SHEET: list[CSSRule] = CSSParser(open(default_css_path).read()).parse()

# Implement inheritance for 4 font properties
# - Children inherit parent's rules.
# - Explicit rules override inherited rules.
# - The values in this dict is each property's default.
INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}
