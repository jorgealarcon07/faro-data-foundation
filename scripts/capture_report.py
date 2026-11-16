"""Render the actual offline reports, exercise controls, and save website-ready evidence."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--browser", type=Path, help="Optional installed Chromium-compatible executable"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = root / "assets/web"
    output.mkdir(parents=True, exist_ok=True)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, executable_path=str(args.browser) if args.browser else None
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        for namespace, label in [
            ("retail_uk_reference", "real"),
            ("retail_synthetic", "synthetic"),
        ]:
            source = root / "reports/latest" / namespace / "index.html"
            page.goto(source.as_uri())
            page.wait_for_selector("#bars .barrow")
            payload = json.loads((source.parent / "report.json").read_text())
            assert page.locator("#activity-table tbody tr").count() == len(payload["activity"])
            page.screenshot(path=str(output / f"{label}-activity.png"), full_page=True)
            page.select_option("#filter", "cancellation")
            assert page.locator("#activity-table tbody tr").count() == sum(
                r["record_class"] == "cancellation" for r in payload["activity"]
            )
            page.click("#tab-quality")
            assert page.locator("#quality").is_visible()
            assert not page.locator("#activity").is_visible()
            page.screenshot(path=str(output / f"{label}-quality.png"), full_page=True)
            checks.append(
                {
                    "namespace": namespace,
                    "activity_rows": len(payload["activity"]),
                    "class_filter": True,
                    "quality_tab": True,
                    "publication_run_id": payload["publication_run_id"],
                }
            )
        assert not errors, errors
        browser.close()
    result = {
        "browser": "Chromium / " + str(args.browser or "Playwright bundled"),
        "checks": checks,
        "page_errors": errors,
        "screenshots": 4,
    }
    (root / "reports/ui-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
