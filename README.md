# Outray

`outray` is a Python library for creating **HTTP, TCP, and UDP tunnels** using [https://outray.dev/](https://outray.dev/). It allows you to forward local services to a remote endpoint easily.  

Install via pip:

```bash
pip install outray
````

---

## Features

* HTTP tunnel proxy (`HttpListener`)
* TCP tunnel proxy (`TCPListener`)
* UDP tunnel proxy (`UDPListener`)
* Forward a tunnel asynchronously or synchronously
* Built-in error handling and logging

---

## Usage Example

- Asynchronous
```python
import asyncio
from outray import forward, http

async def main():
    listener = http("http://localhost:8080")
    await forward(listener)

asyncio.run(main())
```

- Synchronous
```python
import asyncio
from outray import forward, http

listener = http("http://localhost:8080")
forward_sync(listener)
```

---

## API

````markdown
## Environment Variables

Outray supports configuration via environment variables. These are optional but recommended.

### `OUTRAY_API_KEY`

Your API key used to authenticate tunnel connections.

```bash
export OUTRAY_API_KEY=your_api_key_here
````

If not provided explicitly, `forward` and `forward_sync` will automatically read this value from the environment.

Equivalent code usage:

```python
await forward(l1)
await forward(l1, api_key="API_KEY")
```

---

### `OUTRAY_API_URI`

The WebSocket endpoint used to establish tunnels.

```bash
export OUTRAY_API_URI=wss://api.outray.app
```

If not provided explicitly, this value is also read from the environment.

Equivalent code usage:

```python
await forward(l1, api_key="API_KEY", ws_url="API_URL")
```

---

### Creating a Listener

#### TCP

```python
from outray import tcp

listener = tcp(local_host="localhost", local_port=8090, remote_port=20710)
```

#### UDP

```python
from outray import udp

listener = udp(local_host="localhost", local_port=9000, remote_port=30710)
```

#### HTTP

```python
from outray import http

listener = http(url="http://localhost:8080", subdomain="my-subdomain")
```

---

### Forwarding a Tunnel

#### Asynchronous (`forward`)

```python
from outray import forward
import asyncio

asyncio.run(forward(listener))
```

* `forward(listener, ws_url=None, force_takeover=None, ping_interval=20, ping_timeout=20, api_key=None)`
* Forwards the listener to the remote WebSocket tunnel.
* Handles reconnects automatically.

#### Synchronous (`forward_sync`)

```python
from outray import forward_sync

forward_sync(listener)
```

* Same as `forward` but **runs in a blocking synchronous context**.
* Useful for scripts that do not use `asyncio` natively.

---

### Logging

`outray` uses the standard Python `logging` module. To see detailed tunnel events:

```python
import logging

logger = logging.getLogger("outray")
logger.setLevel(logging.DEBUG)
```

