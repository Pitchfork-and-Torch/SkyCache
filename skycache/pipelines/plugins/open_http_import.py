"""Import a single open allowlisted HTTPS resource into a SkyCache package.

Legal: open-content hosts only (see capabilities.open_fetch). Never commercial decrypt.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from skycache.capabilities.open_fetch import fetch_open_url, load_extra_hosts
from skycache.models import (
    CaptureResult,
    ContentFile,
    ContentPackage,
    PriorityClass,
    SourceInfo,
    SourceSpec,
)
from skycache.skybrary.integrity import sha256_file
from skycache.skybrary.license_gate import assert_license_allowed


class OpenHttpImportPlugin:
    name = "open_http_import"
    description = "Fetch allowlisted open HTTPS URL into a content package (license required in options)"
    legal_profile = "file_import_only"
    requires_hardware = False

    def can_handle(self, source: SourceSpec) -> bool:
        return source.plugin == self.name or (
            (source.uri or "").startswith("https://") and source.plugin in (None, "", self.name)
        )

    def run(self, source: SourceSpec, workdir: Path) -> CaptureResult:
        opts = source.options or {}
        url = source.uri or str(opts.get("url") or "")
        license_name = str(opts.get("license") or "")
        try:
            assert_license_allowed(license_name)
        except ValueError as exc:
            return CaptureResult(plugin=self.name, success=False, message=str(exc))

        title = str(opts.get("title") or "Open web resource")
        pkg_id = str(opts.get("id") or "open-http-import")[:80]
        priority = str(opts.get("priority") or "education")
        try:
            pclass = PriorityClass(priority)
        except ValueError:
            pclass = PriorityClass.EDUCATION

        extra_hosts = load_extra_hosts(Path(opts["hosts_file"])) if opts.get("hosts_file") else []
        dest_dir = Path(workdir) / pkg_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        filename = str(opts.get("filename") or "payload.bin")
        try:
            meta = fetch_open_url(
                url,
                dest_dir / filename,
                extra_hosts=extra_hosts,
                max_bytes=int(opts.get("max_bytes") or 50 * 1024 * 1024),
            )
        except (ValueError, RuntimeError) as exc:
            return CaptureResult(plugin=self.name, success=False, message=str(exc))

        digest = sha256_file(dest_dir / filename)
        size = int(meta["bytes"])
        stamp = datetime.now(timezone.utc)
        # Minimal HTML wrapper for PWA
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>{title}</title>
<style>body{{font-family:system-ui;max-width:40rem;margin:1.5rem auto;padding:0 1rem;
background:#0b1220;color:#f1f5f9}} a{{color:#38bdf8}}</style></head><body>
<p>SkyCache open HTTPS import</p>
<h1>{title}</h1>
<p>License: {license_name}</p>
<p>Source: {url}</p>
<p>SHA-256: {digest}</p>
<p><a href="{filename}">Download payload</a></p>
<p>Open content only - not commercial broadband.</p>
</body></html>"""
        (dest_dir / "index.html").write_text(html, encoding="utf-8")
        pkg = ContentPackage(
            id=pkg_id,
            kind="open_http",
            priority_class=pclass,
            title={"en": title},
            summary={"en": f"Open fetch from allowlisted host ({license_name})"},
            languages=["en"],
            received_at=stamp,
            freshness_hours=int(opts.get("freshness_hours") or 168),
            size_bytes=size + len(html.encode("utf-8")),
            license=license_name,
            source=SourceInfo(
                type="open_https",
                legal_note="Allowlisted open host; operator verified license",
                plugin=self.name,
                extra={"url": url, "sha256": digest},
            ),
            files=[
                ContentFile(
                    path="index.html",
                    mime="text/html",
                    size_bytes=len(html.encode("utf-8")),
                    role="index",
                ),
                ContentFile(
                    path=filename,
                    mime=str(meta.get("content_type") or "application/octet-stream"),
                    size_bytes=size,
                    role="payload",
                ),
            ],
            tags=["open-http", "skybrary"],
            icon="education",
        )
        (dest_dir / "manifest.json").write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
        return CaptureResult(
            plugin=self.name,
            success=True,
            message=f"Fetched open resource {url} ({size} bytes)",
            artifacts=[str(dest_dir / "manifest.json")],
            suggested_package=pkg,
            metadata={"sha256": digest, "bytes": size},
        )
