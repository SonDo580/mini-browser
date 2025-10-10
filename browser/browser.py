import tkinter

from browser.constants import WIDTH, HEIGHT
from browser.url import URL
from browser.chrome import Chrome
from browser.tab import Tab


class Browser:
    def __init__(self):
        self.tabs: list[Tab] = []
        self._active_tab: Tab | None = None

        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, width=WIDTH, height=HEIGHT, bg="white"
        )
        self.canvas.pack()

        self.window.bind("<Down>", self.handle_down)  # press down key
        self.window.bind("<Up>", self.handle_up)  # press up key
        self.window.bind("<Button-1>", self.handle_click)  # press left mouse button

        # Init Chrome after creating Tk window since it needs to call get_font.
        # tkinter.font.Font() requires a default Tk root window to exist.
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

    def handle_down(self, e: tkinter.Event) -> None:
        self.active_tab.scroll_down()
        self.draw()

    def handle_up(self, e: tkinter.Event) -> None:
        self.active_tab.scroll_up()
        self.draw()

    def handle_click(self, e: tkinter.Event) -> None:
        if e.y < self.chrome.bottom:
            # Click on the chrome area
            self.chrome.click(e.x, e.y)
        else:
            # Click on the tab content area
            tab_y = e.y - self.chrome.bottom  # subtract the chrome size
            self.active_tab.click(e.x, tab_y)
        self.draw()

    def draw(self) -> None:
        self.canvas.delete("all")

        # Draw the active tab's visible content
        self.active_tab.draw(canvas=self.canvas, offset=self.chrome.bottom)

        # Draw the chrome at the top of the window
        for draw_command in self.chrome.paint():
            draw_command.execute(scroll=0, canvas=self.canvas)
