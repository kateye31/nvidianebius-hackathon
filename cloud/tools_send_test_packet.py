"""Send one packet to the local API without hardware. Labeled as a test unit."""
import base64, os, sys, pathlib, httpx
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from app.packet import Packet, encode, F_MED

p = Packet(1, 9001, 1, F_MED, 77, 32.0, 72, 40.5, 3, 200, 420, 2, 9999)
r = httpx.post(os.environ.get("API", "http://localhost:8000") + "/v1/ingest",
               json={"p": base64.b64encode(encode(p)).decode(), "lat": 26.6, "lon": -82.1,
                     "synthetic": True},
               headers={"X-Unit-Key": os.environ.get("INGEST_KEY", "change-me")})
print(r.status_code, r.json())
