from __future__ import annotations
import ssl
import socket


# Cookie jar:
# - Store cookie and cookie attributes of sites
# - Global, not limited to a particular tab
COOKIE_JAR: dict[str, tuple[str, dict[str, str]]] = {}


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

    def request(
        self, referrer: URL, payload: str | None = None
    ) -> tuple[dict[str, str], str]:
        """Send HTTP request. Return response headers and body"""

        # Establish TCP connection
        s = socket.socket(
            family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))

        # Upgrade to TLS for HTTPS
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # Prepare HTTP request
        method = "POST" if payload is not None else "GET"
        lines: list[str] = [
            f"{method} {self.path} HTTP/1.0",
            f"Host: {self.host}",
        ]

        if payload is not None:
            content_length = len(payload.encode("utf8"))
            lines.append(f"Content-Length: {content_length}")
            lines.append("Content-Type: application/x-www-form-urlencoded")

        if self.host in COOKIE_JAR:
            cookie, cookie_attributes = COOKIE_JAR[self.host]
            if self.__should_send_cookie(cookie_attributes, method, referrer):
                lines.append(f"Cookie: {cookie}")

        lines.append("")

        request = "\r\n".join(lines) + "\r\n"
        if payload is not None:
            request += payload

        # Send HTTP request
        s.send(request.encode("utf8"))

        # Parse response status line
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)

        # Parse response headers
        response_headers: dict[str, str] = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        # Reject chunked or compressed responses
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        # Store cookies
        if "set-cookie" in response_headers:
            cookie, cookie_attributes = self.__extract_cookie_and_attributes(
                response_headers["set-cookie"]
            )
            # Simplification: overwrite existing cookies instead of merging
            COOKIE_JAR[self.host] = (cookie, cookie_attributes)

        # Return response body and close connection
        content = response.read()
        s.close()
        return response_headers, content

    def __extract_cookie_and_attributes(
        self,
        set_cookie_header: str,
    ) -> tuple[str, dict[str, str]]:
        """Extract cookie and cookie attributes from Set-Cookie response header."""
        if ";" not in set_cookie_header:
            return set_cookie_header, {}

        cookie, attributes_part = set_cookie_header.split(";", 1)
        cookie_attributes: dict[str, str] = {}

        for attribute in attributes_part.split(";"):
            if "=" in attribute:
                key, value = attribute.split("=", 1)
            else:
                key, value = attribute, "true"
            cookie_attributes[key.strip().casefold()] = value.casefold()

        return cookie, cookie_attributes

    def __should_send_cookie(
        self, cookie_attributes: dict[str, str], method: str, referrer: URL
    ) -> bool:
        """Determine whether cookie should be sent with current request."""
        # Only send cookies with SameSite=Lax if:
        # - the method is GET (clicking a link).
        # - OR the new URL and the top-level URL have the same host.
        if cookie_attributes.get("samesite", "none") == "lax" and method != "GET":
            return self.host == referrer.host

        # Always send in other cases
        return True

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

    def origin(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"

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
