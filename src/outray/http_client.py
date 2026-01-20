import http.client
from urllib.parse import urlparse
from typing import Optional, Dict
from dataclasses import dataclass

@dataclass
class HttpProxyResponse:
    status_code: int
    headers: Dict[str, str]
    body: bytes

def proxy_http_request(
    uri: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
) -> HttpProxyResponse:

    headers = headers or {}
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    host = parsed.hostname
    port = parsed.port
    path = parsed.path or "/"
    if parsed.query:
        path += f"?{parsed.query}"

    if scheme == "https":
        port = port or 443
        conn = http.client.HTTPSConnection(host, port, timeout=10)
    else:
        port = port or 80
        conn = http.client.HTTPConnection(host, port, timeout=10)

    try:
        conn.request(method.upper(), path, headers=headers)
        res = conn.getresponse()
        body = res.read()
        response_headers = {k: v for k, v in res.getheaders()}
        return HttpProxyResponse(
            status_code=res.status,
            headers=response_headers,
            body=body,
        )
    finally:
        conn.close()
