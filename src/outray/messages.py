from dataclasses import dataclass
from typing import Optional, Union, Dict, List


@dataclass
class OpenTunnelMessage:
    subdomain: Optional[str] = None
    customDomain: Optional[str] = None
    apiKey: Optional[str] = None
    forceTakeover: Optional[bool] = None
    protocol: Optional[str] = None
    remotePort: Optional[int] = None
    type: str = "open_tunnel"

@dataclass
class TunnelResponseMessage:
    requestId: str
    statusCode: int
    headers: Dict[str, Union[str, List[str]]]
    body: Optional[str] = None
    type: str = "response"

@dataclass
class TunnelOpenedMessage:
    url: str
    protocol: Optional[str] = None
    port: Optional[int] = None
    type: str = "tunnel_opened"
    tunnelId: str = None

@dataclass
class TunnelDataMessage:
    requestId: str
    method: str
    path: str
    headers: Dict[str, Union[str, List[str]]]
    body: Optional[str] = None
    type: str = "request"


@dataclass
class TCPDataMessage:
    connectionId: str
    data: str  # base64 encoded
    type: str = "tcp_data"


@dataclass
class TCPCloseMessage:
    connectionId: str
    type: str = "tcp_close"

@dataclass
class TCPConnectionMessage:
    connectionId: str
    type: str = "tcp_connection"

@dataclass
class UDPResponseMessage:
    packetId: str
    targetAddress: str
    targetPort: int
    data: str  # base64 encoded
    type: str = "udp_response"

@dataclass
class UDPDataMessage:
    packetId: str
    sourceAddress: str
    sourcePort: int
    data: str  # base64 encoded
    type: str = "udp_data"

@dataclass
class ErrorMessage:
    code: str
    message: str
    type: str = "error"

