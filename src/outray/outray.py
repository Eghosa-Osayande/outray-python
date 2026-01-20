import asyncio
import json
import logging
from typing import Optional, Union

import websockets

from outray.exceptions import OutrayException

from . import helpers
from .listeners import HttpListener, TCPListener, UDPListener

logger = logging.getLogger(__name__)


def http(
    url: str = "http://localhost:8080",
    subdomain: Optional[str] = None,
) -> HttpListener:
    return HttpListener(
        proxy_uri=url,
        subdomain=subdomain,
    )


def tcp(
    local_host: str = "localhost",
    local_port: int = 8080,
    remote_port: Optional[int] = None,
    recv_bufffer_size: int = 65535,
) -> TCPListener:
    return TCPListener(
        local_host=local_host,
        local_port=local_port,
        remote_port=remote_port,
        recv_bufffer_size=recv_bufffer_size,
    )


def udp(
    local_host: str = "localhost",
    local_port: int = 8080,
    remote_port: Optional[int] = None,
    timeout: float = 20,
) -> UDPListener:
    return UDPListener(
        local_host=local_host,
        local_port=local_port,
        remote_port=remote_port,
        timeout=timeout,
    )


async def forward(
    listener: Union[HttpListener, TCPListener, UDPListener],
    api_key: Optional[str] = None,
    ws_url: Optional[str] = None,
    force_takeover: Optional[bool] = None,
    ping_interval: int = 20,
    ping_timeout: int = 20,
) -> None:
    if ws_url is None:
        ws_url = helpers.get_api_uri()

    if api_key is None:
        api_key = helpers.get_api_key()

    logger.info(
        "Opening tunnel (listener=%s, ws_url=%s)",
        type(listener).__name__,
        ws_url,
    )

    async for ws in websockets.connect(
        ws_url,
        ping_interval=ping_interval,
        ping_timeout=ping_timeout,
    ):
        try:
            payload: dict = {
                "type": "open_tunnel",
                "apiKey": api_key,
                **listener.get_handshake_params(),
            }

            if force_takeover is not None:
                payload["forceTakeover"] = force_takeover

            await ws.send(json.dumps(payload))
            logger.debug("Handshake payload sent")

            async for message in ws:
                try:
                    data: dict = json.loads(message)
                except json.JSONDecodeError:
                    logger.error("Received invalid JSON from server: %s", message)
                    continue

                message_type = data.get("type")
                if not message_type:
                    logger.warning("Received message without type: %s", data)
                    continue

                handler_name = f"on_{message_type}"
                handler = getattr(listener, handler_name, None)

                if handler is None:
                    logger.error(
                        "%s has no handler for message type '%s'",
                        type(listener).__name__,
                        message_type,
                    )
                    logger.debug("Unhandled message payload: %s", data)
                    continue

                if not callable(handler):
                    logger.error(
                        "Handler %s exists but is not callable",
                        handler_name,
                    )
                    continue

                async def send(payload: str) -> None:
                    await ws.send(payload)

                handler(data, send=send)

        except websockets.ConnectionClosed as e:
            logger.warning(
                "WebSocket connection closed (%s). Reconnecting...",
                e,
            )

        except KeyboardInterrupt:
            logger.info("Tunnel closed by user")
            return

        except OutrayException as e:
            logger.exception(e.code)
            if e.should_end_session:
                return

        except Exception:
            logger.exception("Fatal error in tunnel forwarder")
            raise


def forward_sync(
    listener: Union[HttpListener, TCPListener, UDPListener],
    ws_url: Optional[str] = None,
    force_takeover: Optional[bool] = None,
    ping_interval: int = 20,
    ping_timeout: int = 20,
    api_key: Optional[str] = None,
) -> None:
    try:
        asyncio.run(
            forward(
                listener=listener,
                ws_url=ws_url,
                force_takeover=force_takeover,
                ping_interval=ping_interval,
                ping_timeout=ping_timeout,
                api_key=api_key,
            )
        )
    except:
        return
