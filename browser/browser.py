from enum import Enum
import sdl2
import skia
import math
import threading

from browser.constants import WIDTH, HEIGHT, REFRESH_RATE_SEC, SCROLL_STEP
from browser.url import URL
from browser.chrome import Chrome
from browser.tab import Tab, CommitData
from browser.tasks import Task
from browser.render.draw_commands import BaseDrawCommand


class BrowserComponent(Enum):
    CHROME = "chrome"
    CONTENT = "content"


class ScrollDirection(Enum):
    DOWN = 1
    UP = -1


class Browser:
    def __init__(self):
        self.chrome = Chrome(browser=self)

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

        # Skia root surface (a surface is a chunk of memory representing pixels on the screen)
        self.root_surface = skia.Surface.MakeRaster(
            skia.ImageInfo.Make(
                WIDTH,
                HEIGHT,
                ct=skia.kRGBA_8888_ColorType,  # each pixel is represented as (red, green, blue, alpha), each takes up 8 bits
                at=skia.kUnpremul_AlphaType,  # alpha (transparency) is not pre-multiplied
            )
        )

        self.chrome_surface: skia.Surface = skia.Surface(
            WIDTH,
            math.ceil(self.chrome.bottom),
        )
        self.tab_surface: skia.Surface | None = None

        self.tabs: list[Tab] = []
        self._active_tab: Tab | None = None
        self.active_tab_url: URL | None = None
        self.active_tab_scroll: float = 0
        self.active_tab_height: float = 0
        self.active_tab_display_list: list[BaseDrawCommand] = []

        self.focused_component: BrowserComponent | None = None

        self.needs_raster_and_draw: bool = False
        self.needs_animation_frame: bool = True

        self.animation_timer: threading.Timer | None = None

        threading.current_thread().name = "Browser thread"
        self.lock = threading.Lock()

    def commit(self, tab: Tab, data: CommitData):
        """
        For the main thread to communicate with browser thread
        after rendering, which synchronizes the 2 threads.
        """
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            self.active_tab_url = data.url
            if data.scroll is not None:  # sync if scroll offset changed by main thread
                self.active_tab_scroll = data.scroll
            self.active_tab_height = data.height
            self.active_tab_display_list = data.display_list
            self.animation_timer = None  # allow scheduling the next rendering task
            self.set_needs_raster_and_draw()
        self.lock.release()

    @property
    def active_tab(self) -> Tab:
        if not self._active_tab:
            raise Exception("No active tab.")
        return self._active_tab

    def set_active_tab(self, tab: Tab) -> None:
        self._active_tab = tab

        # TODO: cache UI state to use when switching to loaded tab?
        self.active_tab_scroll = 0
        self.active_tab_url = None
        self.active_tab_height = 0
        self.active_tab_display_list = []
        self.tab_surface = None

    def new_tab(self, url: URL):
        """Create a new tab (acquire lock)."""
        self.lock.acquire(blocking=True)
        self.new_tab_internal(url)
        self.lock.release()

    def new_tab_internal(self, url: URL):
        """Create a new tab (don't acquire lock)."""
        tab = Tab(browser=self, tab_height=HEIGHT - self.chrome.bottom)
        self.tabs.append(tab)
        self.set_active_tab(tab)
        self.schedule_load(url)

    def schedule_load(self, url: URL):
        """Schedule loading active tab."""
        self.active_tab.task_runner.clear_pending_tasks()
        task = Task(self.active_tab.load, url)
        self.active_tab.task_runner.schedule_task(task)

    def set_needs_animation_frame(self, tab: Tab) -> None:
        """Only set the dirty flag if called from active tab."""
        self.lock.acquire(blocking=True)
        if tab == self.active_tab:
            self.needs_animation_frame = True
        self.lock.release()

    def schedule_animation_frame(self) -> None:
        def callback():
            self.lock.acquire(blocking=True)
            scroll = self.active_tab_scroll
            self.needs_animation_frame = False
            self.lock.release()
            task = Task(self.active_tab.run_animation_frame, scroll)
            self.active_tab.task_runner.schedule_task(task)

        self.lock.acquire(blocking=True)
        if self.needs_animation_frame and not self.animation_timer:
            self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()
        self.lock.release()

    def set_needs_raster_and_draw(self):
        self.needs_raster_and_draw = True

    def raster_and_draw(self):
        self.lock.acquire(blocking=True)
        if not self.needs_raster_and_draw:
            self.lock.release()
            return

        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.needs_raster_and_draw = False
        self.lock.release()

    def raster_tab(self) -> None:
        """Rasterize the whole active page to the tab surface."""
        if not self.active_tab_height:
            return

        # Create the surface if none exists or document height has changed
        if not self.tab_surface or self.active_tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, math.ceil(self.active_tab_height))

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for draw_command in self.active_tab_display_list:
            draw_command.execute(canvas)

    def raster_chrome(self) -> None:
        """Rasterize the browser chrome to the chrome surface."""
        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        for draw_command in self.chrome.paint():
            draw_command.execute(canvas)

    def draw(self) -> None:
        """Composite chrome surface and tab surface onto Skia root surface,
        flush to SDL window surface and update it to reflect new pixels."""
        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        # Copy from visible portion of tab surface to root surface
        if self.tab_surface:
            tab_rect = skia.Rect.MakeLTRB(
                l=0,
                t=self.chrome.bottom,
                r=WIDTH,
                b=HEIGHT,
            )
            canvas.save()  # save canvas state before transformations/clips
            canvas.clipRect(tab_rect)  # limit drawing to a rectangular region
            tab_offset = self.chrome.bottom - self.active_tab_scroll
            canvas.translate(0, tab_offset)  # shift the coordinate system
            self.tab_surface.draw(canvas, 0, 0)  # only copy pixels in visible portion
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

    def clamp_scroll(self, scroll: float) -> float:
        """Restrict scroll offset between 0 and max_scroll."""
        height = self.active_tab_height
        max_scroll = height - (HEIGHT - self.chrome.bottom)
        return max(0, min(scroll, max_scroll))

    def handle_down(self):
        self.__handle_scroll(ScrollDirection.DOWN)

    def handle_up(self):
        self.__handle_scroll(ScrollDirection.UP)

    def __handle_scroll(self, direction: ScrollDirection):
        self.lock.acquire(blocking=True)
        if not self.active_tab_height:
            self.lock.release()
            return

        self.active_tab_scroll = self.clamp_scroll(
            self.active_tab_scroll + SCROLL_STEP * direction.value
        )
        self.set_needs_raster_and_draw()  # to redraw with new scroll offset
        self.needs_animation_frame = (
            True  # so main thread can receive the scroll offset asynchronously
        )
        self.lock.release()

    def handle_click(self, x: int, y: int) -> None:
        self.lock.acquire(blocking=True)
        if y < self.chrome.bottom:
            # Click on the chrome area
            self.focused_component = BrowserComponent.CHROME
            if self.chrome.click(x, y):
                self.set_needs_raster_and_draw()
        else:
            # Click on the tab content area
            self.focused_component = BrowserComponent.CONTENT
            if self.chrome.blur():
                self.set_needs_raster_and_draw()
            tab_y = y - self.chrome.bottom
            task = Task(self.active_tab.click, x, tab_y)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_key(self, char: str) -> None:
        self.lock.acquire(blocking=True)
        if self.focused_component == BrowserComponent.CHROME:
            if self.chrome.keypress(char):
                self.set_needs_raster_and_draw()
        elif self.focused_component == BrowserComponent.CONTENT:
            task = Task(self.active_tab.keypress, char)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_enter(self) -> None:
        self.lock.acquire(blocking=True)
        if self.focused_component == BrowserComponent.CHROME:
            if self.chrome.enter():
                self.set_needs_raster_and_draw()
        self.lock.release()

    def handle_backspace(self) -> None:
        self.lock.acquire(blocking=True)
        if self.focused_component == BrowserComponent.CHROME:
            if self.chrome.backspace():
                self.set_needs_raster_and_draw()
        elif self.focused_component == BrowserComponent.CONTENT:
            task = Task(self.active_tab.backspace)
            self.active_tab.task_runner.schedule_task(task)
        self.lock.release()

    def handle_quit(self):
        """Ask main threads to quit and clean up the window object."""
        for tab in self.tabs:
            tab.task_runner.set_needs_quit()
        sdl2.SDL_DestroyWindow(self.sdl_window)
