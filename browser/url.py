from __future__ import annotations
import ssl
import socket


class URL:
    def __init__(self, url: str):
        # Example: "https://example.com:8080/blog/page.html"

        # Split scheme and the rest
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]
        # (ex) self.scheme = "https"
        # (ex) url = "example.com:8080/blog/page.html"

        # Separate host and path
        if "/" not in url:
            url = f"{url}/"

        self.host, url = url.split("/", 1)
        # (ex) self.host = "example.com:8080"
        # (ex) url = "blog/page.html"

        self.path = f"/{url}"
        # (ex) self.path = "/blog/page.html"

        # Default port
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
            # (ex) self.port = 443

        # Separate host and custom port
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
            # (ex) self.host = "example.com"
            # (ex) self.port = 8080

    def request(self, payload: str | None = None) -> str:
        """Send HTTP request and return response body"""

        # Establish TCP connection
        s = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))

        # Upgrade to TLS for HTTPS
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # Send HTTP request
        method = "POST" if payload is not None else "GET"
        lines: list[str] = [
            f"{method} {self.path} HTTP/1.0",
            f"Host: {self.host}",
        ]
        if payload is not None:
            content_length = len(payload.encode("utf8"))
            lines.append(f"Content-Length: {content_length}")
            lines.append("Content-Type: application/x-www-form-urlencoded")
        lines.append("")

        request = "\r\n".join(lines) + "\r\n"
        if payload is not None:
            request += payload

        s.send(request.encode("utf8"))

        # Parse response status line and headers
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # Reject chunked or compressed responses
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # Return response body and close connection
        content = response.read()
        s.close()
        return content

    def resolve(self, url: str) -> URL:
        """Resolve relative URL into full URL."""
        # Case 1: Absolute URL
        # (ex) "https://cdn.com/css/style.css" -> intact
        if "://" in url:
            return URL(url)

        # Case 2: Protocol-relative URL
        # (ex) "//cdn.com/css/main.css" -> "https://cdn.com/css/main.css"
        if url.startswith("//"):
            return URL(f"{self.scheme}:{url}")

        # Case 3: Relative path that doesn't start with "/"
        # (ex) self.path = "/blog/page.html"
        #      "style.css" -> "/blog/style.css" (after resolve)
        #      "../reset.css" -> "/reset.css" (after resolve)
        if not url.startswith("/"):
            # Get current directory
            dir, _ = self.path.rsplit("/", 1)

            # Step through "../" prefixes
            while url.startswith("../"):
                _, url = url.split("/", 1)  # Remove 1 "../"

                # Move up 1 directory level. Skip if already reached root.
                if "/" in dir:
                    dir, _ = dir.rsplit("/", 1)

            url = f"{dir}/{url}"

        # Case 4: Host-relative path (or resolved path from case 3)
        # (ex) "/base.css" -> "https://example.com:8080/base.css"
        return URL(f"{self.scheme}://{self.host}:{self.port}{url}")

    def __str__(self):
        # Hide port number if using default port
        port_part = f":{self.port}"
        if (
            self.scheme == "https"
            and self.port == 443
            or self.scheme == "http"
            and self.port == 80
        ):
            port_part = ""

        return f"{self.scheme}://{self.host}{port_part}{self.path}"
