import sys
import tkinter

from browser.browser import Browser
from browser.url import URL
from browser.constants import DEFAULT_LINK

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LINK
    url_manager = URL(url)
    browser = Browser()
    browser.new_tab(url_manager)
    tkinter.mainloop()
