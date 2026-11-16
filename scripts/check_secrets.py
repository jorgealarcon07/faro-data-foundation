"""Focused tracked-file scan; does not read ignored .env or raw data."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
patterns = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"postgres(?:ql)?://[^\s:]+:[^\s@]+@"),
]
issues = []
for name in files:
    p = root / name
    if p.suffix in {".png", ".parquet", ".xlsx"} or not p.is_file():
        continue
    content = p.read_text(encoding="utf-8", errors="replace")
    if any(pattern.search(content) for pattern in patterns):
        issues.append(name)
    if name == ".env" or name.startswith((".runtime/", ".venv/")):
        issues.append(name)
if issues:
    raise SystemExit("Potential secret files: " + ", ".join(issues))
print(
    f"Focused secret scan passed ({len(files)} tracked files); no guarantee against all credential formats"
)
