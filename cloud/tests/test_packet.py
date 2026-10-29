import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from app import packet
from app.packet import Packet, F_GRID, F_MED
from app.scorer import score
from app.forecast import hours_to_unsafe
from app.heat import heat_index_f, tier


def sample(**kw):
    base = dict(version=1, unit_id=7, seq=42, flags=F_MED, battery_pct=81,
                temp_c=32.4, humidity_pct=70, heat_index_c=41.2, heat_tier=3,
                min_since_motion=95, min_dark=310, occupants=2, uptime_s=123456)
    base.update(kw)
    return Packet(**base)


def test_size():
    assert packet.SIZE == 24


def test_roundtrip():
    p = sample()
    q = packet.decode(packet.encode(p))
    assert q == p and q.medical_load and not q.grid_present


def test_known_crc():
    assert packet.crc16_ccitt(b"123456789") == 0x29B1  # CCITT-FALSE check value


def test_bad_crc():
    raw = bytearray(packet.encode(sample()))
    raw[5] ^= F_GRID
    with pytest.raises(ValueError):
        packet.decode(bytes(raw))


def test_heat_index_reference():
    # NWS table: 96 F at 65% RH is about 121 F
    assert abs(heat_index_f(96, 65) - 121) < 2
    assert tier(121) == 3


def test_forecast_rising():
    s = [(i * 3600, 90 + 2 * i) for i in range(4)]  # +2 F/hr, now 96
    assert hours_to_unsafe(s) == pytest.approx(3.5, abs=0.1)


def test_sos_floor():
    h = dict(heat_index_f=82, hours_to_unsafe=None, min_dark=10, min_since_motion=0,
             medical_load=False, on_generator=False, occupants=1, sos=True)
    assert score(h)["risk"] >= 90


def test_battery_unknown_roundtrip():
    q = packet.decode(packet.encode(sample(battery_pct=packet.BATTERY_UNKNOWN)))
    assert q.battery_pct == 255
