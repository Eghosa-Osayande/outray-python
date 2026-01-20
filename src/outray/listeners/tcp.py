import asyncio
import base64
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional

from outray.exceptions import OutrayException

from .. import messages
from .. import helpers

logger = logging.getLogger(__name__)


@dataclass
class TCPListener:
    assigned_port: Optional[int] = None
    remote_port: Optional[int] = None
    local_port: int = 8090
    local_host: str = "127.0.0.1"
    recv_bufffer_size: int = 65535

    writers: dict[str, asyncio.StreamWriter] = field(default_factory=dict)

    def get_handshake_params(self) -> dict:
        return {
            "protocol": "tcp",
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
            logger.error("Tunnel opened without assigned TCP port")
            raise ValueError("No TCP port assigned by tunnel server")

        logger.info(
            "TCP tunnel ready: (%s %s) -> (%s %s)",
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
            "Tunnel error received (code=%s, message=%s)",
            msg.code,
            msg.message,
        )

        raise OutrayException(msg.code, msg.message)

    def on_tcp_connection(self, data: dict, **kw) -> None:
        try:
            msg: messages.TCPConnectionMessage = helpers.scan_into_dataclass(
                messages.TCPConnectionMessage, data
            )
        except Exception:
            logger.exception("Failed to parse TCPConnectionMessage: %s", data)
            return

        logger.info("Incoming TCP connection: %s", msg.connectionId)

        asyncio.create_task(self.read_background(msg.connectionId, **kw))

    async def read_background(self, connectionId: str, **kw) -> None:
        logger.debug(
            "Opening local TCP connection for connectionId=%s (%s:%s)",
            connectionId,
            self.local_host,
            self.local_port,
        )

        try:
            reader, writer = await asyncio.open_connection(
                self.local_host,
                self.local_port,
            )
        except Exception:
            logger.exception(
                "Failed to connect to local TCP service (%s:%s)",
                self.local_host,
                self.local_port,
            )
            return

        if connectionId in self.writers:
            logger.error(
                "Duplicate TCP connectionId detected: %s",
                connectionId,
            )
            writer.close()
            await writer.wait_closed()
            return

        self.writers[connectionId] = writer
        logger.debug("Local TCP connection established (%s)", connectionId)

        try:
            while True:
                data = await reader.read(self.recv_bufffer_size)
                if not data:
                    logger.debug(
                        "Local TCP connection closed (%s)",
                        connectionId,
                    )
                    break

                encoded = base64.b64encode(data).decode("utf-8")

                response = messages.TCPDataMessage(
                    connectionId=connectionId,
                    data=encoded,
                )

                await helpers.write_to_ws(
                    json.dumps(asdict(response)),
                    **kw,
                )

        except asyncio.CancelledError:
            logger.info(
                "TCP background task cancelled (%s)",
                connectionId,
            )
            raise

        except Exception:
            logger.exception(
                "Error while proxying TCP data (%s)",
                connectionId,
            )

        finally:
            logger.debug(
                "Cleaning up TCP connection (%s)",
                connectionId,
            )

            self.writers.pop(connectionId, None)

            if not writer.is_closing():
                writer.close()
            await writer.wait_closed()

            close_msg = messages.TCPCloseMessage(connectionId=connectionId)

            try:
                await helpers.write_to_ws(
                    json.dumps(asdict(close_msg)),
                    **kw,
                )
            except Exception:
                logger.exception(
                    "Failed to notify server of TCP close (%s)",
                    connectionId,
                )

    def on_tcp_data(self, data: dict, **kw) -> None:
        try:
            msg: messages.TCPDataMessage = helpers.scan_into_dataclass(
                messages.TCPDataMessage, data
            )
        except Exception:
            logger.exception("Failed to parse TCPDataMessage: %s", data)
            return

        writer = self.writers.get(msg.connectionId)
        if writer is None:
            logger.warning(
                "Received TCP data for unknown connectionId=%s",
                msg.connectionId,
            )
            return

        try:
            decoded_bytes = base64.b64decode(msg.data)
            writer.write(decoded_bytes)
        except Exception:
            logger.exception(
                "Failed to forward TCP data to local socket (%s)",
                msg.connectionId,
            )

    def on_tcp_close(self, data: dict, **kw) -> None:
        try:
            msg: messages.TCPCloseMessage = helpers.scan_into_dataclass(
                messages.TCPCloseMessage, data
            )
        except Exception:
            logger.exception("Failed to parse TCPCloseMessage: %s", data)
            return

        logger.info("Remote TCP close received (%s)", msg.connectionId)

        asyncio.create_task(self.close_writer(msg.connectionId))

    async def close_writer(self, connection_id: str) -> None:
        writer = self.writers.pop(connection_id, None)
        if writer is None:
            logger.debug(
                "close_writer called for unknown connectionId=%s",
                connection_id,
            )
            return

        if not writer.is_closing():
            writer.close()

        await writer.wait_closed()
        logger.debug("Local TCP writer closed (%s)", connection_id)
