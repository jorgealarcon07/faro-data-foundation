"""Optional Windows dev runtime: verified Zonky packaging of PostgreSQL 17.12.

Use the official PostgreSQL/EDB installer for production. No system service is installed.
"""

import hashlib
import io
import json
import tarfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://repo.maven.apache.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-windows-amd64/17.12.0/embedded-postgres-binaries-windows-amd64-17.12.0.jar"
SHA = "bebadbe868ed53adb1c12033a381e41005915205ea9fedaa2349f5467fa7016b"
root = Path(__file__).resolve().parents[1]
target = root / ".runtime/postgres"
target.mkdir(parents=True, exist_ok=True)
with urllib.request.urlopen(URL, timeout=90) as response:
    data = response.read(40 * 1024 * 1024 + 1)
if len(data) > 40 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != SHA:
    raise SystemExit(
        "Runtime checksum mismatch; do not execute or replace the approved version silently"
    )
with zipfile.ZipFile(io.BytesIO(data)) as jar:
    with tarfile.open(fileobj=io.BytesIO(jar.read("postgres-windows-x86_64.txz"))) as archive:
        archive.extractall(target, filter="data")
(root / "reports").mkdir(exist_ok=True)
(root / "reports/runtime.json").write_text(
    json.dumps(
        {
            "version": "17.12",
            "distribution": "zonkyio/embedded-postgres-binaries",
            "url": URL,
            "sha256": SHA,
            "artifact_bytes": len(data),
            "system_service_installed": False,
        },
        indent=2,
    )
    + "\n"
)
print("Verified PostgreSQL binaries: " + str(target / "bin"))
