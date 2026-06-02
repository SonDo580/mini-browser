import skia
from typing import Literal

from browser.html.nodes import Element

# Supported font weights and styles
TWeight = Literal["normal", "bold"]
TStyle = Literal["roman", "italic"]

# Cache loaded typefaces: (weight, style) -> skia.Typeface
TYPEFACES: dict[tuple[TWeight, TStyle], skia.Typeface] = {}

# Map weight/style literals to skia.FontStyle constants
WEIGHT_MAP = {
    "normal": skia.FontStyle.kNormal_Weight,
    "bold": skia.FontStyle.kBold_Weight,
}
SLANT_MAP = {
    "roman": skia.FontStyle.kUpright_Slant,
    "italic": skia.FontStyle.kItalic_Slant,
}


def get_font(size: int, weight: TWeight, style: TStyle) -> skia.Font:
    """Return a skia.Font object.

    Skia separates fonts into 2 parts:
    - Typeface: represents a font family and its style (cached for reuse).
    - Font: represents a typeface at a particular size.
    """
    key = (weight, style)

    if key not in TYPEFACES:
        # Create font style descriptor
        skia_weight = WEIGHT_MAP[weight]
        skia_slant = SLANT_MAP[style]
        skia_width = skia.FontStyle.kNormal_Width
        style_info = skia.FontStyle(skia_weight, skia_width, skia_slant)

        # Load and cache the typeface for reuse (default font family: Arial)
        TYPEFACES[key] = skia.Typeface("Arial", style_info)

    # Return a skia.Font object for the given size
    return skia.Font(TYPEFACES[key], size)


def get_font_from_css(node: Element) -> skia.Font:
    """
    Extract font-related CSS properties from a node and
    return the corresponding skia.Font object.
    """
    font_weight = node.style["font-weight"]

    font_style = node.style["font-style"]
    if font_style == "normal":
        font_style = "roman"
    elif font_style == "oblique":
        font_style = "italic"

    font_size = int(float(node.style["font-size"][:-2]))  # remove 'px' suffix

    return get_font(font_size, font_weight, font_style)


# ===== Utility functions for working with Skia font metrics =====
def ascent(font: skia.Font) -> float:
    """Return the font ascent (negative, baseline to top of text)."""
    return font.getMetrics().fAscent


def descent(font: skia.Font) -> float:
    """Return the font descent (positive, baseline to bottom of text)."""
    return font.getMetrics().fDescent


def linespace(font: skia.Font) -> float:
    """Return total line height (distance from top to bottom of a line)."""
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent # negate negative ascent value
