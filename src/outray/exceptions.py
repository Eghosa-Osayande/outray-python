TERMINATING_CODES = {
    "SUBDOMAIN_IN_USE",
    "LIMIT_EXCEEDED",
    "AUTH_FAILED",
    "AUTH_REQUIRED",
    "TCP_TUNNEL_FAILED",
    "UDP_TUNNEL_FAILED",
    "DOMAIN_NOT_VERIFIED",
    "DOMAIN_IN_USE",
    "SUBDOMAIN_DENIED",
    "TUNNEL_UNAVAILABLE",
}


def should_terminate(code: str) -> bool:
    return code in TERMINATING_CODES


class OutrayException(Exception):
    code: str
    should_end_session: bool
    message: str

    def __init__(self, code: str, message: str):
        self.code = code
        self.should_end_session = should_terminate(code)
        self.message = message
