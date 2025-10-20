import socket
import io
from typing import Any

from server_test.app import handle_request
from server_test.utils import generate_token

# In-memory "database" of sessions
SESSIONS: dict[str, dict[str, Any]] = {}


def handle_connection(connection: socket.socket) -> None:
    """Handle an individual client connection."""
    request: io.BufferedReader = connection.makefile("b")

    # Parse HTTP request line
    request_line = request.readline().decode("utf8")
    method, url_path, version = request_line.split(" ", 2)
    assert method in ["GET", "POST"]

    # Parse request headers
    request_headers: dict[str, str] = {}
    while True:
        line = request.readline().decode("utf8")
        if line == "\r\n":
            break
        header, value = line.split(":", 1)
        request_headers[header.casefold()] = value.strip()

    # Extract token cookie, or generate a new one for new visitors
    if "cookie" in request_headers:
        # Simplification: assume that only token cookie exists
        token = request_headers["cookie"][len("token=") :]
    else:
        token = generate_token()

    # Read request body if present
    request_body: str | None = None
    if "content-length" in request_headers:
        content_length = int(request_headers["content-length"])
        request_body = request.read(content_length).decode("utf8")

    # Create or retrieve an existing session
    session = SESSIONS.setdefault(token, {})

    # Delegate to application logic to handle request
    print(f"{method} {url_path}")
    status, response_body = handle_request(
        session, method, url_path, request_headers, request_body
    )
    print(status)

    # Prepare HTTP response
    response_content_length = len(response_body.encode("utf8"))
    lines: list[str] = [
        f"HTTP/1.0 {status}",
        f"Content-Length: {response_content_length}",
    ]
    if "cookie" not in request_headers:
        # Set token cookie for new visitors
        lines.append(f"Set-Cookie: token={token}")
    lines.append("")
    response = "\r\n".join(lines) + "\r\n"
    response += response_body

    # Send response and close the connection
    connection.send(response.encode("utf8"))
    connection.close()
