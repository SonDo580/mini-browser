import os
from typing import Any
import html

from server_test.utils import form_decode, generate_token

# Note that the "authentication system" is very insecure.
# It's only intended for testing our browser.

# In-memory "database" of guestbook entries
ENTRIES: list[tuple[str, str]] = [("Zero was here", "zero")]

# (Hard-code) username/password pairs
LOGINS: dict[str, str] = {
    "x": "x",
    "zero": "zero",
}

# Parent path of static assets folder
STATIC_PARENT_DIR = os.path.dirname(__file__)


def handle_request(
    session: dict[str, Any],
    method: str,
    url_path: str,
    headers: dict[str, str],
    request_body: str | None,
) -> tuple[str, str]:
    """Handle a single HTTP request. Return HTTP status and response body."""
    if method == "GET" and url_path == "/login":
        return "200 OK", login_form()

    if method == "POST" and url_path == "/":
        params = form_decode(request_body or "")
        return do_login(session, params)

    if method == "GET" and url_path == "/":
        return "200 OK", show_guestbook(session)

    if method == "POST" and url_path == "/add":
        params = form_decode(request_body or "")
        add_entry(session, params)
        return "200 OK", show_guestbook(session)

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


def login_form() -> str:
    out = """
<!DOCTYPE html>
<form action=/ method=post>
    <p>Username: <input name=username></p>
    <p>Password: <input name=password type=password></p>
    <p><button>Log in</button></p>
</form>
""" 

    # Test transparency
    out += """
<div style="font-size: 50px; background-color: orange; color: #00000080; border-radius: 10px">
    Test
</div>
"""

    # Test opacity
    out += """
<div style="background-color:purple">
    Parent
    <div style="background-color:yellow;opacity:0.5">
        Child (50% opacity)
    </div>
    Parent
</div>
"""

    # Test blend mode
    out += """
<div style="background-color:orange">
    Parent
    <div style="background-color:blue;mix-blend-mode:difference">
        Child
    </div>
    Parent
</div>
"""

    # Test "overflow: clip"
    out += """
<div 
  style="border-radius:30px;background-color:lightblue;overflow:clip">
    This test text exists here to ensure that the "div" element is
    large enough that the border radius is obvious.
</div>
"""

    out += """<script src="/static/test1.js"></script>"""

    return out

def do_login(session: dict[str, Any], params: dict[str, str]) -> tuple[str, str]:
    """Handle login. Return status and response body."""
    username = params.get("username")
    password = params.get("password")
    if username in LOGINS and LOGINS[username] == password:
        session["user"] = username
        return "200 OK", show_guestbook(session)

    return (
        "401 Unauthorized",
        f"""
<!DOCTYPE html>
<h1>Invalid credentials</h1>
""",
    )


def show_guestbook(session: dict[str, Any]) -> str:
    """Display the guest book and a form to add new entries."""
    output = """
<!DOCTYPE html>
<head>
    <link rel="stylesheet" href="static/test.css">
</head>
"""

    # Ask user to login
    if "user" not in session:
        output += """<a href=/login>Sign in to write in the guest book</a>"""
        return output

    # Greeting
    output += f"""<h1>Hello, {session["user"]}</h1>"""

    # Form to add new guest (with a nonce to mitigate CSRF attacks)
    nonce = generate_token()
    session["nonce"] = nonce
    output += f"""
<form action=add method=post>
    <input name=nonce type=hidden value={nonce}>
    <p><input name=guest></p>
    <p><button>Sign the book!</button></p>
</form>
"""

    # Show warning when input value is too long
    output += """<strong></strong>"""

    # Display all entries
    for comment, person in ENTRIES:
        output += f"""<p>{html.escape(comment)}
<i>by {html.escape(person)}</i></p>"""
        
    output += """<script src="/static/test.js"></script>"""

    # Test Content Security Policy
    output += "<script src=https://example.com/evil.js></script>"

    return output


def add_entry(session: dict[str, Any], params: dict[str, str]) -> None:
    """Add new entry to guest book."""
    # Check if user is logged in
    if "user" not in session:
        return

    # Verify the nonce (mitigate CSRF attacks)
    if (
        "nonce" not in session
        or "nonce" not in params
        or session["nonce"] != params["nonce"]
    ):
        return

    if "guest" in params and len(params["guest"]) <= 50:
        ENTRIES.append((params["guest"], session["user"]))


def not_found(url_path: str, method: str) -> tuple[str, str]:
    """Return Not-Found status and page."""
    return (
        "404 Not Found",
        f"""
<!DOCTYPE html>
<h1>{method} {url_path} not found!</h1>
""",
    )
