from enum import Enum
import sdl2
import skia
import math

from browser.constants import WIDTH, HEIGHT, VSTEP
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
            WIDTH,
            HEIGHT,
            sdl2.SDL_WINDOW_SHOWN,  # make the window visible
        )

        # Define masks that tell SDL which bits correspond to which color channel
        # - Each pixel uses 4 bytes for (R, G, B, A) channels.
        # - The byte order depends on the CPU’s endianness.
        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:  # Big-endian
            self.RED_MASK = 0xFF000000
            self.GREEN_MASK = 0x00FF0000
            self.BLUE_MASK = 0x0000FF00
            self.ALPHA_MASK = 0x000000FF
        else:  # Little-endian (most systems)
            self.RED_MASK = 0x000000FF
            self.GREEN_MASK = 0x0000FF00
            self.BLUE_MASK = 0x00FF0000
            self.ALPHA_MASK = 0xFF000000

        # Create Skia root surface
        # (A surface is a chunk of memory representing pixels on the screen.)
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH,
                HEIGHT,
                ct=skia.kRGBA_8888_ColorType,  # each pixel is represented as (red, green, blue, alpha), each takes up 8 bits
                at=skia.kUnpremul_AlphaType,  # alpha (transparency) is not pre-multiplied
            )
        )

        self.chrome = Chrome(self)
        self.chrome_surface: skia.Surface = skia.Surface(
            WIDTH,
            math.ceil(self.chrome.bottom),
        )
        self.tab_surface: skia.Surface | None = None

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

        self.raster_chrome()
        self.raster_tab()
        self.draw()

    def draw(self) -> None:
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        # Copy from visible portion of tab surface to root surface
        tab_rect = skia.Rect.MakeLTRB(
            l=0,
            t=self.chrome.bottom,
            r=WIDTH,
            b=HEIGHT,
        )
        canvas.save()  # save canvas state before transformations/clips
        canvas.clipRect(tab_rect)  # limit drawing to a rectangular region
        tab_offset = self.chrome.bottom - self.active_tab.scroll
        canvas.translate(0, tab_offset)  # shift the coordinate system
        self.tab_surface.draw(
            canvas, 0, 0
        )  # only pixels in visible portion are rendered
        canvas.restore()  # remove transformations/clips done to the canvas

        # Copy from chrome surface to root surface
        chrome_rect = skia.Rect.MakeLTRB(l=0, t=0, r=WIDTH, b=self.chrome.bottom)
        canvas.save()
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)
        canvas.restore()

        # Get the bytes representing Skia root surface
        skia_image = self.root_surface.makeImageSnapshot()
        skia_bytes = skia_image.tobytes()

        # Wrap Skia pixels into an SDL surface
        depth = 32  # bits per pixel
        pitch = 4 * WIDTH  # bytes per row
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(
            skia_bytes,
            WIDTH,
            HEIGHT,
            depth,
            pitch,
            self.RED_MASK,
            self.GREEN_MASK,
            self.BLUE_MASK,
            self.ALPHA_MASK,
        )

        # Copy pixel data to window surface
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)

        # Update window surface to reflect new pixels
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)

    def raster_tab(self) -> None:
        """Rasterize the whole active page to the tab surface."""
        tab_height = math.ceil(self.active_tab.document.height + 2 * VSTEP)

        # Create the surface if none exists or document height has changed
        if not self.tab_surface or tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        self.active_tab.raster(canvas)

    def raster_chrome(self) -> None:
        """Rasterize the browser chrome to the chrome surface."""
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for draw_command in self.chrome.paint():
            draw_command.execute(canvas)

    def handle_down(self) -> None:
        if self.active_tab.scroll_down():
            self.draw()

    def handle_up(self) -> None:
        if self.active_tab.scroll_up():
            self.draw()

    def handle_click(self, x: int, y: int) -> None:
        if y < self.chrome.bottom:
            # Click on the chrome area
            old_url = self.active_tab.url
            self.focused_component = BrowserComponent.CHROME
            self.chrome.click(x, y)

            self.raster_chrome()
            if self.active_tab.url != old_url:  # opened new tab
                self.raster_tab()
            self.draw()
        else:
            # Click on the tab content area
            self.focused_component = BrowserComponent.CONTENT
            chrome_blur_handled = self.chrome.blur()

            old_url = self.active_tab.url
            tab_y = y - self.chrome.bottom
            tab_clicked_handled = self.active_tab.click(x, tab_y)

            if chrome_blur_handled or self.active_tab.url != old_url:
                # unfocused a chrome component or clicked a link in content area
                self.raster_chrome()
            if tab_clicked_handled:
                self.raster_tab()
            self.draw()

    def handle_key(self, char: str) -> None:
        if self.focused_component == BrowserComponent.CHROME:
            if self.chrome.keypress(char):
                self.raster_chrome()
                self.draw()
        elif self.focused_component == BrowserComponent.CONTENT:
            if self.active_tab.keypress(char):
                self.raster_tab()
                self.draw()

    def handle_enter(self) -> None:
        if self.chrome.enter():
            self.raster_chrome()
            self.raster_tab()
            self.draw()

    def handle_backspace(self) -> None:
        if self.focused_component == BrowserComponent.CHROME:
            if self.chrome.backspace():
                self.raster_chrome()
                self.draw()
        elif self.focused_component == BrowserComponent.CONTENT:
            if self.active_tab.backspace():
                self.raster_tab()
                self.draw()

    def handle_quit(self):
        """Clean up the window object."""
        sdl2.SDL_DestroyWindow(self.sdl_window)
