CATALOG_CACHE: dict[str, str] = {}


def cache_catalog_entry(catalog_key: str, catalog_value: str) -> None:
    CATALOG_CACHE[catalog_key] = catalog_value


def get_catalog_entry(catalog_key: str) -> str | None:
    return CATALOG_CACHE.get(catalog_key)
