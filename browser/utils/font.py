import tkinter
import tkinter.font
from typing import Literal

TWeight = Literal["normal", "bold"]
TStyle = Literal["roman", "italic"]

# Global font cache: maps (size, weight, style) -> (font, label)
FONTS: dict[
    tuple[int, TWeight, TStyle],
    tuple[tkinter.font.Font, tkinter.Label],
] = {}


def get_font(size: int, weight: TWeight, style: TStyle) -> tkinter.font.Font:
    """Return a cached font object"""

    # Note:
    # - The label widget is used for performance reason
    #   (For better performance, create a dummy widget using a font before calling 'metrics')
    # - Document: https://github.com/python/cpython/blob/main/Lib/tkinter/font.py#L163

    key = (size, weight, style)
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]
