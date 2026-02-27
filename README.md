# MassAffect

A simple, centralized VPS status and monitoring system

# Overview

MassAffect consists of a central, NodeJS-based **Controller** and a variable
number of Python **Agents**.

## Controller

Currently, the **Controller** is a very simple, single-file Express server that
waits for structured, HMAC-encrypted JSON data from *explicitly whitelisted*
**Agents** (VPSes) over HTTPS; both gzip-compressed and uncompressed JSON is
accepted.

Once validated, the data is stored in Redis "ring buffer" list (newest events
FIRST) using the following key structure:

```
ma:vps:{VPS_NAME}:{COLLECTOR_TYPE}:events
```

The `{COLLECTOR_TYPE}` namespace will depend on what **Agent/Collector** is
*producing* the incoming data.

### Controller (SSE View)

The **Controller** provides an SSE (Sever-Sent Events) viewing route that shows
ALL incoming JSON data from all approved sources. Only *whitelisted* IP address
are permitted.

**NOTE**: The current approach is to render on the server, and stream the final
HTML as SSE events. This keeps things simple and unifies UI logic; there's really
no need to have complicated JavaScript build the UI reactively in the browser. In
fact, this kind of "easy hydration" approach to dynamic content is making a
comeback lately!

### Controller (REST API)

**TODO**: Describe JSON routes and GET query params.

## Agent

The **Agent** is a modern, asyncio-heavy Python 3 daemon designed to integrate
with `systemd`. It is responsible for collecting, batching, encrypting and
finally transporting (with compression) the payloads that are sent to the
**Controller**.

### Agent (Transport)

**TODO**: Talk about how the `Transport` interface is pluggable, and describe
the current `HTTPTransport` and `DebugTransport` implementations.

### Agent (Dispatch)

**TODO**: Talk about how the default `Dispatch` is "fire-and-forget", and how
fugure implementations might introduce some kind of "retry" mechanism.

### Agent (Collectors)

Data payloads are gathered by *collectors*, all of which live in the `collector`
module. When launched, the **Agent** discovers and enumerates *collector*
objects; those that are marked `autoload = True` are always initialized and run.
*Collectors* that are **not** marked `autoload` will look for explicit
configuration variables in `config.py`.

**TODO**: More about collectors!

### Agent (Socket Server/IPC)

The **Agent** also creates an "abstract" unix socket called `massaffect` which
can be used to inject data into the system that can't be easily wrapped by a
*collector*. For example, the WordPress plugin can send its output directly to
this socket, totally removing the need for an intermediate log file and
unnecessary disk IO.

As with standard *collectors*, all incoming data is validated, batched and
compressed before being queued for dispatch to the **Controller**.

### Agent (Config)

For the time being, all configuration is managed with a simple `config.py`
(which is ignored by Git, since it will contain the HMAC "secret").

# TODO

- Add timestamp to HMAC verification to prevent replay attacks
- Experiment with adding additional id components to the "logs" namespace
