"""Community content authoring helper - scaffolds operator-authored local packs.

Creates a simple HTML package from title/body for village notices, clinic hours,
or school materials. License defaults to operator_supplied; inventory remains
the operator's duty.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from skycache.models import (
    CaptureResult,
    ContentFile,
    ContentPackage,
    PriorityClass,
    SourceInfo,
    SourceSpec,
)


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return (s or "community-note")[:48]


class CommunityBoardPlugin:
    name = "community_board"
    description = "Scaffold community-authored local HTML packages (operator license duty)"
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        return source.plugin == self.name

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        opts = source.options or {}
        title = str(opts.get("title") or "Community notice").strip()
        body = str(opts.get("body") or "Local community content.").strip()
        lang = str(opts.get("lang") or "en").strip()[:8]
        prio_raw = str(opts.get("priority") or "general").lower()
        try:
            pclass = PriorityClass(prio_raw)
        except ValueError:
            pclass = PriorityClass.GENERAL
        # Never allow emergency without explicit opt-in
        if pclass == PriorityClass.EMERGENCY and not opts.get("confirm_emergency"):
            pclass = PriorityClass.GENERAL

        pkg_id = _slug(str(opts.get("id") or f"community-{title}"))
        dest = Path(workdir) / pkg_id
        dest.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc)

        html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 40rem; margin: 1.5rem auto;
      padding: 0 1rem; background: #0b1220; color: #f1f5f9; line-height: 1.5; }}
    .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px;
      background: #134e4a; color: #5eead4; font-size: 0.8rem; }}
  </style>
</head>
<body>
  <p class="badge">Community  |  local author</p>
  <h1>{_esc(title)}</h1>
  <p>{_esc(body)}</p>
  <p style="color:#94a3b8;font-size:0.9rem">SkyCache Nexus local pack. Not commercial internet.</p>
</body>
</html>
"""
        index = dest / "index.html"
        index.write_text(html, encoding="utf-8")
        size = index.stat().st_size
        pkg = ContentPackage(
            id=pkg_id,
            kind="community",
            priority_class=pclass,
            title={lang: title, "en": title},
            summary={lang: body[:200], "en": body[:200]},
            languages=[lang],
            received_at=stamp,
            freshness_hours=int(opts.get("freshness_hours") or 168),
            size_bytes=size,
            license=str(opts.get("license") or "operator_supplied"),
            source=SourceInfo(
                type="community_authored",
                legal_note="Operator confirms redistribution rights",
                plugin=self.name,
            ),
            files=[ContentFile(path="index.html", mime="text/html", size_bytes=size)],
            tags=["community", "local"],
            icon=pclass.value,
        )
        (dest / "manifest.json").write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Created community pack {pkg_id}",
            artifacts=[str(dest / "manifest.json")],
            suggested_package=pkg,
        )


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
