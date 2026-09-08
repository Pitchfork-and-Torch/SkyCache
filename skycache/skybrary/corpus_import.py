"""Legal bulk corpus import for Skybrary (Wave 2.B2 / S5).

- Import a folder of .txt / .md / .html / .epub into SkyCache packages
- Optional allowlisted open HTTPS pull (Gutenberg-style) via open_fetch

Fail-closed: license option required and must pass license_gate.
Never pirate mirrors, warez, or commercial decrypt.
Operator-run only - respect robots/terms of each host.
"""

from __future__ import annotations

import logging
import re
import shutil
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from skycache.capabilities.open_fetch import fetch_open_url, validate_open_url
from skycache.models import ContentFile, ContentPackage, PriorityClass, SourceInfo
from skycache.skybrary.integrity import sha256_file, sha256_text
from skycache.skybrary.license_gate import assert_license_allowed
from skycache.skybrary.models import Edition, Work

log = logging.getLogger("skycache.skybrary.corpus_import")

TEXT_SUFFIXES = frozenset({".txt", ".md", ".html", ".htm"})
EPUB_SUFFIXES = frozenset({".epub"})
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | EPUB_SUFFIXES

# Soft caps for operator-run bulk (avoid accidental huge dumps in one go)
DEFAULT_MAX_FILES = 200
DEFAULT_MAX_BODY_CHARS = 2_000_000
DEFAULT_OPEN_MAX_BYTES = 20 * 1024 * 1024

_ID_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag.lower() in {"script", "style"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data and data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        return "\n".join(self._chunks)


def slugify_id(raw: str, *, prefix: str = "corpus", max_len: int = 64) -> str:
    base = Path(raw).stem if raw else "work"
    base = unquote(base)
    base = base.strip().lower().replace(" ", "-")
    base = _ID_SAFE.sub("-", base).strip("-._") or "work"
    if base[0].isdigit():
        base = f"w-{base}"
    out = f"{prefix}-{base}"[:max_len].rstrip("-._")
    return out or f"{prefix}-work"


def strip_html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001
        # Fallback: crude tag strip
        return re.sub(r"<[^>]+>", " ", html)
    return parser.text().strip()


def extract_text_from_epub(path: Path, *, max_chars: int = DEFAULT_MAX_BODY_CHARS) -> str:
    """Best-effort plain text from a minimal or real EPUB (ZIP of XHTML/HTML/TXT)."""
    path = Path(path)
    chunks: list[str] = []
    total = 0
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = sorted(
                n
                for n in zf.namelist()
                if not n.endswith("/")
                and n.lower().endswith((".xhtml", ".html", ".htm", ".txt", ".xml"))
                and "meta-inf" not in n.lower()
            )
            for name in names:
                try:
                    raw = zf.read(name)
                except Exception:  # noqa: BLE001
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("latin-1", errors="replace")
                if name.lower().endswith((".xhtml", ".html", ".htm", ".xml")):
                    text = strip_html_to_text(text)
                text = text.strip()
                if not text:
                    continue
                remain = max_chars - total
                if remain <= 0:
                    break
                if len(text) > remain:
                    text = text[:remain]
                chunks.append(text)
                total += len(text)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Not a valid EPUB/ZIP: {path}") from exc
    body = "\n\n".join(chunks).strip()
    if not body:
        body = f"[EPUB package {path.name}: no extractable text; binary retained for offline use.]"
    return body


def _read_text_file(path: Path, *, max_chars: int = DEFAULT_MAX_BODY_CHARS) -> str:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        text = strip_html_to_text(text)
    if len(text) > max_chars:
        text = text[:max_chars]
    return text


def _html_wrapper(
    *,
    title: str,
    license_name: str,
    creators: str,
    digest: str,
    body: str,
    payload_link: str | None = None,
    source_note: str = "",
) -> str:
    payload = (
        f'<p><a href="{payload_link}">Download original file</a></p>' if payload_link else ""
    )
    src = f"<p class=\"meta\">{source_note}</p>" if source_note else ""
    # Escape minimal HTML specials in body for pre
    safe_body = (
        body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{title}</title>
<style>body{{font-family:Georgia,serif;max-width:40rem;margin:1.5rem auto;padding:0 1rem;line-height:1.55;
background:#0b1220;color:#f1f5f9}} h1{{font-size:1.35rem;color:#5eead4}}
.meta{{color:#94a3b8;font-size:.9rem}} pre{{white-space:pre-wrap;font-family:Georgia,serif}}
a{{color:#38bdf8}}</style></head><body>
<p class="meta">Skybrary corpus import  |  Open license required  |  Not a complete archive</p>
<h1>{title}</h1>
<p class="meta">{creators}  |  license: {license_name}  |  sha256: {digest[:16]}...</p>
{src}
{payload}
<pre>{safe_body}</pre>
<p class="meta">SkyCache / Skybrary - store-and-forward open knowledge. Never pirate mirrors.</p>
</body></html>
"""


def build_work_package(
    out_dir: Path,
    *,
    work_id: str,
    title: str,
    body: str,
    license_name: str,
    creators: list[str] | None = None,
    subjects: list[str] | None = None,
    language: str = "en",
    provenance: dict[str, Any] | None = None,
    fmt: str = "txt",
    payload_src: Path | None = None,
    payload_name: str | None = None,
    priority_class: str = "education",
) -> Path:
    """Write a SkyCache package dir with work.txt, index.html, optional payload, manifest."""
    lic = assert_license_allowed(license_name)
    work_id = work_id.strip()
    if not work_id or any(c in work_id for c in ("/", "\\", "..")):
        raise ValueError(f"Unsafe work_id: {work_id!r}")

    creators = list(creators or ["unknown"])
    subjects = list(subjects or ["corpus_import", "literature_pd"])
    provenance = dict(provenance or {"source": "corpus_import"})
    stamp = datetime.now(timezone.utc)

    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    body_bytes = body.encode("utf-8")
    (out_dir / "work.txt").write_bytes(body_bytes)
    digest = sha256_text(body)

    payload_rel: str | None = None
    payload_size = 0
    payload_sha = ""
    if payload_src is not None:
        src = Path(payload_src)
        name = payload_name or src.name
        # Keep simple basename
        name = Path(name).name
        dest = out_dir / name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        payload_rel = name
        payload_size = dest.stat().st_size
        payload_sha = sha256_file(dest)

    title_map = {"en": title}
    summary_map = {"en": title[:240]}
    creator_str = "  |  ".join(creators)
    html = _html_wrapper(
        title=title,
        license_name=lic,
        creators=creator_str,
        digest=digest,
        body=body[:50_000] + ("..." if len(body) > 50_000 else ""),
        payload_link=payload_rel,
        source_note=str(provenance.get("note") or provenance.get("url") or ""),
    )
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    html_size = len(html.encode("utf-8"))

    work = Work(
        work_id=work_id,
        title=title_map,
        creators=creators,
        languages=[language],
        subjects=subjects,
        license=lic,
        provenance=provenance,
        civilizational_tier=3,
        summary=summary_map,
    )
    edition_path = payload_rel if payload_rel and fmt == "epub" else "work.txt"
    edition_fmt = fmt if fmt in {"txt", "epub", "pdf", "md", "html"} else "txt"
    edition = Edition(
        edition_id=f"{work_id}-{edition_fmt}",
        work_id=work_id,
        format=edition_fmt,
        path=edition_path,
        size_bytes=payload_size if edition_fmt == "epub" and payload_size else len(body_bytes),
        sha256=payload_sha if edition_fmt == "epub" and payload_sha else digest,
        priority_class=priority_class,
        received_at=stamp,
    )

    files = [
        ContentFile(path="index.html", mime="text/html", size_bytes=html_size, role="index"),
        ContentFile(
            path="work.txt",
            mime="text/plain",
            size_bytes=len(body_bytes),
            role="payload",
        ),
    ]
    if payload_rel:
        mime = "application/epub+zip" if payload_rel.lower().endswith(".epub") else "application/octet-stream"
        files.append(
            ContentFile(
                path=payload_rel,
                mime=mime,
                size_bytes=payload_size,
                role="payload",
            )
        )

    try:
        pclass = PriorityClass(priority_class)
    except ValueError:
        pclass = PriorityClass.EDUCATION

    size_total = sum(f.size_bytes for f in files)
    pkg = ContentPackage(
        id=work_id,
        kind="skybrary_text",
        priority_class=pclass,
        title=title_map,
        summary=summary_map,
        languages=[language],
        received_at=stamp,
        freshness_hours=8760 * 10,
        size_bytes=size_total,
        license=lic,
        source=SourceInfo(
            type="corpus_import",
            legal_note="Operator-verified open license; fail-closed gate",
            plugin="corpus_folder_import",
            extra={
                "work": work.model_dump(mode="json"),
                "edition": edition.model_dump(mode="json"),
                "sha256": digest,
                "payload_sha256": payload_sha or None,
                "provenance": provenance,
            },
        ),
        files=files,
        tags=["skybrary", "corpus", lic.replace(" ", "-")] + subjects[:6],
        icon="education",
    )
    (out_dir / "manifest.json").write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
    return out_dir


def discover_corpus_files(
    source_dir: Path,
    *,
    recursive: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
) -> list[Path]:
    source_dir = Path(source_dir)
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Not a directory: {source_dir}")
    files: list[Path] = []
    if recursive:
        candidates = sorted(source_dir.rglob("*"))
    else:
        candidates = sorted(source_dir.iterdir())
    for p in candidates:
        if not p.is_file():
            continue
        if p.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if p.name.startswith("."):
            continue
        files.append(p)
        if len(files) >= max_files:
            break
    return files


def import_folder(
    source_dir: Path,
    out_dir: Path,
    *,
    license_name: str,
    language: str = "en",
    subjects: list[str] | None = None,
    creators: list[str] | None = None,
    recursive: bool = False,
    max_files: int = DEFAULT_MAX_FILES,
    id_prefix: str = "corpus",
) -> dict[str, Any]:
    """Import .txt/.md/.html/.epub from a directory. License required (fail closed)."""
    lic = assert_license_allowed(license_name)
    source_dir = Path(source_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = discover_corpus_files(source_dir, recursive=recursive, max_files=max_files)
    packages: list[str] = []
    errors: list[str] = []
    subjects = subjects or ["corpus_import"]

    for src in files:
        try:
            work_id = slugify_id(src.name, prefix=id_prefix)
            title = src.stem.replace("_", " ").replace("-", " ").strip() or work_id
            fmt = "epub" if src.suffix.lower() in EPUB_SUFFIXES else (
                "html" if src.suffix.lower() in {".html", ".htm"} else
                "md" if src.suffix.lower() == ".md" else "txt"
            )
            if src.suffix.lower() in EPUB_SUFFIXES:
                body = extract_text_from_epub(src)
                payload_src = src
            else:
                body = _read_text_file(src)
                payload_src = None
            if not body.strip():
                errors.append(f"{src.name}: empty body")
                continue
            pkg_path = build_work_package(
                out_dir / work_id,
                work_id=work_id,
                title=title,
                body=body,
                license_name=lic,
                creators=creators,
                subjects=subjects,
                language=language,
                provenance={
                    "source": "corpus_folder",
                    "path": str(src.name),
                    "note": "Local folder import; operator verified license",
                },
                fmt=fmt if fmt in {"txt", "epub", "md", "html"} else "txt",
                payload_src=payload_src,
            )
            packages.append(str(pkg_path))
        except Exception as exc:  # noqa: BLE001
            log.warning("corpus skip %s: %s", src, exc)
            errors.append(f"{src.name}: {exc}")

    return {
        "ok": len(packages) > 0,
        "license": lic,
        "source_dir": str(source_dir),
        "imported": len(packages),
        "total_candidates": len(files),
        "packages": packages,
        "errors": errors,
        "legal": "Open/authorized licenses only - never pirate mirrors",
    }


def import_open_url(
    url: str,
    out_dir: Path,
    *,
    license_name: str,
    title: str | None = None,
    work_id: str | None = None,
    language: str = "en",
    subjects: list[str] | None = None,
    creators: list[str] | None = None,
    extra_hosts: list[str] | None = None,
    max_bytes: int = DEFAULT_OPEN_MAX_BYTES,
) -> dict[str, Any]:
    """Fetch one allowlisted open URL (e.g. gutenberg.org) and package it.

    Uses open_fetch allowlist. License still required (operator verifies the work).
    """
    lic = assert_license_allowed(license_name)
    url = validate_open_url(url, extra_hosts)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    filename = Path(unquote(parsed.path)).name or "payload.bin"
    # Normalize weird gutenberg names like "1342-0.txt"
    if not filename or filename in {".", "/"}:
        filename = "payload.bin"

    wid = work_id or slugify_id(filename, prefix="open")
    work_out = out_dir / wid
    work_out.mkdir(parents=True, exist_ok=True)
    dest = work_out / filename

    meta = fetch_open_url(url, dest, extra_hosts=extra_hosts, max_bytes=max_bytes)
    suffix = Path(filename).suffix.lower()
    display_title = title or Path(filename).stem.replace("-", " ").replace("_", " ").strip() or wid

    if suffix in EPUB_SUFFIXES:
        body = extract_text_from_epub(dest)
        fmt = "epub"
        payload_src = dest
    elif suffix in TEXT_SUFFIXES or suffix == "":
        body = _read_text_file(dest)
        fmt = "html" if suffix in {".html", ".htm"} else "txt"
        payload_src = None
    else:
        # Unknown binary: keep payload, minimal body for FTS
        body = (
            f"Open import payload: {filename}\n"
            f"URL: {url}\n"
            f"Bytes: {meta.get('bytes')}\n"
            f"Content-Type: {meta.get('content_type')}\n"
            "[Operator must verify open license before redistribution.]"
        )
        fmt = "txt"
        payload_src = dest

    # If payload was already written into work_out and build will re-copy, fine.
    # For text files we already have body; may leave original file as payload too.
    if payload_src is None and dest.is_file() and suffix in TEXT_SUFFIXES:
        # Keep original alongside work.txt for provenance
        payload_src = dest
        payload_name = filename
    else:
        payload_name = filename if payload_src is not None else None

    # build_work_package wipes out_dir - move payload aside if needed
    staging = out_dir / f".staging-{wid}"
    staging.mkdir(parents=True, exist_ok=True)
    staged_payload: Path | None = None
    if payload_src is not None and Path(payload_src).is_file():
        staged_payload = staging / Path(payload_src).name
        if Path(payload_src).resolve() != staged_payload.resolve():
            shutil.copy2(payload_src, staged_payload)
        else:
            staged_payload = Path(payload_src)

    pkg_path = build_work_package(
        work_out,
        work_id=wid,
        title=display_title,
        body=body,
        license_name=lic,
        creators=creators or ["open import"],
        subjects=subjects or ["corpus_import", "open_http"],
        language=language,
        provenance={
            "source": "open_url",
            "url": url,
            "retrieved_bytes": meta.get("bytes"),
            "content_type": meta.get("content_type"),
            "note": "Allowlisted open HTTPS; operator verified license; never pirate mirrors",
        },
        fmt=fmt,
        payload_src=staged_payload,
        payload_name=payload_name,
    )
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)

    return {
        "ok": True,
        "license": lic,
        "url": url,
        "work_id": wid,
        "package": str(pkg_path),
        "bytes": meta.get("bytes"),
        "legal": "Allowlisted open host + operator license - never pirate mirrors",
    }


def register_packages_to_skybrary(
    package_dirs: list[Path],
    *,
    settings: Any,
    register_content: bool = True,
) -> list[str]:
    """Ingest package dirs into content catalog + Skybrary works FTS."""
    from skycache.db.catalog import Catalog
    from skycache.ingest.normalizer import ContentManager
    from skycache.skybrary.catalog import SkybraryCatalog
    from skycache.skybrary.ingest import ingest_package_dir_to_skybrary

    catalog = Catalog(settings.db_path)
    content = ContentManager(settings, catalog) if register_content else None
    sky = SkybraryCatalog(settings.skybrary_db_path)
    ids: list[str] = []
    try:
        for p in package_dirs:
            wid = ingest_package_dir_to_skybrary(Path(p), sky=sky, content=content)
            ids.append(wid)
    finally:
        sky.close()
        catalog.close()
    return ids
