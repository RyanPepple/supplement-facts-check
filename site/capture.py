#!/usr/bin/env python3
"""Capture the evidence behind a score: the product listing and the label panel.

Every scored row needs two dated screenshots of the live listing. This takes
them with headless Chrome so a re-capture pass is reproducible and the files
land with the naming the site already expects:

    captures/<prefix>-listing-<YYYY-MM-DD>.png
    captures/<prefix>-panel-<YYYY-MM-DD>.png

The panel is one image in Amazon's gallery and which one varies by product, so
it is a two-step job. Sheets first, then capture the chosen index:

    python3 site/capture.py listings            # all scored rows
    python3 site/capture.py sheets              # contact sheet per product
    python3 site/capture.py panel florastor 5   # gallery image 5 is the panel

Nothing here reads a label or changes a score. It only puts dated evidence on
disk; the reading stays a human judgment made against the committed file.

Requires: Pillow, and Google Chrome at the path below.
"""
import csv
import json
import random
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parent.parent
CAPS = ROOT / "captures"
SHEETS = ROOT / ".capture-sheets"          # scratch, not committed
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
TODAY = date.today().isoformat()


def chrome(args, capture=False):
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--user-agent={UA}", "--virtual-time-budget=10000", *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    return r.stdout if capture else None


def shot(url, out, width=1400, height=3200):
    chrome([f"--window-size={width},{height}", f"--screenshot={out}", url])
    return Path(out).exists()


# Amazon answers rapid automated requests with an interstitial instead of the
# listing. It renders as a near-empty page, two orders of magnitude smaller than
# a real one, so size alone separates them. A gate page is never evidence: it is
# deleted on sight rather than written into captures/. The response to being
# gated is to slow down, never to click through it.
GATE_BYTES = 200_000


def shot_verified(url, out, width=1400, height=3200, tries=3):
    for attempt in range(1, tries + 1):
        if shot(url, out, width, height) and Path(out).stat().st_size >= GATE_BYTES:
            return True
        Path(out).unlink(missing_ok=True)
        if attempt < tries:
            wait = 120 * attempt + random.randint(0, 60)
            print(f"   gated, waiting {wait}s before retry {attempt + 1}/{tries}", flush=True)
            time.sleep(wait)
    return False


def trim(path):
    """Crop the white margin a rendered image leaves around itself."""
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).getbbox()
    if box:
        im.crop(box).save(path)


def gallery(asin):
    """Full-resolution gallery image URLs for a listing, in display order."""
    dom = chrome([f"--dump-dom", f"https://www.amazon.com/dp/{asin}"], capture=True) or ""
    urls = re.findall(r'"hiRes":"(https://m\.media-amazon\.com/images/I/[^"]+)"', dom)
    if not urls:
        urls = re.findall(r'"large":"(https://m\.media-amazon\.com/images/I/[^"]+)"', dom)
    seen, out = set(), []
    for u in urls:
        u = u.replace("\\u002F", "/")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def rows():
    """Scored rows paired with the capture prefix already used for each."""
    prefixes = {re.match(r"(.+?)-(?:panel|listing)-\d{4}-\d{2}-\d{2}\.png$", p.name).group(1)
                for p in CAPS.glob("*.png")
                if re.match(r"(.+?)-(?:panel|listing)-\d{4}-\d{2}-\d{2}\.png$", p.name)}
    out = []
    with open(ROOT / "pilot-scores.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["total_score"].strip() or not r["asin"].strip():
                continue
            # apostrophes drop out, as they do in the site's own slugs, so
            # "Physician's Choice" matches the physicians-choice-* captures
            hay = re.sub(r"[^a-z0-9]+", "-", (r["brand"] + " " + r["product"]).lower().replace("'", ""))
            match = sorted((p for p in prefixes if all(t in hay for t in p.split("-"))),
                           key=len, reverse=True)
            if match:
                out.append((match[0], r["asin"].strip(), r["product"]))
            else:
                print(f"  no capture prefix matches {r['product']}, skipped")
    return out


def cmd_listings():
    """Capture every scored row's listing, paced so the gate is not provoked."""
    todo = [(p, a, n) for p, a, n in rows() if not (CAPS / f"{p}-listing-{TODAY}.png").exists()]
    print(f"{len(todo)} listings to capture", flush=True)
    for i, (prefix, asin, name) in enumerate(todo, 1):
        out = CAPS / f"{prefix}-listing-{TODAY}.png"
        ok = shot_verified(f"https://www.amazon.com/dp/{asin}", out)
        print(f"{'ok  ' if ok else 'GATED'} {out.name}  ({name})", flush=True)
        if i < len(todo):
            time.sleep(random.randint(45, 90))


def cmd_sheets():
    SHEETS.mkdir(exist_ok=True)
    index = {}
    for prefix, asin, name in rows():
        urls = gallery(asin)
        index[prefix] = urls
        cells = "".join(
            f'<figure style="margin:0"><figcaption style="font:700 20px sans-serif">{i}</figcaption>'
            f'<img src="{u}" style="width:100%"></figure>' for i, u in enumerate(urls))
        html = (f'<body style="margin:0;background:#fff"><h1 style="font:700 22px sans-serif">{prefix}</h1>'
                f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px">{cells}</div>')
        (SHEETS / f"{prefix}.html").write_text(html, encoding="utf-8")
        shot((SHEETS / f"{prefix}.html").as_uri(), SHEETS / f"{prefix}.png", 1600, 1400)
        print(f"{prefix}: {len(urls)} gallery images -> .capture-sheets/{prefix}.png")
    (SHEETS / "index.json").write_text(json.dumps(index, indent=1))


def cmd_panel(prefix, idx):
    urls = json.loads((SHEETS / "index.json").read_text())[prefix]
    page = SHEETS / f"{prefix}-panel.html"
    page.write_text(f'<body style="margin:0"><img src="{urls[int(idx)]}" style="width:1400px">',
                    encoding="utf-8")
    out = CAPS / f"{prefix}-panel-{TODAY}.png"
    shot(page.as_uri(), out, 1400, 4000)
    trim(out)
    print(f"ok {out.name}  {Image.open(out).size}")


if __name__ == "__main__":
    {"listings": cmd_listings, "sheets": cmd_sheets, "panel": cmd_panel}[sys.argv[1]](*sys.argv[2:])
