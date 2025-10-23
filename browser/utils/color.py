import skia

# Map color names to their hex values
# Reference: https://developer.mozilla.org/en-US/docs/Web/CSS/named-color
COLOR_HEX = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "lightblue": "#add8e6",
    "lightgreen": "#90ee90",
    "orange": "#ffa500",
    "orangered": "#ff4500",
    "gray": "#808080",
    # add more...
}


def parse_color(color: str) -> skia.Color:
    """Convert a color string into a Skia Color object."""
    color = color.lower()

    # Resolve named color to its hex form
    if color in COLOR_HEX:
        return parse_color(COLOR_HEX[color])

    # Handle hex format
    if color.startswith("#") and len(color) == 7:
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return skia.Color(r, g, b)
        except ValueError:
            pass  # invalid hex digits, fall through to default

    return skia.ColorBLACK  # fallback
