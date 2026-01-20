from .outray import http, tcp, udp, forward, forward_sync
from .listeners.http import HttpListener
from .listeners.udp import UDPListener
from .listeners.tcp import TCPListener
from dotenv import load_dotenv
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.hasHandlers():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

logger.propagate = False 


load_dotenv()