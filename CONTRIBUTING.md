# Contributing to SkyCache

Thank you for helping improve offline information access.

## Ground rules

1. Read [`docs/legal-ethics.md`](docs/legal-ethics.md).  
2. **No commercial decryption** or encrypted-constellation support.  
3. Prefer wrapping mature tools (SatDump, gr-satellites, Kiwix) over reimplementation.  
4. Keep the sim demo working without hardware.  
5. Add tests for prioritizer / ingest / API changes.  

## Dev setup

```bash
python -m pip install -e ".[dev]"
python scripts/make_sample_package.py
pytest -q
ruff check skycache tests
```

## Plugin PRs

Document:

- Frequencies / modes  
- Legal profile (`fta_public` / `amateur_open` / `file_import_only`)  
- Hardware requirements  
- How to test with a file fixture  

## Code style

- Python 3.11+, type hints encouraged  
- UTF-8 files without BOM  
- Clear comments on legal and safety boundaries  
