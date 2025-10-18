import urllib.parse


def form_decode(url_encoded_body: str) -> dict[str, str]:
    """Decode a URL-encoded form body."""
    params: dict[str, str] = {}

    for pair in url_encoded_body.split("&"):
        if "=" not in pair:
            continue
        name, value = pair.split("=", 1)
        name = urllib.parse.unquote_plus(name)
        value = urllib.parse.unquote_plus(value)
        params[name] = value

    return params
