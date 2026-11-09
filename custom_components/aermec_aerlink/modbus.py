"""Minimal, tolerant Modbus TCP client for the Aermec AerLink gateway.

The AerLink firmware writes a wrong ``length`` in the MBAP header of its
responses (real length + 12). Standard clients such as pymodbus wait for
bytes that never arrive and time out. This client ignores the declared
length and parses the response from the PDU itself.

Requests are serialized (one at a time) because the gateway is small and
often sits on a weak Wi-Fi link.
"""
from __future__ import annotations

import asyncio
import struct

TIMEOUT = 5.0
GAP = 0.05


class AerLinkError(Exception):
    """Communication error with the AerLink."""


class AerLinkClient:
    """Async Modbus TCP client tailored to the AerLink."""

    def __init__(self, host: str, port: int = 502, unit: int = 1) -> None:
        self.host, self.port, self.unit = host, port, unit
        self._lock = asyncio.Lock()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._tid = 0

    async def close(self) -> None:
        if self._writer:
            self._writer.close()
        self._reader = self._writer = None

    async def _read_pdu(self) -> bytes:
        r = self._reader
        assert r is not None
        head = await r.readexactly(7)
        fc = (await r.readexactly(1))[0]
        if fc & 0x80:
            code = (await r.readexactly(1))[0]
            raise AerLinkError(f"Modbus exception {code} (function {fc & 0x7F})")
        if fc in (1, 2, 3, 4):
            n = await r.readexactly(1)
            body = n + await r.readexactly(n[0])
        elif fc in (5, 6, 15, 16):
            body = await r.readexactly(4)
        else:
            raise AerLinkError(f"Unexpected function code {fc}")
        if struct.unpack(">H", head[:2])[0] != self._tid:
            raise AerLinkError("Transaction id mismatch")
        return bytes([fc]) + body

    async def _request(self, pdu: bytes) -> bytes:
        async with self._lock:
            last: Exception | None = None
            for _ in range(2):
                try:
                    if self._writer is None:
                        self._reader, self._writer = await asyncio.wait_for(
                            asyncio.open_connection(self.host, self.port), TIMEOUT
                        )
                    self._tid = (self._tid + 1) & 0xFFFF
                    self._writer.write(
                        struct.pack(">HHHB", self._tid, 0, len(pdu) + 1, self.unit) + pdu
                    )
                    await self._writer.drain()
                    resp = await asyncio.wait_for(self._read_pdu(), TIMEOUT)
                    await asyncio.sleep(GAP)
                    return resp
                except AerLinkError:
                    raise
                except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
                    last = err
                    await self.close()
            raise AerLinkError(f"AerLink not responding: {last!r}")

    async def read_holding(self, addr: int, count: int) -> list[int]:
        resp = await self._request(struct.pack(">BHH", 3, addr, count))
        return list(struct.unpack(f">{count}h", resp[2 : 2 + 2 * count]))

    async def read_coils(self, addr: int, count: int) -> list[bool]:
        resp = await self._request(struct.pack(">BHH", 1, addr, count))
        data = resp[2:]
        return [bool(data[i // 8] >> (i % 8) & 1) for i in range(count)]

    async def write_register(self, addr: int, value: int) -> None:
        await self._request(struct.pack(">BHH", 6, addr, value & 0xFFFF))

    async def write_coil(self, addr: int, on: bool) -> None:
        await self._request(struct.pack(">BHH", 5, addr, 0xFF00 if on else 0))
