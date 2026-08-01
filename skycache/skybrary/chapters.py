"""Multi-file chapter navigation + light EPUB spine for in-PWA reader (v0.9.1)."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from skycache.skybrary.corpus_import import extract_text_from_epub, strip_html_to_text

# Prefer these roles for chapter order
_TEXT_SUFFIXES = {".txt", ".md", ".html", ".htm", ".xhtml"}
_SKIP_NAMES = {"manifest.json", "profile-manifest.json", "profile-manifest.sha256"}


def list_package_chapters(package_dir: Path) -> list[dict[str, Any]]:
    """List readable chapter-like files in a package directory (stable order)."""
    package_dir = Path(package_dir)
    if not package_dir.is_dir():
        return []

    chapters: list[dict[str, Any]] = []
    # Prefer explicit chapters/ or parts/ dirs
    ordered: list[Path] = []
    for sub in ("chapters", "parts", "text", "OEBPS", "ops"):
        d = package_dir / sub
        if d.is_dir():
            ordered.extend(sorted(p for p in d.rglob("*") if p.is_file()))
    # Root-level readable files
    root_files = sorted(
        p
        for p in package_dir.iterdir()
        if p.is_file() and p.name not in _SKIP_NAMES
    )
    for p in root_files:
        if p not in ordered:
            ordered.append(p)
    # Nested remaining
    for p in sorted(package_dir.rglob("*")):
        if p.is_file() and p not in ordered and p.name not in _SKIP_NAMES:
            ordered.append(p)

    idx = 0
    for p in ordered:
        rel = p.relative_to(package_dir).as_posix()
        suf = p.suffix.lower()
        if suf == ".epub":
            spine = list_epub_spine_entries(p)
            if spine:
                for s in spine:
                    chapters.append(
                        {
                            "index": idx,
                            "id": f"epub-{idx}",
                            "title": s.get("title") or f"Section {idx + 1}",
                            "path": rel,
                            "epub_inner": s.get("href"),
                            "format": "epub-section",
                            "size_bytes": p.stat().st_size,
                        }
                    )
                    idx += 1
            else:
                chapters.append(
                    {
                        "index": idx,
                        "id": f"ch-{idx}",
                        "title": p.stem.replace("-", " ").replace("_", " "),
                        "path": rel,
                        "format": "epub",
                        "size_bytes": p.stat().st_size,
                    }
                )
                idx += 1
            continue
        if suf not in _TEXT_SUFFIXES and suf not in {".pdf"}:
            continue
        if p.name.lower() == "index.html" and any(
            c.get("path") == "work.txt" for c in chapters
        ):
            # Keep index as optional last chapter if work.txt exists
            pass
        title = p.stem.replace("-", " ").replace("_", " ")
        if p.name == "work.txt":
            title = "Full text"
        chapters.append(
            {
                "index": idx,
                "id": f"ch-{idx}",
                "title": title,
                "path": rel,
                "format": suf.lstrip(".") or "bin",
                "size_bytes": p.stat().st_size,
            }
        )
        idx += 1

    # Stable preference: work.txt first if present
    chapters.sort(
        key=lambda c: (
            0 if c.get("path") == "work.txt" else 1,
            2 if c.get("path") == "index.html" else 0,
            c.get("index", 0),
        )
    )
    for i, c in enumerate(chapters):
        c["index"] = i
        c["id"] = f"ch-{i}"
    return chapters


def list_epub_spine_entries(epub_path: Path, *, limit: int = 80) -> list[dict[str, str]]:
    """Best-effort OPF spine listing from an EPUB zip."""
    epub_path = Path(epub_path)
    try:
        with zipfile.ZipFile(epub_path, "r") as zf:
            names = zf.namelist()
            opf = next((n for n in names if n.lower().endswith(".opf")), None)
            if not opf:
                # Fall back to ordered xhtml
                xhtml = sorted(
                    n
                    for n in names
                    if n.lower().endswith((".xhtml", ".html", ".htm"))
                    and "meta-inf" not in n.lower()
                )
                return [
                    {"href": n, "title": Path(n).stem.replace("-", " ")[:80]}
                    for n in xhtml[:limit]
                ]
            raw = zf.read(opf)
            try:
                root = ET.fromstring(raw)
            except ET.ParseError:
                return []
            # Handle namespaces loosely
            def local(tag: str) -> str:
                return tag.rsplit("}", 1)[-1].lower()

            id_to_href: dict[str, str] = {}
            id_to_title: dict[str, str] = {}
            for el in root.iter():
                if local(el.tag) == "item":
                    iid = el.attrib.get("id") or ""
                    href = el.attrib.get("href") or ""
                    if iid and href:
                        id_to_href[iid] = href
                        id_to_title[iid] = Path(href).stem.replace("-", " ")[:80]
            spine: list[dict[str, str]] = []
            for el in root.iter():
                if local(el.tag) == "itemref":
                    idref = el.attrib.get("idref") or ""
                    href = id_to_href.get(idref, "")
                    if href:
                        # resolve relative to opf dir
                        base = str(Path(opf).parent).replace("\\", "/")
                        if base in (".", ""):
                            full = href
                        else:
                            full = f"{base}/{href}".replace("//", "/")
                        spine.append(
                            {
                                "href": full,
                                "title": id_to_title.get(idref) or Path(href).stem,
                            }
                        )
                    if len(spine) >= limit:
                        break
            return spine
    except (zipfile.BadZipFile, OSError, KeyError):
        return []


def read_chapter_text(
    package_dir: Path,
    *,
    path: str,
    epub_inner: str | None = None,
    max_chars: int = 400_000,
) -> dict[str, Any]:
    """Load text for a chapter path (including optional EPUB inner file)."""
    package_dir = Path(package_dir)
    rel = Path(path)
    if ".." in rel.parts:
        raise ValueError("path traversal refused")
    target = (package_dir / rel).resolve()
    if not str(target).startswith(str(package_dir.resolve())):
        raise ValueError("path traversal refused")
    if not target.is_file():
        raise FileNotFoundError(path)

    if target.suffix.lower() == ".epub":
        if epub_inner:
            with zipfile.ZipFile(target, "r") as zf:
                # normalize
                candidates = [epub_inner, epub_inner.lstrip("./")]
                data = None
                for c in candidates:
                    try:
                        data = zf.read(c)
                        break
                    except KeyError:
                        continue
                if data is None:
                    # try basename match
                    base = Path(epub_inner).name
                    for n in zf.namelist():
                        if n.endswith(base):
                            data = zf.read(n)
                            break
                if data is None:
                    raise FileNotFoundError(epub_inner)
                try:
                    html = data.decode("utf-8")
                except UnicodeDecodeError:
                    html = data.decode("latin-1", errors="replace")
                body = strip_html_to_text(html) if "<" in html[:200] else html
                if len(body) > max_chars:
                    body = body[:max_chars]
                return {
                    "ok": True,
                    "path": path,
                    "epub_inner": epub_inner,
                    "format": "epub-section",
                    "kind": "text",
                    "body": body,
                }
        body = extract_text_from_epub(target, max_chars=max_chars)
        return {
            "ok": True,
            "path": path,
            "format": "epub",
            "kind": "text",
            "body": body,
        }

    raw = target.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    kind = "html" if target.suffix.lower() in {".html", ".htm", ".xhtml"} else "text"
    if kind == "html":
        # Return html body for client sanitizer; also plain fallback
        body = text
    else:
        body = text
    if len(body) > max_chars:
        body = body[:max_chars]
    return {
        "ok": True,
        "path": path,
        "format": target.suffix.lstrip("."),
        "kind": kind,
        "body": body,
    }


def chapters_for_work(
    *,
    work: dict[str, Any],
    content_dir: Path,
    package_path: Path | None = None,
) -> dict[str, Any]:
    """Resolve package dir from work and list chapters."""
    content_dir = Path(content_dir)
    pkg_id = work.get("package_id") or work.get("work_id")
    pkg_dir = package_path
    if pkg_dir is None and pkg_id:
        candidate = content_dir / str(pkg_id)
        if candidate.is_dir():
            pkg_dir = candidate
    chapters: list[dict[str, Any]] = []
    if pkg_dir and Path(pkg_dir).is_dir():
        chapters = list_package_chapters(Path(pkg_dir))
    # editions as soft chapters if empty
    if not chapters:
        for ed in work.get("editions") or []:
            chapters.append(
                {
                    "index": len(chapters),
                    "id": f"ed-{ed.get('edition_id')}",
                    "title": f"{ed.get('format', 'file')} edition",
                    "path": ed.get("path") or "work.txt",
                    "format": ed.get("format") or "txt",
                    "size_bytes": ed.get("size_bytes") or 0,
                }
            )
    return {
        "work_id": work.get("work_id"),
        "package_id": pkg_id,
        "chapter_count": len(chapters),
        "chapters": chapters,
        "legal": "Open/PD package reading only. Not a complete archive claim.",
    }
