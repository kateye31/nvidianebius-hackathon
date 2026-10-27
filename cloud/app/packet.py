"""Packet contract v1. Must match docs/PACKET.md and firmware packet.h."""
from __future__ import annotations
import struct
from dataclasses import dataclass, asdict

FMT = "<BHHBBhBhBHHBIH"
SIZE = struct.calcsize(FMT)  # 24
assert SIZE == 24

F_GRID, F_SOS, F_GEN, F_SHED, F_MED = 1, 2, 4, 8, 16


def crc16_ccitt(data: bytes, crc: int = 0xFFFF) -> int:
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


@dataclass
class Packet:
    version: int
    unit_id: int
    seq: int
    flags: int
    battery_pct: int
    temp_c: float
    humidity_pct: int
    heat_index_c: float
    heat_tier: int
    min_since_motion: int
    min_dark: int
    occupants: int
    uptime_s: int

    @property
    def grid_present(self) -> bool: return bool(self.flags & F_GRID)
    @property
    def sos(self) -> bool: return bool(self.flags & F_SOS)
    @property
    def on_generator(self) -> bool: return bool(self.flags & F_GEN)
    @property
    def ac_shed(self) -> bool: return bool(self.flags & F_SHED)
    @property
    def medical_load(self) -> bool: return bool(self.flags & F_MED)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(grid_present=self.grid_present, sos=self.sos,
                 on_generator=self.on_generator, ac_shed=self.ac_shed,
                 medical_load=self.medical_load)
        return d


def encode(p: Packet) -> bytes:
    body = struct.pack(FMT[:-1], p.version, p.unit_id, p.seq, p.flags,
                       p.battery_pct, round(p.temp_c * 10), p.humidity_pct,
                       round(p.heat_index_c * 10), p.heat_tier,
                       p.min_since_motion, p.min_dark, p.occupants, p.uptime_s)
    return body + struct.pack("<H", crc16_ccitt(body))


def decode(raw: bytes) -> Packet:
    if len(raw) != SIZE:
        raise ValueError(f"packet must be {SIZE} bytes, got {len(raw)}")
    f = struct.unpack(FMT, raw)
    if crc16_ccitt(raw[:-2]) != f[-1]:
        raise ValueError("bad crc")
    if f[0] != 1:
        raise ValueError(f"unknown version {f[0]}")
    return Packet(f[0], f[1], f[2], f[3], f[4], f[5] / 10, f[6], f[7] / 10,
                  f[8], f[9], f[10], f[11], f[12])
