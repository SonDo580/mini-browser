import skia
from typing import Literal

# Supported font weights and styles
TWeight = Literal["normal", "bold"]
TStyle = Literal["roman", "italic"]

# Cache loaded typefaces: (weight, style) -> skia.Typeface
TYPEFACES: dict[tuple[TWeight, TStyle], skia.Typeface] = {}

# Map weight/style literals to Skia constants
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


# ===== Utility functions for working with Skia font metrics =====
def ascent(font: skia.Font) -> float:
    """Return the font ascent (distance from baseline to top of text)."""
    return font.getMetrics().fAscent


def descent(font: skia.Font) -> float:
    """Return the font descent (distance from baseline to bottom of text)."""
    return font.getMetrics().fDescent


def linespace(font: skia.Font) -> float:
    """Return total line height (distance from top to bottom of a line)."""
    # Skia font's ascent and descent are positive if they go downward and negative if they go upward
    # -> negate ascent value when computing linespace
    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent
