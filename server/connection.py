import socket
import io

from server.app import handle_request


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

    # Read request body if present
    request_body: str | None = None
    if "content-length" in request_headers:
        content_length = int(request_headers["content-length"])
        request_body = request.read(content_length).decode("utf8")

    # Delegate to application logic to handle request
    status, response_body = handle_request(method, url_path, request_headers, request_body)

    # Prepare HTTP response
    response_content_length = len(response_body.encode("utf8"))
    lines: list[str] = [
        f"HTTP/1.0 {status}",
        f"Content-Length: {response_content_length}",
        "",
    ]
    response = "\r\n".join(lines) + "\r\n"
    response += response_body

    # Send response and close the connection
    connection.send(response.encode("utf8"))
    connection.close()
