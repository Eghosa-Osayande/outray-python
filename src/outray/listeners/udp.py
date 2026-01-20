import asyncio
import base64
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from outray.exceptions import OutrayException

from .. import messages
from .. import helpers

logger = logging.getLogger(__name__)


@dataclass
class UDPListener:
    local_port: int = 9000
    local_host: str = "127.0.0.1"
    remote_port: Optional[int] = None
    timeout: Optional[float] = None

    _transport: Optional[asyncio.DatagramTransport] = None
    assigned_port: Optional[int] = None

    def get_handshake_params(self) -> dict:
        return {
            "protocol": "udp",
            "remotePort": self.remote_port,
        }

    def on_tunnel_opened(self, data: dict, **kw) -> None:
        try:
            msg: messages.TunnelOpenedMessage = helpers.scan_into_dataclass(
                messages.TunnelOpenedMessage, data
            )
        except Exception:
            logger.exception("Failed to parse TunnelOpenedMessage: %s", data)
            raise

        self.assigned_port = msg.port

        if self.assigned_port is None:
            logger.error("UDP tunnel opened without assigned port")
            raise ValueError("No UDP port assigned by tunnel server")

        logger.info(
            "UDP tunnel ready: (%s %s) -> (%s %s)",
            msg.url,
            self.assigned_port,
             self.local_host,
            self.local_port,
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
            "UDP tunnel error received (code=%s, message=%s)",
            msg.code,
            msg.message,
        )
        raise OutrayException(msg.code, msg.message)

    def on_udp_data(self, data: dict, **kw) -> None:
        asyncio.create_task(self.process_udp_data(data, **kw))

    async def process_udp_data(self, data: dict, **kw) -> None:
        try:
            msg: messages.UDPDataMessage = helpers.scan_into_dataclass(
                messages.UDPDataMessage, data
            )
        except Exception:
            logger.exception("Failed to parse UDPDataMessage: %s", data)
            return

        try:
            decoded_bytes = base64.b64decode(msg.data)
        except Exception:
            logger.exception(
                "Failed to decode base64 UDP payload (packetId=%s)",
                msg.packetId,
            )
            return

        loop = asyncio.get_running_loop()
        response_future: asyncio.Future[bytes] = loop.create_future()

        class ClientProtocol(asyncio.DatagramProtocol):
            def datagram_received(self, data: bytes, addr):
                if not response_future.done():
                    response_future.set_result(data)

        try:
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: ClientProtocol(),
                local_addr=(self.local_host, self.local_port),
            )
        except Exception:
            logger.exception("Failed to create UDP endpoint")
            return

        try:
            transport.sendto(
                decoded_bytes,
                (self.local_host, self.local_port),
            )

            logger.debug(
                "Sent UDP packet to local service (%s:%s, packetId=%s)",
                self.local_host,
                self.local_port,
                msg.packetId,
            )

            try:
                result: Optional[bytes] = await asyncio.wait_for(
                    response_future,
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                logger.debug(
                    "UDP response timeout (packetId=%s)",
                    msg.packetId,
                )
                result = None
                return

            encoded_result: Optional[str] = (
                base64.b64encode(result).decode("utf-8") if result is not None else None
            )

            response = messages.UDPResponseMessage(
                packetId=msg.packetId,
                targetAddress=msg.sourceAddress,
                targetPort=msg.sourcePort,
                data=encoded_result,
            )

            await helpers.write_to_ws(
                json.dumps(asdict(response)),
                **kw,
            )

            logger.debug(
                "UDP response forwarded to tunnel (packetId=%s)",
                msg.packetId,
            )

        except Exception:
            logger.exception(
                "Error while processing UDP packet (packetId=%s)",
                msg.packetId,
            )

        finally:
            transport.close()
