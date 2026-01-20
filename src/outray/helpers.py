from dataclasses import dataclass, fields
import os
from typing import Optional
from urllib.parse import urlparse
from urllib.parse import urljoin
from typing import Optional


def get_api_uri() -> Optional[str]:
    api_url = "wss://api.outray.dev/"
    api_url_from_env = os.getenv("OUTRAY_API_URI")

    if api_url_from_env is not None:
        api_url = api_url_from_env

    return api_url


def get_api_key() -> Optional[str]:
    return os.getenv("OUTRAY_API_KEY")


def extract_subdomain(url: str) -> str | None:
    hostname = urlparse(url).hostname
    if not hostname:
        return None

    subdomain = hostname.split(".")[0]
    return subdomain or None


@dataclass
class HttpProxyResponse:
    status_code: int
    headers: Optional[map] = None
    body: str = ""


def build_full_url(proxy_uri: str, path: str) -> str:
    return urljoin(proxy_uri.rstrip("/") + "/", path.lstrip("/"))


def scan_into_dataclass(cls, kwargs: dict):
    user_fields = {f.name for f in fields(cls)}
    filtered_data = {k: v for k, v in kwargs.items() if k in user_fields}
    return cls(**filtered_data)


async def write_to_ws(data, **kw):
    send_fn = kw["send"]
    if send_fn is None:
        return  # TODO
    await send_fn(data)
