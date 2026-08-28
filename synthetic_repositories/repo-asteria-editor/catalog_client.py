from urllib.request import urlopen


CATALOG_ENDPOINT = "https://catalog.synthetic.invalid/v1/documents"


def fetch_catalog_document(document_id: str) -> bytes:
    with urlopen(f"{CATALOG_ENDPOINT}/{document_id}", timeout=5) as response:
        return response.read()
