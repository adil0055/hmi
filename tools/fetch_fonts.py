#!/usr/bin/env python3
"""Download the typefaces listed in assets/fonts/catalog.json.

Every family in the catalogue is redistributable (SIL OFL 1.1 or Apache 2.0)
and comes from the upstream google/fonts repository, and the files are
committed alongside it — so a clone needs nothing and this only has to be run
after adding a family to the catalogue, or to repair a missing file.

    python3 tools/fetch_fonts.py            # fetch whatever is missing
    python3 tools/fetch_fonts.py --force    # re-download everything
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
CATALOG = FONT_DIR / "catalog.json"
BASE = "https://raw.githubusercontent.com/google/fonts/main"


def fetch(url: str, target: Path) -> int:
    """Download `url` to `target`, returning the byte count."""
    request = urllib.request.Request(url, headers={"User-Agent": "car-hmi/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    # A repository that answers 200 with an HTML error page would otherwise
    # leave a file that QFontDatabase silently refuses at runtime.
    if payload[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf"):
        raise ValueError(f"not a font file ({payload[:16]!r})")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return len(payload)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args(argv)

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    families = catalog["families"]

    total = skipped = failed = 0
    for family in families:
        directory = FONT_DIR / family["dir"]
        wanted = [*family["files"], "OFL.txt"] if family["licence"].startswith("SIL") \
            else [*family["files"], "LICENSE.txt"]
        for name in wanted:
            target = directory / name
            if target.exists() and not args.force:
                skipped += 1
                continue
            url = f"{BASE}/{family['source']}/{urllib.parse.quote(name)}"
            try:
                if name in ("OFL.txt", "LICENSE.txt"):
                    # Licence text, not a font — fetch without the header check.
                    request = urllib.request.Request(url, headers={"User-Agent": "car-hmi/1.0"})
                    with urllib.request.urlopen(request, timeout=60) as response:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(response.read())
                    size = target.stat().st_size
                else:
                    size = fetch(url, target)
            except (urllib.error.URLError, ValueError, TimeoutError) as exc:
                print(f"  FAILED {family['name']}/{name}: {exc}", file=sys.stderr)
                failed += 1
                continue
            print(f"  {family['name']}/{name}  ({size // 1024} KB)")
            total += 1

    print(f"\n{total} downloaded, {skipped} already present, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
