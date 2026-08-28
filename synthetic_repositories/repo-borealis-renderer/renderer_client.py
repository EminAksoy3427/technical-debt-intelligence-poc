from urllib.request import urlopen


def render_document(renderer_endpoint: str, document: bytes) -> bytes:
    with urlopen(renderer_endpoint, data=document) as response:
        return response.read()
