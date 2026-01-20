import asyncio
import base64
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from outray.exceptions import OutrayException
from outray.http_client import proxy_http_request

from .. import messages
from .. import helpers

logger = logging.getLogger(__name__)


@dataclass
class HttpListener:
    subdomain: Optional[str] = None
    custom_domain: Optional[str] = None
    proxy_uri: Optional[str] = None

    _assigned_url: Optional[str] = None
    _derived_subdomain: Optional[str] = None

    def get_handshake_params(self) -> dict:
        params = {
            "subdomain": self.subdomain,
            "customDomain": self.custom_domain,
        }

        if self._derived_subdomain is not None:
            params["subdomain"] = self._derived_subdomain

        return params

    def on_tunnel_opened(self, data: dict, **kw) -> None:
        try:
            msg: messages.TunnelOpenedMessage = helpers.scan_into_dataclass(
                messages.TunnelOpenedMessage, data
            )
        except Exception as exc:
            logger.exception("Failed to parse TunnelOpenedMessage: %s", data)
            raise

        self._assigned_url = msg.url
        self._derived_subdomain = helpers.extract_subdomain(msg.url)

        if self._derived_subdomain is None:
            logger.error(
                "Tunnel opened but failed to derive subdomain from URL: %s",
                msg.url,
            )
            raise ValueError(f"Invalid tunnel URL returned by server: {msg.url}")

        logger.info("HTTP tunnel ready: %s -> %s", self._assigned_url, self.proxy_uri)

    def on_request(self, data: dict, **kw) -> None:
        if self.proxy_uri is None:
            logger.error("Received request but proxy_uri is not configured")
            return

        try:
            msg: messages.TunnelDataMessage = helpers.scan_into_dataclass(
                messages.TunnelDataMessage, data
            )
        except Exception:
            logger.exception("Failed to parse TunnelDataMessage: %s", data)
            return

        try:
            full_proxy_uri = helpers.build_full_url(self.proxy_uri, msg.path)
        except Exception:
            logger.exception(
                "Failed to build proxy URL (base=%s, path=%s)",
                self.proxy_uri,
                msg.path,
            )
            return

        logger.debug(
            "Proxying HTTP request %s %s (requestId=%s)",
            msg.method,
            full_proxy_uri,
            msg.requestId,
        )

        try:
            proxy_response = proxy_http_request(
                full_proxy_uri,
                msg.method,
                msg.headers,
            )
        except Exception:
            logger.exception(
                "Upstream proxy request failed (%s %s)",
                msg.method,
                full_proxy_uri,
            )
            return

        response = messages.TunnelResponseMessage(
            body=base64.b64encode(proxy_response.body).decode("utf-8"),
            headers=proxy_response.headers,
            statusCode=proxy_response.status_code,
            requestId=msg.requestId,
        )

        try:
            asyncio.create_task(helpers.write_to_ws(json.dumps(asdict(response)), **kw))
        except Exception:
            logger.exception(
                "Failed to dispatch response for requestId=%s",
                msg.requestId,
            )

    def on_error(self, data: dict, **kw) -> None:
        try:
            msg: messages.ErrorMessage = helpers.scan_into_dataclass(
                messages.ErrorMessage, data
            )
        except Exception:
            logger.exception("Failed to parse ErrorMessage: %s", data)
            return

        logger.error(
            "Tunnel error received (code=%s, message=%s)",
            msg.code,
            msg.message,
        )

        raise OutrayException(msg.code, msg.message)
