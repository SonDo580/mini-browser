from enum import Enum
import sdl2
import skia

from browser.constants import WIDTH, HEIGHT
from browser.url import URL
from browser.chrome import Chrome
from browser.tab import Tab


class BrowserComponent(Enum):
    CHROME = "chrome"
    CONTENT = "content"


class Browser:
    def __init__(self):
        self.tabs: list[Tab] = []
        self._active_tab: Tab | None = None
        self.focused_component: BrowserComponent | None = None

        # Create SDL Window for browser GUI
        self.sdl_window = sdl2.SDL_CreateWindow(
            b"Browser",  # title (as bytes)
            sdl2.SDL_WINDOWPOS_CENTERED,  # x position (centered on screen)
            sdl2.SDL_WINDOWPOS_CENTERED,  # y position (centered on screen)
            WIDTH,  # window's width in pixels
            HEIGHT,  # window's height in pixels
            sdl2.SDL_WINDOW_SHOWN,  # make the window visible
        )

        # Define masks that tell SDL which bits correspond to which color channel
        # - Each pixel uses 4 bytes for (R, G, B, A) channels.
        # - The byte order depends on the CPU’s endianness.
        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            # Big-endian: bytes stored as [RR][GG][BB][AA]
            self.RED_MASK = 0xFF000000
            self.GREEN_MASK = 0x00FF0000
            self.BLUE_MASK = 0x0000FF00
            self.ALPHA_MASK = 0x000000FF
        else:
            # Little-endian (most systems): bytes stored as [AA][BB][GG][RR]
            self.RED_MASK = 0x000000FF
            self.GREEN_MASK = 0x0000FF00
            self.BLUE_MASK = 0x00FF0000
            self.ALPHA_MASK = 0xFF000000

        # Create a surface for Skia to draw to
        # (A surface is a chunk of memory representing pixels on the screen.)
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH,  # surface's width in pixels
                HEIGHT,  # surface's height in pixels
                ct=skia.kRGBA_8888_ColorType,  # each pixel is represented as (red, green, blue, alpha), each takes up 8 bits
                at=skia.kUnpremul_AlphaType,  # alpha (transparency) is not pre-multiplied
            )
        )

        # Initialize the browser's chrome
        self.chrome = Chrome(self)

    @property
    def active_tab(self) -> Tab:
        if self._active_tab is None:
            raise Exception("No active tab.")
        return self._active_tab

    def set_active_tab(self, tab: Tab) -> None:
        """Used by the Chrome when users select a tab."""
        self._active_tab = tab

    def new_tab(self, url: URL) -> None:
        """Create a new tab."""
        tab_height = HEIGHT - self.chrome.bottom
        tab = Tab(tab_height)
        self.tabs.append(tab)
        self._active_tab = tab
        tab.load(url)
        self.draw()

    def draw(self) -> None:
        # Get the canvas to draw to Skia root surface
        canvas = self.root_surface.getCanvas()

        # Clear the canvas before drawing new content
        canvas.clear(skia.ColorWHITE) # default to white background 

        # Draw the active tab's visible content
        self.active_tab.draw(canvas=canvas, offset=self.chrome.bottom)

        # Draw the chrome at the top of the window
        for draw_command in self.chrome.paint():
            draw_command.execute(scroll=0, canvas=canvas)

        # Get the sequence of bytes representing Skia surface
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()

        # Wrap Skia pixels into an SDL surface
        depth = 32
        pitch = 4 * WIDTH
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes,  # Pointer to raw RGBA pixel data
            WIDTH,  # surface's width in pixels
            HEIGHT,  # surface's height in pixels
            depth,  # bits per pixel
            pitch,  # bytes per row
            self.RED_MASK,  # bit mask for red channel
            self.GREEN_MASK,  # bit mask for green channel
            self.BLUE_MASK,  # bit mask for blue channel
            self.ALPHA_MASK,  # bit mask for alpha channel
        )

        # Copy pixel data from new SDL surface to window surface
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)

        # Update the window surface to reflect new pixels
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)

    def handle_down(self) -> None:
        self.active_tab.scroll_down()
        self.draw()

    def handle_up(self) -> None:
        self.active_tab.scroll_up()
        self.draw()

    def handle_click(self, x: int, y: int) -> None:
        if y < self.chrome.bottom:
            # Click on the chrome area
            self.focused_component = BrowserComponent.CHROME
            self.chrome.click(x, y)
        else:
            # Click on the tab content area
            self.focused_component = BrowserComponent.CONTENT
            self.chrome.blur()
            tab_y = y - self.chrome.bottom  # subtract the chrome size
            self.active_tab.click(x, tab_y)
        self.draw()

    def handle_key(self, char: str) -> None:
        if self.focused_component == BrowserComponent.CHROME:
            self.chrome.keypress(char)
            self.draw()
        elif self.focused_component == BrowserComponent.CONTENT:
            self.active_tab.keypress(char)
            self.draw()

    def handle_enter(self) -> None:
        self.chrome.enter()
        self.draw()

    def handle_backspace(self) -> None:
        if self.focused_component == BrowserComponent.CHROME:
            self.chrome.backspace()
            self.draw()
        elif self.focused_component == BrowserComponent.CONTENT:
            self.active_tab.backspace()
            self.draw()

    def handle_quit(self):
        """Clean up the window object."""
        sdl2.SDL_DestroyWindow(self.sdl_window)
