import socket

from server.connection import handle_connection


if __name__ == "__main__":
    # Create a TCP streaming socket over IPv4
    s = socket.socket(
        family=socket.AF_INET, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )

    # Allow immediate port reuse after crash
    # (Normally, when a program using a socket crashes, the OS prevents the port from being reused for a short period)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Accept connections from anywhere on port 8000
    PORT = 8000
    s.bind(("", PORT))

    # Start listening for incoming connections
    s.listen()
    print(f"Server listening on port {PORT}")

    # Handle incoming connections
    while True:
        connection, address = s.accept()
        print(f"Accepted connection from {address}")
        handle_connection(connection)
