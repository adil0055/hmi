#!/usr/bin/env python3
"""Render the cluster across a matrix of typefaces and vehicle states.

The output is a labelled corpus: one PNG per (font, state) with a sidecar JSON
saying exactly what the renderer drew and in which typeface.  Something reading
the cluster through a camera can then be scored honestly — every answer has a
known-correct one to be marked against.

    python3 tools/font_corpus.py --out corpus
    python3 tools/font_corpus.py --out corpus --fonts titillium liberation-sans
    python3 tools/font_corpus.py --out corpus --list

The default font set is chosen to be awkward on purpose.  It holds three
near-clones in each of three categories — Liberation Sans / FreeSans / DejaVu
Sans are all Helvetica-Arial grotesques, Liberation Serif / FreeSerif are both
Times clones — because a font checker that can only tell a serif from a
sans-serif has not been tested at all.  The interesting question is whether it
can tell two Arial clones apart at cluster resolution through a lens.

Each render runs in its own process.  Registering and unregistering
application fonts repeatedly inside one Qt process is exactly the kind of
global state that produces a corpus quietly mislabelled halfway through, and a
mislabelled corpus is worse than no corpus.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_DUMP = ROOT / "tools" / "text_dump.py"

#: Where distribution packages put the faces used below.
FONT_DIRS = [
    Path("/usr/share/fonts/truetype"),
    Path("/usr/share/fonts/opentype"),
    Path("/usr/local/share/fonts"),
    Path.home() / ".fonts",
    Path.home() / ".local/share/fonts",
]

#: key -> (label, [filename ...]).  Filenames are resolved against FONT_DIRS,
#: so a box missing one family just drops that entry instead of failing.
FONT_CANDIDATES: dict[str, tuple[str, list[str]]] = {
    # The cluster's own typeface.  Resolved specially, from assets/fonts.
    "titillium": ("Titillium Web", []),
    # --- grotesques: the hard group -----------------------------------------
    "liberation-sans": ("Liberation Sans", [
        "LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
        "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf"]),
    "free-sans": ("FreeSans", [
        "FreeSans.ttf", "FreeSansBold.ttf",
        "FreeSansOblique.ttf", "FreeSansBoldOblique.ttf"]),
    "dejavu-sans": ("DejaVu Sans", ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf"]),
    # --- serifs --------------------------------------------------------------
    "liberation-serif": ("Liberation Serif", [
        "LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf",
        "LiberationSerif-Italic.ttf", "LiberationSerif-BoldItalic.ttf"]),
    "free-serif": ("FreeSerif", [
        "FreeSerif.ttf", "FreeSerifBold.ttf",
        "FreeSerifItalic.ttf", "FreeSerifBoldItalic.ttf"]),
    "dejavu-serif": ("DejaVu Serif", ["DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf"]),
    # --- monospaces ----------------------------------------------------------
    "liberation-mono": ("Liberation Mono", [
        "LiberationMono-Regular.ttf", "LiberationMono-Bold.ttf",
        "LiberationMono-Italic.ttf", "LiberationMono-BoldItalic.ttf"]),
    "free-mono": ("FreeMono", [
        "FreeMono.ttf", "FreeMonoBold.ttf",
        "FreeMonoOblique.ttf", "FreeMonoBoldOblique.ttf"]),
    "dejavu-mono": ("DejaVu Sans Mono", [
        "DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf",
        "DejaVuSansMono-Oblique.ttf", "DejaVuSansMono-BoldOblique.ttf"]),
    # --- deliberate outliers -------------------------------------------------
    # Not grotesque, not Times, not monospace: a checker that scores these as
    # close to anything above is keying on something other than letterform.
    "loma": ("Loma", ["Loma.otf", "Loma-Bold.otf", "Loma-Oblique.otf"]),
    "unifont": ("Unifont", ["unifont.otf"]),
}

#: Vehicle states, picked to move the text around rather than the needles.
#: Between them they cover digits, the gear letters, both unit systems, the
#: negative sign, the degree symbol and the "no reading yet" placeholders.
STATES: dict[str, dict[str, object]] = {
    "rest": {},
    "cruise": {
        "speed": 118, "rpm": 3450, "gearMode": "D", "gearNumber": 4,
        "engineRunning": True, "fuelLevel": 0.55, "coolantTemp": 92,
    },
    "highway": {
        "speed": 97, "rpm": 2180, "gearMode": "D", "gearNumber": 6,
        "engineRunning": True, "fuelLevel": 0.62, "coolantTemp": 91,
        "tripDistance": 284.6, "tripSeconds": 10980, "avgConsumption": 17.4,
        "odometer": 48213, "outsideTemp": -6, "rangeKm": 412,
    },
    "imperial": {
        "units": "imperial", "consumptionUnits": "mpg",
        "speed": 143, "rpm": 4120, "gearMode": "D", "gearNumber": 5,
        "engineRunning": True, "fuelLevel": 0.38, "coolantTemp": 96,
        "tripDistance": 76.5, "tripSeconds": 3725, "avgConsumption": 12.9,
        "odometer": 91004, "outsideTemp": 31, "rangeKm": 233,
    },
    "sport": {
        "driveMode": "Sport", "speed": 201, "rpm": 6900, "gearMode": "D",
        "gearNumber": 5, "engineRunning": True, "fuelLevel": 0.21,
        "coolantTemp": 104, "outsideTemp": 9, "rangeKm": 88,
    },
    "reverse": {
        "gearMode": "R", "speed": 6, "rpm": 900, "engineRunning": True,
        "fuelLevel": 0.47, "coolantTemp": 74, "outsideTemp": 0, "odometer": 7,
    },
}


def resolve_font(key: str) -> tuple[str, list[Path]] | None:
    """Turn a candidate key into (label, existing files), or None if absent."""
    label, names = FONT_CANDIDATES[key]

    if key == "titillium":
        bundled = sorted((ROOT / "assets" / "fonts").glob("*.ttf"))
        return (label, bundled) if bundled else None

    found: list[Path] = []
    for name in names:
        for directory in FONT_DIRS:
            if not directory.is_dir():
                continue
            hits = sorted(directory.rglob(name))
            if hits:
                found.append(hits[0])
                break
    # The regular weight is the one the cluster leans on; without it the entry
    # is not really that family.
    return (label, found) if found else None


def render_one(job: dict, out_dir: Path, width: int, delay: int) -> dict:
    """Run text_dump.py for one (font, state) pair."""
    stem = f"{job['font']}__{job['state']}"
    png = out_dir / "frames" / f"{stem}.png"
    meta = out_dir / "frames" / f"{stem}.json"

    cmd = [sys.executable, str(TEXT_DUMP), str(png), "--json", str(meta),
           "--width", str(width), "--delay", str(delay)]
    if job["files"]:
        cmd += ["--font", *job["files"]]
    if job["set"]:
        cmd += ["--set", *[f"{k}={v}" for k, v in job["set"].items()]]

    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)

    record = {
        "font": job["font"],
        "fontLabel": job["label"],
        "state": job["state"],
        "image": str(png.relative_to(out_dir)),
        "texts": str(meta.relative_to(out_dir)),
        "ok": proc.returncode == 0 and png.is_file() and meta.is_file(),
    }
    if not record["ok"]:
        record["error"] = (proc.stderr or proc.stdout or "render failed").strip()[-400:]
        return record

    payload = json.loads(meta.read_text(encoding="utf-8"))
    families = {t["resolvedFamily"] for t in payload["texts"]}
    record["resolvedFamilies"] = sorted(families)
    record["textCount"] = len(payload["texts"])
    # Qt substitutes silently when a family will not load, so the family the
    # renderer actually used is the ground truth, not the one we asked for.
    record["requestedFamily"] = payload["font"]["family"]
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="corpus", help="output directory")
    parser.add_argument("--fonts", nargs="*", default=None,
                        help="font keys to render (default: everything available)")
    parser.add_argument("--states", nargs="*", default=None,
                        help="state keys to render (default: all)")
    parser.add_argument("--width", type=int, default=1790)
    parser.add_argument("--delay", type=int, default=700, help="ms to let each scene settle")
    parser.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--list", action="store_true",
                        help="show which fonts and states are available and exit")
    args = parser.parse_args()

    resolved = {key: resolve_font(key) for key in FONT_CANDIDATES}
    available = {k: v for k, v in resolved.items() if v is not None}

    if args.list:
        print("fonts:")
        for key, (label, files) in resolved.items():
            if files is None:
                print(f"  {key:18s} -- not installed")
            else:
                print(f"  {key:18s} {label}  ({len(files)} file(s))")
        print("\nstates:")
        for key in STATES:
            print(f"  {key}")
        return 0

    font_keys = args.fonts or list(available)
    missing = [k for k in font_keys if k not in available]
    if missing:
        print(f"error: not installed on this machine: {', '.join(missing)}", file=sys.stderr)
        print("run with --list to see what is available", file=sys.stderr)
        return 2

    state_keys = args.states or list(STATES)
    unknown = [k for k in state_keys if k not in STATES]
    if unknown:
        print(f"error: unknown state(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    (out_dir / "frames").mkdir(parents=True, exist_ok=True)

    jobs = [
        {
            "font": fk,
            "label": available[fk][0],
            "files": [str(p) for p in available[fk][1]],
            "state": sk,
            "set": STATES[sk],
        }
        for fk in font_keys
        for sk in state_keys
    ]

    print(f"rendering {len(jobs)} frames "
          f"({len(font_keys)} fonts x {len(state_keys)} states) on {args.jobs} workers")
    started = time.time()
    records: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(render_one, j, out_dir, args.width, args.delay): j for j in jobs}
        for done in concurrent.futures.as_completed(futures):
            record = done.result()
            records.append(record)
            mark = "ok " if record["ok"] else "FAIL"
            print(f"  [{len(records):3d}/{len(jobs)}] {mark} {record['font']}__{record['state']}")
            if not record["ok"]:
                print(f"        {record['error']}", file=sys.stderr)

    records.sort(key=lambda r: (r["font"], r["state"]))
    manifest = {
        "width": args.width,
        "fonts": [
            {
                "key": k,
                "label": available[k][0],
                "files": [str(p) for p in available[k][1]],
            }
            for k in font_keys
        ],
        "states": {k: STATES[k] for k in state_keys},
        "frames": records,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    failed = [r for r in records if not r["ok"]]
    print(f"\nwrote {out_dir / 'manifest.json'} in {time.time() - started:.1f}s "
          f"({len(records) - len(failed)} ok, {len(failed)} failed)")

    # A family that did not load is not a rendering bug, it is the corpus
    # quietly turning into two copies of the fallback face.  Say so loudly.
    for record in records:
        if record["ok"] and record["requestedFamily"] not in record.get("resolvedFamilies", []):
            print(f"  note: {record['font']}__{record['state']} asked for "
                  f"{record['requestedFamily']!r} but drew "
                  f"{record.get('resolvedFamilies')}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
