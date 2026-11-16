import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
actual = {
    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted((root / "contracts/v1").glob("*.json"))
}
lock = json.loads((root / "contracts.lock.json").read_text())
if lock != {"version": "1.0.0", "sha256": actual}:
    raise SystemExit("Contract drift: review version, fixtures and update contracts.lock.json")
print("Contract hashes verified")
