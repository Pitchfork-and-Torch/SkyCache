from pathlib import Path

from skycache.packages.builder import create_package, validate_package_dir


def test_create_and_validate(tmp_path: Path):
    out = tmp_path / "edu-demo"
    create_package(
        out,
        package_id="edu-demo-001",
        title="Demo lesson",
        priority_class="education",
        summary="A short demo",
    )
    assert (out / "manifest.json").is_file()
    assert (out / "index.html").is_file()
    assert validate_package_dir(out) == []


def test_validate_missing_file(tmp_path: Path):
    out = tmp_path / "bad"
    create_package(out, package_id="bad-001", title="Bad")
    # Break package: remove payload
    (out / "index.html").unlink()
    errs = validate_package_dir(out)
    assert any("Missing file" in e for e in errs)


def test_forbidden_source_in_manifest(tmp_path: Path):
    out = tmp_path / "evil"
    create_package(out, package_id="evil-001", title="No")
    text = (out / "manifest.json").read_text(encoding="utf-8")
    text = text.replace("package_create", "starlink-decoder")
    (out / "manifest.json").write_text(text, encoding="utf-8")
    errs = validate_package_dir(out)
    assert any("Forbidden" in e for e in errs)
