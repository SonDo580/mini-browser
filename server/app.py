import os

from server.utils import form_decode

# In-memory "database" of guestbook entries
ENTRIES = ["Pavel was here"]

# Parent path of static assets folder
STATIC_PARENT_DIR = os.path.dirname(__file__)


def handle_request(
    method: str, url_path: str, headers: dict[str, str], request_body: str | None
) -> tuple[str, str]:
    """Handle a single HTTP request. Return HTTP status and response body."""
    if method == "GET" and url_path == "/":
        return "200 OK", show_guestbook()

    if method == "POST" and url_path == "/add":
        params = form_decode(request_body or "")
        return "200 OK", add_entry(params)

    if method == "GET" and url_path.startswith("/static/"):
        return serve_static(url_path)

    return not_found(url_path, method)


def serve_static(url_path: str) -> tuple[str, str]:
    """Serve static assets. Return HTTP status and response body."""
    file_path = os.path.join(STATIC_PARENT_DIR, url_path.lstrip("/"))
    if not os.path.exists(file_path):
        return not_found(url_path, method="GET")

    with open(file=file_path, mode="r", encoding="utf8") as f:
        content = f.read()
    return "200 OK", content


def show_guestbook() -> str:
    """Display the guest book and a form to add new entries."""
    html = """
<!DOCTYPE html>
<head>
    <link rel="stylesheet" href="static/test.css">
    <script src="/static/test.js"></script>
</head>
"""

    # Display all entries
    for entry in ENTRIES:
        html += f"<p>{entry}</p>"

    # Form to add new guest
    html += """
<form action=add method=post>
    <p><input name=guest></p>
    <p><button>Sign the book!</button></p>
</form>
"""

    # Show warning when input value is too long
    html += """<strong></strong>"""

    return html


def add_entry(params: dict[str, str]) -> str:
    """Add new entry to guest book and return the updated page."""
    if "guest" in params and len(params["guest"]) <= 50:
        ENTRIES.append(params["guest"])
    return show_guestbook()


def not_found(url_path: str, method: str) -> tuple[str, str]:
    """Return Not-Found status and page."""
    html = f"""
<!DOCTYPE html>
<h1>{method} {url_path} not found!</h1>
"""
    return "404 Not Found", html
