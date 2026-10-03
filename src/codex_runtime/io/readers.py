"""Bounded stdio client for the official Codex app-server account usage read."""

import asyncio
import json
import math
from contextlib import suppress
from dataclasses import dataclass
from typing import Protocol


class RateLimitProvider(Protocol):
    def read_rate_limits(self) -> object:
        """Return the account/rateLimits/read result or raise on provider failure."""


class ProviderError(Exception):
    """Transport/protocol failure; raw provider messages are intentionally omitted."""


@dataclass(frozen=True)
class AppServerProvider:
    """Use the installed Codex CLI's existing authenticated account.

    A check owns a short-lived subprocess and closes it on success or failure.
    Call from a synchronous worker (or asyncio.to_thread in async applications).
    Authentication setup and CLI installation belong to the consuming runtime.
    """

    executable: str = "codex"
    timeout_seconds: float = 15.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")

    def read_rate_limits(self) -> object:
        return asyncio.run(self._read())

    async def _read(self) -> object:
        process = None
        try:
            async with asyncio.timeout(self.timeout_seconds):
                process = await asyncio.create_subprocess_exec(
                    self.executable,
                    "app-server",
                    "--listen",
                    "stdio://",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    limit=65536,
                )
                if process.stdin is None or process.stdout is None:
                    raise ProviderError("missing_stdio")
                writer, reader = process.stdin, process.stdout
                await self._send(
                    writer,
                    {
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "clientInfo": {"name": "codex_runtime", "version": "0.1.0"}
                        },
                    },
                )
                await self._response(reader, 1)
                await self._send(writer, {"method": "initialized", "params": {}})
                await self._send(writer, {"id": 2, "method": "account/rateLimits/read"})
                return await self._response(reader, 2)
        except (OSError, TimeoutError, ValueError) as exc:
            raise ProviderError("provider_transport_error") from exc
        finally:
            if process is not None:
                if process.returncode is None:
                    with suppress(ProcessLookupError):
                        process.kill()
                # Drain bounded pipe buffers after killing, so wait cannot hang
                # when an oversized response has paused the stream transport.
                await process.communicate()

    @staticmethod
    async def _send(writer: asyncio.StreamWriter, message: dict[str, object]) -> None:
        writer.write((json.dumps(message) + "\n").encode())
        await writer.drain()

    @staticmethod
    async def _response(reader: asyncio.StreamReader, request_id: int) -> object:
        for _ in range(100):
            line = await reader.readline()
            if not line:
                raise ProviderError("provider_closed")
            response = json.loads(line)
            if not isinstance(response, dict):
                raise ProviderError("invalid_response")
            if "id" not in response:
                continue
            if type(response["id"]) is not int or response["id"] != request_id:
                raise ProviderError("unexpected_response")
            if "error" in response or "result" not in response:
                raise ProviderError("provider_rpc_error")
            return response["result"]
        raise ProviderError("too_many_notifications")
