from server.utils import form_decode

# In-memory "database" of guestbook entries
ENTRIES = ["Pavel was here"]


def handle_request(
    method: str, url_path: str, headers: dict[str, str], request_body: str | None
) -> tuple[str, str]:
    """Handle a single HTTP request. Return HTTP status and response body."""
    if method == "GET" and url_path == "/":
        return "200 OK", show_guestbook()

    if method == "POST" and url_path == "/add":
        params = form_decode(request_body or "")
        return "200 OK", add_entry(params)

    return "404 Not Found", not_found(url_path, method)


def show_guestbook() -> str:
    """Display the guest book and a form to add new entries."""
    html = "<!DOCTYPE html>"

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

    return html


def add_entry(params: dict[str, str]) -> str:
    """Add new entry to guest book and return the updated page."""
    if "guest" in params:
        ENTRIES.append(params["guest"])
    return show_guestbook()


def not_found(url_path: str, method: str) -> str:
    """Return Not-Found page."""
    return f"""
<!DOCTYPE html>
<h1>{method} {url_path} not found!</h1>
"""
