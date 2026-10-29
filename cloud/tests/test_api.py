import sys, pathlib, base64
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient
from app import db, main, packet
from app.agents.crew_brief import template

KEY = {"X-Unit-Key": main.INGEST_KEY}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "t.sqlite"))
    return TestClient(main.app)


def guide_json(**kw):
    d = dict(unit_id=1, grid_present=False, sos=True, battery_pct=255, temp_f=88.0,
             humidity=60, heat_index_f=95.5, heat_tier=2, hours_since_motion=6.5,
             hours_dark=14.0, uptime_s=500)
    d.update(kw)
    return d


def test_api_packet_json(client):
    assert client.post("/api/packet", json=guide_json()).status_code == 401
    r = client.post("/api/packet", json=guide_json(), headers=KEY)
    assert r.status_code == 200 and r.json()["stored"]
    h = client.get("/v1/homes").json()[0]
    assert h["sos"] and not h["grid_present"] and h["risk"] >= 90
    assert h["min_dark"] == 840 and h["min_since_motion"] == 390
    assert not h["battery_known"] and abs(h["heat_index_f"] - 95.5) < 0.2


def test_api_packet_out_of_range(client):
    assert client.post("/api/packet", json=guide_json(humidity=300), headers=KEY).status_code == 400


def _send(client, up, hi_c, seq):
    p = packet.Packet(1, 1, seq, packet.F_MED, 255, 30.0, 60, hi_c, 2, 0, 60, 1, up)
    r = client.post("/v1/ingest", headers=KEY, json={"p": base64.b64encode(packet.encode(p)).decode()})
    assert r.status_code == 200


def test_forecast_uses_device_clock_and_resets_on_reboot(client):
    for i, hi_f in enumerate([90, 92, 94, 96]):             # +2 F per device hour
        _send(client, 3600 * (i + 1), (hi_f - 32) * 5 / 9, i)
    assert client.get("/v1/homes").json()[0]["hours_to_unsafe"] == pytest.approx(3.5, abs=0.2)  # 0.1 C packet resolution
    _send(client, 10, (96 - 32) * 5 / 9, 0)                  # reboot: uptime restarts
    assert client.get("/v1/homes").json()[0]["hours_to_unsafe"] is None


def test_template_brief_cites_scorer(client):
    client.post("/api/packet", json=guide_json(), headers=KEY)
    text = template(client.get("/v1/homes").json(), reason="no key")
    assert "TEMPLATE BRIEF" in text and "Unit 1" in text and "SOS" in text


def test_sim_endpoint_reads_job_output_and_drops_trials(client, tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    assert client.get("/v1/sim").json() == {}
    (tmp_path / "sim_result.json").write_text(json.dumps(
        {"simulated": True, "trials": {"x": [1]}, "mean_weighted_person_hours": {"reduction_pct": 30}}))
    s = client.get("/v1/sim").json()
    assert s["sim_result"]["mean_weighted_person_hours"]["reduction_pct"] == 30
    assert "trials" not in s["sim_result"]


def test_checkin_without_model_is_503_not_a_guess(client, monkeypatch):
    from app.agents import client as llm
    monkeypatch.setattr(llm, "NANO", "")
    monkeypatch.setattr("app.agents.checkin_parser.NANO", "")
    r = client.post("/v1/checkin", json={"unit_id": 1, "text": "oxygen battery dies tonight"})
    assert r.status_code == 503


def test_triage_falls_back_per_home(client, monkeypatch):
    monkeypatch.setattr("app.agents.triage_fanout.NANO", "")
    client.post("/api/packet", json=guide_json(), headers=KEY)
    why = client.get("/v1/triage").json()["why"]
    assert why["1"].startswith("(no explanation")
    assert isinstance(client.get("/v1/usage").json(), dict)
