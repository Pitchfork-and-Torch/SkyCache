"""Content license inventory for operator compliance."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from skycache.db.catalog import Catalog

# Licenses we treat as generally OK for community redistribution *when operator confirms terms*
KNOWN_OPEN = frozenset(
    {
        "cc0",
        "cc0-1.0",
        "cc-by",
        "cc-by-4.0",
        "cc-by-sa",
        "cc-by-sa-4.0",
        "public-domain",
        "public_domain",
        "operator_supplied",
        "kiwix",
        "moh-open",
        "unknown",  # flagged, not blocked
    }
)


class LicenseInventory:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def report(self) -> dict[str, Any]:
        packages = self.catalog.list_packages(limit=10_000)
        by_license: Counter[str] = Counter()
        items: list[dict[str, str]] = []
        unknown = 0
        for rec in packages:
            p = rec.package
            lic = (p.license or "unknown").strip()
            by_license[lic] += 1
            if lic.lower() in {"unknown", ""}:
                unknown += 1
            items.append(
                {
                    "id": p.id,
                    "license": lic,
                    "priority_class": p.priority_class.value,
                    "title": p.title_for("en"),
                    "source_type": p.source.type,
                }
            )
        return {
            "package_count": len(packages),
            "by_license": dict(by_license.most_common()),
            "unknown_or_blank": unknown,
            "items": items,
            "operator_duty": (
                "Keep this inventory current. Confirm redistribution rights for every pack. "
                "Kiwix/ZIM and MoH materials have their own terms."
            ),
            "legal": (
                "SkyCache only serves open/FTA/operator-authored content. "
                "No commercial decrypt. Receive-only satellite."
            ),
        }

    def report_html(self, *, node_id: str = "", version: str = "") -> str:
        """Printable HTML inventory for regulators/partners (browser -> PDF).

        Avoids heavy PDF libraries on Pi-class hardware.
        """
        rep = self.report()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        rows = []
        for it in rep.get("items") or []:
            rows.append(
                "<tr>"
                f"<td>{_esc(it.get('id'))}</td>"
                f"<td>{_esc(it.get('title'))}</td>"
                f"<td>{_esc(it.get('license'))}</td>"
                f"<td>{_esc(it.get('priority_class'))}</td>"
                f"<td>{_esc(it.get('source_type'))}</td>"
                "</tr>"
            )
        body = "\n".join(rows) or "<tr><td colspan='5'>No packages.</td></tr>"
        by_lic = rep.get("by_license") or {}
        summary = ", ".join(f"{_esc(k)}={v}" for k, v in by_lic.items()) or " - "
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>SkyCache license inventory</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 1rem 1.25rem; color: #0f172a; }}
  h1 {{ font-size: 1.25rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.85rem; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 0.35rem 0.5rem; text-align: left; }}
  th {{ background: #f1f5f9; }}
  .meta {{ color: #475569; font-size: 0.9rem; }}
  @media print {{ .noprint {{ display: none; }} }}
</style>
</head>
<body>
  <p class="noprint"><button onclick="window.print()">Print / Save as PDF</button></p>
  <h1>SkyCache license passport inventory</h1>
  <p class="meta">Node {_esc(node_id or "(unset)")}
     {_esc(f"  |  v{version}" if version else "")}  |  {now}</p>
  <p><strong>{rep.get("package_count", 0)}</strong> packages  | 
     unknown/blank licenses: <strong>{rep.get("unknown_or_blank", 0)}</strong></p>
  <p class="meta">By license: {summary}</p>
  <table>
    <thead><tr><th>ID</th><th>Title</th><th>License</th><th>Priority</th><th>Source</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
  <p class="meta">{_esc(rep.get("operator_duty"))}</p>
  <p class="meta">{_esc(rep.get("legal"))}</p>
</body>
</html>
"""


def _esc(s: Any) -> str:
    return (
        str(s if s is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
