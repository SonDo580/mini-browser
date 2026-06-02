import sys
import sdl2
import ctypes

from browser.browser import Browser
from browser.url import URL
from browser.constants import DEFAULT_LINK


def mainloop(browser: Browser):
    """Run the main SDL event loop."""
    event = sdl2.SDL_Event()

    while True:
        # Process user input events
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            # Close window
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()

            # Left mouse button released
            elif (
                event.type == sdl2.SDL_MOUSEBUTTONUP
                and event.button.button == sdl2.SDL_BUTTON_LEFT
            ):
                x, y = event.button.x, event.button.y
                browser.handle_click(x, y)

            # Key down
            elif event.type == sdl2.SDL_KEYDOWN:
                key = event.key.keysym.sym

                if key == sdl2.SDLK_RETURN:
                    browser.handle_enter()
                elif key == sdl2.SDLK_BACKSPACE:
                    browser.handle_backspace()
                elif key == sdl2.SDLK_DOWN:
                    browser.handle_down()
                elif key == sdl2.SDLK_UP:
                    browser.handle_up()

            # Text input (printable characters)
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode("utf8"))

        # Run 1 scheduled task
        browser.active_tab.task_runner.run()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python -m browser [url]")
        sys.exit(1)
    url = sys.argv[1] if len(sys.argv) == 2 else DEFAULT_LINK

    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)

    url_manager = URL(url)
    browser = Browser()
    browser.new_tab(url_manager)

    mainloop(browser)
