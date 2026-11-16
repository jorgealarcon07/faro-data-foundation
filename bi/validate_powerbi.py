"""Validate PBIR JSON against Microsoft's published schemas and check model bindings.

Schema validation is not evidence that Desktop opened/refreshed a model.
"""

import json
import urllib.request
from functools import lru_cache
from pathlib import Path

import jsonschema
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=100)
def load(uri):
    if not uri.startswith("https://developer.microsoft.com/json-schemas/"):
        raise ValueError("Only official Microsoft schemas are allowed")
    relative = uri.removeprefix("https://developer.microsoft.com/json-schemas/")
    url = "https://raw.githubusercontent.com/microsoft/json-schemas/main/" + relative
    with urllib.request.urlopen(url, timeout=30) as response:
        value = json.load(response)
    return {**value, "$id": uri}


def retrieve(uri):
    return Resource.from_contents(load(uri))


registry = Registry(retrieve=retrieve)
count = 0
for path in [
    ROOT / "Faro.pbip",
    ROOT / "Faro.Report/definition.pbir",
    *sorted((ROOT / "Faro.Report/definition").rglob("*.json")),
]:
    document = json.loads(path.read_text(encoding="utf-8"))
    uri = document["$schema"]
    schema = load(uri)
    validator = jsonschema.validators.validator_for(schema)(schema, registry=registry)
    validator.validate(document)
    count += 1
model = json.loads((ROOT / "Faro.SemanticModel/model.bim").read_text(encoding="utf-8"))["model"]
tables = {
    t["name"]: {
        "Column": {c["name"] for c in t["columns"]},
        "Measure": {m["name"] for m in t["measures"]},
    }
    for t in model["tables"]
}
for path in (ROOT / "Faro.Report/definition").rglob("visual.json"):
    visual = json.loads(path.read_text(encoding="utf-8"))["visual"]
    for role in visual["query"]["queryState"].values():
        for projection in role["projections"]:
            kind, value = next(iter(projection["field"].items()))
            assert value["Property"] in tables[value["Expression"]["SourceRef"]["Entity"]][kind]
result = {
    "json_files_validated": count,
    "bindings_valid": True,
    "schema_source": "microsoft/json-schemas",
    "desktop_opened": False,
    "desktop_refreshed": False,
}
(ROOT.parent / "reports/powerbi-validation.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
