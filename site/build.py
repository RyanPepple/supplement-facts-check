#!/usr/bin/env python3
"""Build the Supplement Facts Check website from the repository's data files.

Every number on the site is read from the CSVs and README at build time.
Nothing is typed into a template by hand, so the site cannot drift from the
dataset. Run from the repository root:

    python3 site/build.py

Output goes to docs/, which GitHub Pages can serve directly
(Settings -> Pages -> Deploy from branch -> main, /docs).

Requires: markdown, Pillow  (pip install markdown pillow)
"""
import csv
import html
import json
import re
import shutil
from pathlib import Path

import markdown
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
REPO_URL = "https://github.com/RyanPepple/supplement-facts-check"
RAW_URL = REPO_URL + "/blob/main/"

# Set this to the final domain (no trailing slash) once it is decided, e.g.
# "https://example.com". While empty, no canonical tags, sitemap.xml or CNAME
# are written, and every link on the site stays relative.
SITE_URL = "https://supplementfactscheck.org"

# Ahrefs Web Analytics (cookieless). Loaded in the <head> of every page.
# Set AHREFS_KEY to "" to build the site with no analytics script.
AHREFS_KEY = "35knwYMmqmBZ6XSpedl1oA"
ANALYTICS = (f'<script src="https://analytics.ahrefs.com/analytics.js" data-key="{AHREFS_KEY}" async></script>'
             if AHREFS_KEY else "")

# Share image for Open Graph / X cards. Source file lives in site/, copied to docs/ at build.
OG_IMAGE = "og-image.png"

LICENSE_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
AUTHOR = {"@type": "Person", "name": "Ryan Pepple", "url": "https://github.com/RyanPepple"}

CRITERIA = [
    ("criterion_1_exact_dose_disclosed", "Exact amount for every active ingredient",
     "No proprietary blend appears anywhere on the Supplement Facts panel."),
    ("criterion_2_standardization_pct", "Standardization percentage stated",
     "Wherever potency depends on a percentage, such as % withanolides, the label states it."),
    ("criterion_3_chemical_form_named", "Chemical form or strain named",
     "“Magnesium glycinate,” not “magnesium.” For probiotics, every organism carries a strain designation."),
    ("criterion_4_dose_within_trial_range", "Dose within the trial range",
     "The disclosed dose falls inside the range human trials used for the outcome the product claims."),
    ("criterion_5_coa_publicly_accessible", "Certificate of analysis is public",
     "A third-party certificate is reachable with no email gate and no account."),
    ("criterion_6_per_serving_amounts", "Per-serving amounts are complete",
     "Serving size and servings per container are both on the panel."),
]

# ----------------------------------------------------------- comparison pairs
# Head-to-head pages for the pairs a shopper is actually choosing between.
# Both members of a pair must be scored in pilot-scores.csv: a comparison page
# is generated from the same rows as the two product pages, so a pair cannot be
# added without the data to fill it, and the build fails if a name does not match.
# Pairs are picked from the captured ranking itself -- adjacency in the top 30 is
# the only demand signal in the dataset -- plus the obvious same-segment pairs
# (two kids' products, two gummies, two of one brand's own formulas). Each pair
# is written with the better-ranked product first, so the URL is predictable.
COMPARISONS = [
    # the top of the ranking, against each other
    ("Physician's CHOICE Probiotics 60 Billion CFU", "Seed DS-01 Daily Synbiotic"),
    ("Physician's CHOICE Probiotics 60 Billion CFU", "Culturelle Pro Strength Probiotics"),
    ("Seed DS-01 Daily Synbiotic", "Culturelle Pro Strength Probiotics"),
    ("Seed DS-01 Daily Synbiotic", "Align Probiotic Pro Formula"),
    ("Culturelle Pro Strength Probiotics", "Align Probiotic Pro Formula"),
    # the two highest disclosure scores in the pilot
    ("Florastor Probiotic", "Align Probiotic Pro Formula"),
    ("Culturelle Pro Strength Probiotics", "Florastor Probiotic"),
    # direct-to-consumer brands bought on advertising rather than shelf presence
    ("Seed DS-01 Daily Synbiotic", "BIOMA Probiotics"),
    # bought on the CFU count printed on the front of the box
    ("Physician's CHOICE Probiotics 60 Billion CFU", "NewRhythm Probiotics 50 Billion CFU"),
    # drugstore shelf neighbours
    ("Nature's Bounty Probiotic Acidophilus", "NOW Supplements Probiotic-10"),
    ("Align Probiotic Pro Formula", "Phillips' Colon Health Daily Probiotic"),
    # which of one brand's own two formulas
    ("Align Probiotic Pro Formula", "Align Probiotic Bloating Relief + Food Digestion"),
    # for a child
    ("Culturelle Daily Chewable Probiotics for Kids", "MaryRuth Organics Kids Probiotics"),
    ("Culturelle Daily Chewable Probiotics for Kids", "Garden of Life Dr. Formulated Kids+ Probiotics"),
    # gummies
    ("Lemme Debloat Digestive & Gut Health Gummies", "Digestive Advantage Probiotic Gummies"),
]

e = html.escape


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "")).strip("-")


def read_csv(name):
    with open(ROOT / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def split_notes(notes):
    """Split a notes cell into {criterion number: reasoning}, plus any preamble."""
    marks = list(re.finditer(r"(?:(?<=^)|(?<=\. ))C([1-6]) ([01])(?=[: ])", notes))
    out, pre = {}, notes[: marks[0].start()].strip() if marks else notes
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(notes)
        text = notes[m.end():end].lstrip(": ").strip()
        text = re.sub(r"\s*Panel: captures/\S+(\s+Listing: captures/\S+)?\s*$", "", text)
        out[int(m.group(1))] = text[:1].upper() + text[1:]
    return pre, out


def capture_date(filename):
    """The date a capture was taken, read off its own filename."""
    m = re.search(r"-(\d{4}-\d{2}-\d{2})\.png$", filename)
    return m.group(1) if m else ""


def source_caveat(dose_row):
    """Any problem with the source paper that the row flagged but could not fix.

    The dose rows mark these inline with UNRESOLVED: or SEPARATE INCONSISTENCY:.
    They are the audit's own notes against its own sources, so they belong on the
    page rather than only in the CSV.
    """
    m = re.search(r"UNRESOLVED:|SEPARATE INCONSISTENCY:", dose_row["outcome_measured"])
    if not m:
        return "", ""
    text = dose_row["outcome_measured"]
    return text[:m.start()].rstrip(" ;-"), text[m.start():].strip()


def version_and_status(readme):
    ver = re.search(r"\*\*Methodology version:\*\*\s*([\d.]+)\s*—\s*locked\s*([\d-]+)", readme)
    return (ver.group(1), ver.group(2)) if ver else ("", "")


# ----------------------------------------------------------- structured data
# One JSON-LD graph per page, built from the same rows that render the HTML, so
# a machine reading the page gets the score, the per-criterion reasoning and the
# capture it was read from without having to parse the markup.


def page_url(path):
    return f"{SITE_URL}/{'' if path == 'index.html' else path}"


def graph(*nodes):
    return {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}


def website_node():
    return {"@type": "WebSite", "@id": f"{SITE_URL}/#website", "url": f"{SITE_URL}/",
            "name": "Supplement Facts Check", "inLanguage": "en",
            "author": AUTHOR, "publisher": AUTHOR, "license": LICENSE_URL}


def webpage_node(path, title, desc, main=None, modified=None, image=None):
    url = page_url(path)
    node = {"@type": "WebPage", "@id": url + "#page", "url": url, "name": title,
            "description": desc, "isPartOf": {"@id": f"{SITE_URL}/#website"},
            "license": LICENSE_URL, "author": AUTHOR}
    if main:
        node["mainEntity"] = {"@id": main}
    if modified:
        node["dateModified"] = modified
    if image:
        node["primaryImageOfPage"] = image
    return node


def capture_nodes(r, figs_srcs, caps):
    """ImageObject per committed capture: the evidence, addressable on its own."""
    out = []
    for src in figs_srcs:
        name, w, h = caps[src]
        view = "Supplement Facts panel" if "-panel-" in src else "Product listing"
        when = capture_date(src) or r["capture_date"]
        out.append({"@type": "ImageObject", "contentUrl": f"{SITE_URL}/captures/{name}",
                    "width": w, "height": h, "license": LICENSE_URL,
                    "caption": f"{view} of {r['product']}, captured {when}",
                    "dateCreated": when, "creditText": "Supplement Facts Check",
                    "sameAs": f"{RAW_URL}captures/{src}"})
    return out


def review_node(r, pre, why, path, images):
    """The score as a Review: 0-6 on label disclosure, with the criteria split out."""
    notes = [({"@type": "ListItem", "position": i, "name": label}, r[key] == "1")
             for i, (key, label, _) in enumerate(CRITERIA, 1)]
    body = " ".join(f"{i}. {label}: scored {r[key]}. {why.get(i, 'No reasoning recorded.')}"
                    for i, (key, label, _) in enumerate(CRITERIA, 1))
    # Product is its own node and points back at the review: Google rejects a
    # Product that has none of review / aggregateRating / offers.
    product = {"@type": "Product", "@id": page_url(path) + "#product", "name": r["product"],
               "brand": {"@type": "Brand", "name": r["brand"]},
               "review": {"@id": page_url(path) + "#review"}}
    if r.get("asin", "").strip():
        product["identifier"] = {"@type": "PropertyValue", "propertyID": "ASIN",
                                 "value": r["asin"].strip()}
    node = {
        "@type": "Review", "@id": page_url(path) + "#review",
        "name": f"{r['product']}: label disclosure score {r['total_score']}/6",
        "itemReviewed": {"@id": page_url(path) + "#product"},
        "reviewAspect": "Supplement Facts label disclosure",
        "reviewRating": {
            "@type": "Rating", "ratingValue": int(r["total_score"]), "bestRating": 6, "worstRating": 0,
            "ratingExplanation": "Six yes-or-no criteria on what the label discloses, 1 point each, no "
                                 "weighting and no partial credit. This rates disclosure only. It is not an "
                                 "assessment of whether the product works, and nothing was lab-tested.",
        },
        "positiveNotes": {"@type": "ItemList", "itemListElement": [n for n, ok in notes if ok]},
        "negativeNotes": {"@type": "ItemList", "itemListElement": [n for n, ok in notes if not ok]},
        "reviewBody": (pre + " " + body).strip(),
        "author": AUTHOR, "publisher": AUTHOR, "license": LICENSE_URL,
        "datePublished": r["capture_date"],
        "isBasedOn": {"@id": f"{SITE_URL}/#dataset"},
    }
    if images:
        node["associatedMedia"] = images
        product["image"] = [i["contentUrl"] for i in images]
    return product, node


# ---------------------------------------------------------------- templates

CSS = """
:root{--paper:#f7f5ef;--card:#fffefb;--ink:#14130f;--soft:#57534a;--rule:#14130f;
--hair:#d9d5c8;--pass:#1d6b45;--fail:#a5321f;--accent:#a5321f;--link:#14130f}
@media (prefers-color-scheme:dark){:root{--paper:#131210;--card:#1b1a17;--ink:#f1eee5;
--soft:#a8a397;--rule:#f1eee5;--hair:#36332c;--pass:#6fca9b;--fail:#f08a73;--accent:#f08a73;--link:#f1eee5}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.6 Georgia,"Iowan Old Style","Times New Roman",serif}
a{color:var(--link);text-underline-offset:3px}a:hover{color:var(--accent)}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
.sans,.brand,h1,h2,h3,nav,.panel,table,.tag,.btn,footer,.kicker{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}
header.site{border-bottom:6px solid var(--rule)}
header.site .wrap{display:flex;flex-wrap:wrap;gap:8px 24px;align-items:baseline;justify-content:space-between;padding-top:18px;padding-bottom:12px}
.brand{font-weight:900;font-size:22px;letter-spacing:-.02em;text-decoration:none}
header.site nav{display:flex;flex-wrap:wrap;gap:6px 18px}
nav a{font-size:14px;font-weight:700;text-decoration:none;text-transform:uppercase;letter-spacing:.04em}
nav a[aria-current]{text-decoration:underline;text-decoration-thickness:2px}
h1{font-size:clamp(34px,6vw,60px);line-height:1.02;letter-spacing:-.03em;font-weight:900;margin:48px 0 18px;text-wrap:balance}
h2{font-size:28px;line-height:1.15;letter-spacing:-.02em;font-weight:900;margin:64px 0 8px;padding-top:14px;border-top:6px solid var(--rule)}
h3{font-size:18px;font-weight:800;margin:28px 0 6px}
.lede{font-size:21px;line-height:1.5;max-width:42em;color:var(--ink)}
.kicker{font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)}
.note{border-left:4px solid var(--accent);padding:10px 16px;background:var(--card);margin:24px 0;max-width:46em;font-size:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:22px;margin-top:24px}
.panel{background:var(--card);border:2px solid var(--rule);padding:10px 12px 12px;color:var(--ink)}
.panel .t{font-size:30px;font-weight:900;letter-spacing:-.03em;line-height:1;border-bottom:1px solid var(--rule);padding-bottom:6px}
.panel .p{font-size:15px;font-weight:700;line-height:1.25;padding:6px 0;border-bottom:8px solid var(--rule)}
.panel .p small{display:block;font-weight:400;color:var(--soft)}
.panel .score{display:flex;justify-content:space-between;align-items:baseline;border-bottom:4px solid var(--rule);padding:4px 0}
.panel .score b{font-size:15px}.panel .score span{font-size:34px;font-weight:900;letter-spacing:-.03em}
.panel ol{list-style:none;margin:0;padding:0}
.panel li{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--hair);padding:5px 0;font-size:14px;line-height:1.3}
.panel li b{font-weight:800;white-space:nowrap}.pass{color:var(--pass)}.fail{color:var(--fail)}
.panel .f{font-size:12px;color:var(--soft);padding-top:8px;line-height:1.4}
.btn{display:inline-block;margin-top:10px;font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.05em}
.crit{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:0 32px;margin-top:12px}
.crit div{border-bottom:1px solid var(--hair);padding:14px 0}
.crit b{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;display:block;font-size:16px}
.crit span{color:var(--soft);font-size:15.5px}
.prose{max-width:46em}.prose h2{font-size:26px}.prose h3{font-size:19px}
.prose code,code{font:14px ui-monospace,Menlo,monospace;background:var(--card);border:1px solid var(--hair);padding:1px 5px}
.tablewrap{overflow-x:auto;margin:18px 0;border:2px solid var(--rule);background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.4}
th{text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.05em;border-bottom:4px solid var(--rule);padding:8px 10px;white-space:nowrap}
td{vertical-align:top;border-bottom:1px solid var(--hair);padding:8px 10px}
.prose .tablewrap td,.prose .tablewrap th{font-size:14px}
td.n{white-space:nowrap;font-weight:700}td.muted{color:var(--soft)}
.cav{display:block;margin-top:7px;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-size:12.5px;line-height:1.45;color:var(--fail)}
.cav b{font-weight:800}
input[type=search]{font:16px "Helvetica Neue",Helvetica,Arial,sans-serif;width:100%;max-width:420px;padding:10px 12px;border:2px solid var(--rule);background:var(--card);color:var(--ink)}
.why{display:grid;grid-template-columns:auto 1fr;gap:6px 18px;border-bottom:1px solid var(--hair);padding:16px 0;max-width:52em}
.why .m{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-weight:900;font-size:26px;line-height:1}
.why b{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}.why p{margin:4px 0 0;font-size:16px}
figure{margin:20px 0;max-width:520px}figure img{max-width:100%;height:auto;border:2px solid var(--rule);background:#fff}
figcaption{font-size:14px;color:var(--soft);font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}
.caps{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.rel{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:0 32px;margin-top:12px}
.rel h3{font-size:16px;margin:20px 0 4px}
.rel ul{list-style:none;padding:0;margin:0}
.rel li{display:flex;justify-content:space-between;align-items:baseline;gap:12px;border-bottom:1px solid var(--hair);padding:9px 0;font-size:15.5px}
.rel li b{font-weight:400;color:var(--soft);font-size:14px;white-space:nowrap}
.relnav{font-size:15px;margin-top:26px;padding-top:14px;border-top:1px solid var(--hair)}
.relnav span{color:var(--soft)}
footer{margin-top:80px;border-top:6px solid var(--rule);font-size:14px;color:var(--soft)}
footer .wrap{padding-top:18px;padding-bottom:40px}footer a{color:var(--soft)}
.built{display:inline-flex;align-items:stretch;margin-top:14px;border:2px solid var(--rule);color:var(--ink);text-decoration:none;font-weight:800;font-size:12px;text-transform:uppercase;letter-spacing:.08em;line-height:1;transition:background .15s,color .15s}
.built span{padding:8px 10px;border-right:2px solid var(--rule)}
.built b{padding:8px 12px;font-weight:900;letter-spacing:.16em;text-transform:lowercase}
footer a.built{color:var(--ink)}footer a.built:hover,footer a.built:focus-visible{background:var(--ink);color:var(--card)}
footer a.built:hover span,footer a.built:focus-visible span{border-color:var(--card)}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.sc-ctrl{display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;margin:18px 0 0;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}
.sc-ctrl input[type=search]{max-width:300px;flex:1 1 240px}
.sc-chips{display:flex;flex-wrap:wrap;align-items:center;gap:6px}
.sc-lab{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.05em;color:var(--soft)}
.sc-chips button,#sc-reset{font:700 13px "Helvetica Neue",Helvetica,Arial,sans-serif;background:var(--card);color:var(--ink);border:2px solid var(--rule);padding:6px 10px;cursor:pointer;line-height:1}
.sc-chips button[aria-pressed=true]{background:var(--ink);color:var(--card)}
.sc-chips button:hover,#sc-reset:hover{color:var(--accent)}
.sc-chips button[aria-pressed=true]:hover{color:var(--card)}
#sc-reset{text-transform:uppercase;letter-spacing:.05em;font-size:12px}
.sc-count{margin:0;font-size:13px;color:var(--soft)}
table.sc th,table.sc td{padding:7px 8px}
table.sc th.c,table.sc td.c{text-align:center;width:1%;white-space:nowrap}
table.sc th button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer;text-transform:inherit;letter-spacing:inherit;display:inline-flex;align-items:baseline;gap:4px}
table.sc th button:hover{color:var(--accent)}
table.sc th button abbr{text-decoration:none;border-bottom:1px dotted var(--soft)}
table.sc th[aria-sort] button::after{content:"";font-size:10px;opacity:.55}
table.sc th[aria-sort=ascending] button::after{content:"▲";opacity:1}
table.sc th[aria-sort=descending] button::after{content:"▼";opacity:1}
table.sc tbody th{font-weight:400;text-align:left;text-transform:none;letter-spacing:0;font-size:14px;border-bottom:1px solid var(--hair);vertical-align:top;white-space:normal}
table.sc tbody th small{display:block;color:var(--soft);font-size:12.5px}
table.sc td.c b{font-weight:800;font-size:15px}
table.sc td.s{text-align:center;font-weight:900;font-size:15px;white-space:nowrap}
"""

NAV = [("index.html", "Results"), ("findings.html", "Findings"),
       ("comparisons.html", "Comparisons"),
       ("methodology.html", "Methodology"), ("reference.html", "Dose reference"),
       ("conflict-of-interest.html", "Conflict of interest")]


def page(path, title, desc, body, ctx, jsonld=None):
    depth = path.count("/")
    rel = "../" * depth
    cur = ' aria-current="page"'
    home = rel or "./"  # link the canonical "/" rather than /index.html
    nav = "".join(f'<a href="{home if h == "index.html" else rel + h}"{cur if h == path else ""}>{t}</a>'
                  for h, t in NAV)
    canon = f'<link rel="canonical" href="{SITE_URL}/{"" if path == "index.html" else path}">' if SITE_URL else ""
    # "</" is split so a string in the data can never close the script element early
    blob = json.dumps(jsonld).replace("</", "<\\/") if jsonld else ""
    ld = f'<script type="application/ld+json">{blob}</script>' if jsonld else ""
    social = (f'<meta property="og:url" content="{page_url(path)}">'
              f'<meta property="og:image" content="{SITE_URL}/{OG_IMAGE}">'
              f'<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
              f'<meta name="twitter:card" content="summary_large_image">'
              f'<meta name="twitter:image" content="{SITE_URL}/{OG_IMAGE}">') if SITE_URL else ""
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{canon}
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Supplement Facts Check">
<link rel="icon" href="{rel}favicon.ico" sizes="48x48"><link rel="icon" href="{rel}favicon.svg" type="image/svg+xml"><link rel="icon" href="{rel}favicon-48.png" type="image/png" sizes="48x48"><link rel="icon" href="{rel}favicon-192.png" type="image/png" sizes="192x192"><link rel="apple-touch-icon" href="{rel}apple-touch-icon.png">
{social}
<link rel="stylesheet" href="{rel}style.css">{ld}
{ANALYTICS}
</head><body>
<header class="site"><div class="wrap"><a class="brand" href="{home}">Supplement Facts Check</a><nav>{nav}</nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">
<p>Methodology v{ctx['ver']}, locked {ctx['locked']}. All data is public domain under
<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0 1.0</a>. Every figure on this site is generated from the
<a href="{REPO_URL}">public repository</a>, where the full commit history is the record.</p>
<p>Authored by Ryan Pepple, who owns a competing supplement brand. Read the
<a href="{rel}conflict-of-interest.html">conflict-of-interest statement</a>. This site reports what labels disclose.
It does not test products, and it is not medical advice.</p>
<a class="built" href="https://abovance.com/" rel="nofollow" title="Abovance, AI SEO and GEO. The author's consultancy."><span>Site built by</span><b>abovance</b></a>
</div></footer></body></html>"""
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")


def panel(row, rel="", link=True):
    items = ""
    for i, (key, label, _) in enumerate(CRITERIA, 1):
        v = row[key]
        cls, word = ("pass", "1 ✓") if v == "1" else ("fail", "0 ✗")
        items += f'<li><span>{i}. {e(label)}</span><b class="{cls}">{word}</b></li>'
    btn = f'<a class="btn" href="{rel}products/{slugify(row["product"])}.html">Why it scored this way →</a>' if link else ""
    return f"""<article class="panel">
<div class="t">Disclosure Facts</div>
<div class="p">{e(row['product'])}<small>{e(row['brand'])} · label captured {e(row['capture_date'])}</small></div>
<div class="score"><b>Disclosure score</b><span>{e(row['total_score'])}/6</span></div>
<ol>{items}</ol>
<div class="f">Each criterion scores 1 or 0. No weighting, no partial credit.</div>
{btn}
</article>"""


# ------------------------------------------------------------- comparisons
# A comparison page holds nothing of its own. Both columns, the verdict line and
# the per-criterion reasoning are read from the same two rows that render the two
# product pages, so a comparison cannot disagree with the pages it compares.


def compare_path(a, b):
    """URL for a pair: the two product-page slugs, joined by -vs-."""
    return f"compare/{slugify(a['product'])}-vs-{slugify(b['product'])}.html"


def compare_verdict(a, b, differ):
    """The one-line finding, derived from the two scores rather than written."""
    sa, sb = int(a["total_score"]), int(b["total_score"])
    if sa == sb:
        if differ:
            return (f"Both score {sa} out of 6, but not for the same reasons: they disclose different things, "
                    f"and differ on {len(differ)} of the six criteria.")
        return (f"Both score {sa} out of 6, and on the identical criteria. On label disclosure there is "
                f"nothing to choose between them.")
    hi, lo = (a, b) if sa > sb else (b, a)
    return (f"{hi['product']} discloses more: {max(sa, sb)} out of 6 against {min(sa, sb)}. "
            f"That is a statement about {lo['product']}'s label, not about the product.")


def criterion_rows(a, b):
    """Split the six criteria into the ones the pair differs on and the rest."""
    differ, agree = [], []
    for i, (key, label, desc) in enumerate(CRITERIA, 1):
        (differ if a[key] != b[key] else agree).append((i, key, label, desc))
    return differ, agree


def compare_page(a, b, others, ctx, ver):
    """Build one head-to-head page for a scored pair."""
    path = compare_path(a, b)
    pre_a, why_a = split_notes(a["notes"])
    pre_b, why_b = split_notes(b["notes"])
    differ, agree = criterion_rows(a, b)

    def mark(row, key):
        return ('<b class="pass">1 ✓</b>' if row[key] == "1" else '<b class="fail">0 ✗</b>')

    trs = "".join(
        f'<tr><td>{i}. {e(label)}<br><small style="color:var(--soft)">{e(desc)}</small></td>'
        f'<td class="n">{mark(a, key)}</td><td class="n">{mark(b, key)}</td>'
        f'<td class="muted">{"differ" if a[key] != b[key] else "same"}</td></tr>'
        for i, (key, label, desc) in enumerate(CRITERIA, 1))
    trs += (f'<tr><th>Disclosure score</th><th class="n">{e(a["total_score"])}/6</th>'
            f'<th class="n">{e(b["total_score"])}/6</th><th></th></tr>')

    def blocks(rows):
        out = ""
        for i, key, label, _ in rows:
            m = f'{e(a[key])} / {e(b[key])}'
            cls = "pass" if a[key] == b[key] == "1" else ("fail" if a[key] == b[key] == "0" else "")
            out += (f'<div class="why"><div class="m {cls}">{m}</div><div><b>{i}. {e(label)}</b>'
                    f'<p><b>{e(a["product"])}:</b> {e(why_a.get(i, "No reasoning recorded."))}</p>'
                    f'<p><b>{e(b["product"])}:</b> {e(why_b.get(i, "No reasoning recorded."))}</p></div></div>')
        return out

    links = "".join(
        f'<li><a href="{Path(compare_path(x, y)).name}">{e(x["product"])} vs {e(y["product"])}</a> '
        f'<span style="color:var(--soft)">({e(x["total_score"])}/6 vs {e(y["total_score"])}/6)</span></li>'
        for x, y in others)
    body = f"""
<p class="kicker" style="margin-top:40px">Head to head</p>
<h1 style="margin-top:8px;font-size:clamp(28px,4.6vw,44px)">{e(a['product'])} vs {e(b['product'])}</h1>
<p class="lede">{e(compare_verdict(a, b, differ))}</p>
<div class="note"><b class="sans">What this compares.</b> Six yes-or-no questions about what each label discloses,
scored under methodology v{ver} from dated screenshots of the two live labels
({e(a['product'])} captured {e(a['capture_date'])}, {e(b['product'])} captured {e(b['capture_date'])}).
A higher score means the label tells you more, not that the product works better. Neither product was lab-tested,
and nothing here is medical advice or a recommendation to buy either one.</div>

<h2>Side by side</h2>
<div class="tablewrap"><table>
<tr><th>Criterion</th><th>{e(a['product'])}</th><th>{e(b['product'])}</th><th>Agreement</th></tr>
{trs}
</table></div>

<h2>Where they differ</h2>
{f'<p class="lede" style="font-size:18px">The pair splits on {len(differ)} of the six criteria. The reasoning below is the same text that appears on each product page.</p>{blocks(differ)}' if differ else '<p class="prose">They do not differ on any criterion: both labels scored identically on all six. The reasoning for each is under “Where they agree” below.</p>'}

<h2>Where they agree</h2>
{f'<p class="lede" style="font-size:18px">Both labels were scored the same way on the remaining {len(agree)}.</p>{blocks(agree)}' if agree else '<p class="prose">Nothing: the two labels were scored differently on every one of the six criteria.</p>'}

<h2>The two scorecards</h2>
<div class="grid">{panel(a, '../')}{panel(b, '../')}</div>

<h2>Other comparisons</h2>
<ul class="prose">{links}</ul>
<p><a class="btn" href="../comparisons.html">All comparisons →</a> &nbsp;
<a class="btn" href="{RAW_URL}pilot-scores.csv">Both rows in the dataset →</a></p>
"""
    title = f"{a['product']} vs {b['product']}: label disclosure compared"
    desc = (f"{a['product']} scored {a['total_score']}/6 and {b['product']} scored {b['total_score']}/6 on label "
            f"disclosure. The six criteria side by side, with the reasoning for each.")
    # The comparison itself in machine-readable form: the two scores and the
    # pages they are argued on, so a reader does not have to parse the table.
    cmp_ld = {
        "@type": "ItemList", "@id": page_url(path) + "#comparison",
        "name": f"{a['product']} and {b['product']}: label disclosure scores",
        "description": desc, "numberOfItems": 2, "itemListOrder": "https://schema.org/ItemListUnordered",
        "about": {"@id": f"{SITE_URL}/#dataset"},
        "itemListElement": [
            {"@type": "ListItem", "position": i,
             "url": page_url(f"products/{slugify(r['product'])}.html"),
             "name": f"{r['product']} ({r['brand']}): {r['total_score']}/6"}
            for i, r in enumerate((a, b), 1)],
    }
    modified = max(a["capture_date"], b["capture_date"])
    page(path, title, desc, body, ctx,
         graph(website_node(),
               webpage_node(path, title, desc, main=page_url(path) + "#comparison", modified=modified),
               cmp_ld))
    return path, title


# Every scorecard links on to the rest of the sample, so no product page is a
# dead end. The groups are read off the data rather than hand-picked: brand and
# score come from the row, the format group comes from words in the product's
# own name, and "previous/next" follows the captured ranking.
FORMAT_GROUPS = [
    (r"\bkids\b|\bkids\+|\bchildren\b", "Also for children"),
    (r"\bgumm(y|ies)\b", "Also sold as gummies"),
    (r"\bchewable\b", "Also chewable"),
    (r"\bwomen'?s?\b", "Also marketed to women"),
    (r"\bmen'?s?\b", "Also marketed to men"),
]


def rel_list(rows, rel):
    """A list of links to other product pages, each with its score."""
    return "".join(
        f'<li><a href="{rel}products/{slugify(o["product"])}.html">{e(o["product"])}</a>'
        f'<b>{e(o["total_score"])}/6</b></li>' for o in rows)


def related(row, pilot, order, rel="../"):
    """The cross-link section at the foot of a product page."""
    me = slugify(row["product"])
    others = [o for o in pilot if slugify(o["product"]) != me]
    groups = []

    same_brand = [o for o in others if o["brand"] == row["brand"]]
    if same_brand:
        groups.append((f"Also from {e(row['brand'])}", same_brand))

    for pattern, heading in FORMAT_GROUPS:
        if re.search(pattern, row["product"], re.I):
            peers = [o for o in others if re.search(pattern, o["product"], re.I)]
            if peers:
                groups.append((heading, peers))

    same_score = [o for o in others if o["total_score"] == row["total_score"]]
    if same_score:
        groups.append((f"Also scored {e(row['total_score'])}/6", same_score))

    by_score = sorted(others, key=lambda o: int(o["total_score"]))
    ends = [o for o in (by_score[-1], by_score[0]) if o] if by_score else []
    seen, extremes = set(), []
    for o in ends:
        if slugify(o["product"]) not in seen:
            seen.add(slugify(o["product"]))
            extremes.append(o)
    if extremes:
        groups.append(("Elsewhere in the pilot", extremes))

    # A product with a brand, format and score all to itself would otherwise get
    # a thin section, so fall back to the scores either side of its own.
    linked = {slugify(o["product"]) for _, rows in groups for o in rows}
    if len(linked) < 3:
        near = [o for o in others
                if abs(int(o["total_score"]) - int(row["total_score"])) == 1
                and slugify(o["product"]) not in linked]
        if near:
            groups.append(("Scored a point either side", near))

    # de-duplicate within a group only: the same product can legitimately appear
    # under two headings, because each heading answers a different question.
    cards = "".join(f'<section><h3>{h}</h3><ul>{rel_list(rows, rel)}</ul></section>'
                    for h, rows in groups if rows)

    by_slug = {slugify(o["product"]): o for o in pilot}
    i = order.index(me)
    prev_row = by_slug[order[i - 1]] if i > 0 else None
    next_row = by_slug[order[i + 1]] if i + 1 < len(order) else None

    def link(o, prefix, suffix):
        return (f'<a href="{rel}products/{slugify(o["product"])}.html">{prefix}{e(o["product"])}{suffix}</a>'
                if o else "")
    nav = " · ".join(x for x in (
        link(prev_row, "← ", ""),
        f'<a href="{rel or "./"}">All {len(pilot)} scorecards</a>',
        link(next_row, "", " →")) if x)

    return f"""<h2>Compare with other products</h2>
<p class="prose">Groups are read from the dataset, not curated: the brand and the score come from this product's own
row, and the format group comes from words in its own name. A product can appear under more than one heading.</p>
<div class="rel">{cards}</div>
<p class="relnav"><span>In rank order in the captured sample:</span> {nav}</p>"""


SCORECARD_JS = """<script>
(function(){
  var table = document.getElementById("sc");
  var panel = document.getElementById("sc-controls");
  if (!table || !panel) return;
  var body = table.tBodies[0], rows = [].slice.call(body.rows);
  var q = document.getElementById("sc-q"), count = document.getElementById("sc-count");
  var chips = [].slice.call(panel.querySelectorAll("[data-crit]"));
  var heads = [].slice.call(table.tHead.rows[0].cells);
  panel.hidden = false;

  function val(row, i) {
    var cell = row.cells[i], n = cell.getAttribute("data-n");
    return n === null ? cell.textContent.trim().toLowerCase() : parseFloat(n);
  }
  function cmp(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  function sortBy(i, desc) {
    rows.slice().sort(function (a, b) {
      // Ties fall back to score, then product name, so the order is never arbitrary.
      return (desc ? -1 : 1) * cmp(val(a, i), val(b, i))
          || -cmp(val(a, 7), val(b, 7))
          || cmp(val(a, 0), val(b, 0));
    }).forEach(function (r) { body.appendChild(r); });
    heads.forEach(function (th, j) {
      th.setAttribute("aria-sort", j === i ? (desc ? "descending" : "ascending") : "none");
    });
  }
  heads.forEach(function (th, i) {
    var btn = th.querySelector("button");
    if (!btn) return;
    btn.addEventListener("click", function () {
      // Numbers open high-to-low, text A-to-Z; clicking the active column flips it.
      var active = th.getAttribute("aria-sort") !== "none";
      var desc = active ? th.getAttribute("aria-sort") === "ascending" : i !== 0;
      sortBy(i, desc);
    });
  });

  function apply() {
    var term = q.value.trim().toLowerCase();
    var want = chips.filter(function (c) { return c.getAttribute("aria-pressed") === "true"; })
                    .map(function (c) { return parseInt(c.getAttribute("data-crit"), 10); });
    var shown = 0;
    rows.forEach(function (r) {
      var ok = (!term || r.cells[0].textContent.toLowerCase().indexOf(term) > -1)
            && want.every(function (n) { return r.cells[n].getAttribute("data-n") === "1"; });
      r.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = shown === rows.length
      ? "Showing all " + rows.length + " products"
      : shown === 0
        ? "No product meets every filter you have set."
        : "Showing " + shown + " of " + rows.length + " products";
  }
  q.addEventListener("input", apply);
  chips.forEach(function (c) {
    c.addEventListener("click", function () {
      c.setAttribute("aria-pressed", c.getAttribute("aria-pressed") === "true" ? "false" : "true");
      apply();
    });
  });
  document.getElementById("sc-reset").addEventListener("click", function () {
    q.value = "";
    chips.forEach(function (c) { c.setAttribute("aria-pressed", "false"); });
    apply();
  });
})();
</script>"""


def scorecard(pilot):
    """The whole pilot as one table: 18 products by 6 criteria, sortable and filterable.

    Rendered pre-sorted by score, so the table is already useful with no JavaScript;
    the sort buttons and the filters are revealed by the script that drives them.
    """
    rows = sorted(pilot, key=lambda r: (-int(r["total_score"]), r["product"].lower()))
    trs = ""
    for r in rows:
        cells = ""
        for key, label, _ in CRITERIA:
            ok = r[key] == "1"
            cells += (f'<td class="c" data-n="{"1" if ok else "0"}">'
                      f'<b class="{"pass" if ok else "fail"}" aria-hidden="true">{"&#10003;" if ok else "&#10007;"}</b>'
                      f'<span class="sr">{"Yes" if ok else "No"}: {e(label)}</span></td>')
        trs += (f'<tr><th scope="row"><a href="products/{slugify(r["product"])}.html">{e(r["product"])}</a>'
                f'<small>{e(r["brand"])}</small></th>{cells}'
                f'<td class="s" data-n="{e(r["total_score"])}">{e(r["total_score"])}/6</td></tr>')
    chips = "".join(f'<button type="button" data-crit="{i}" aria-pressed="false" '
                    f'title="{e(label)}"><span aria-hidden="true">{i}</span>'
                    f'<span class="sr">Show only products that pass criterion {i}: {e(label)}</span></button>'
                    for i, (_, label, _) in enumerate(CRITERIA, 1))
    heads = "".join(f'<th class="c" scope="col" aria-sort="none"><button type="button">'
                    f'<abbr title="{e(label)}">{i}</abbr></button></th>'
                    for i, (_, label, _) in enumerate(CRITERIA, 1))
    return f"""<div class="sc-ctrl" id="sc-controls" hidden>
<label class="sr" for="sc-q">Filter products by name or brand</label>
<input type="search" id="sc-q" placeholder="Filter by product or brand">
<div class="sc-chips" role="group" aria-label="Show only products that pass a criterion">
<span class="sc-lab">Passes only</span>{chips}</div>
<button type="button" id="sc-reset">Reset</button>
<p class="sc-count" id="sc-count" aria-live="polite">Showing all {len(rows)} products</p>
</div>
<div class="tablewrap"><table class="sc" id="sc">
<caption class="sr">Every scored product with its result on each of the six criteria and its total out of 6.
Column headers sort the table; the numbered headers are criteria 1 to 6.</caption>
<thead><tr><th scope="col" aria-sort="none"><button type="button">Product</button></th>{heads}
<th class="c" scope="col" aria-sort="descending"><button type="button">Score</button></th></tr></thead>
<tbody>{trs}</tbody></table></div>
<p class="sc-count">Criteria, in column order: {"; ".join(f"{i}. {e(label)}" for i, (_, label, _) in enumerate(CRITERIA, 1))}.</p>
{SCORECARD_JS}"""


def md_section(readme, start, end=None):
    i = readme.index(start)
    j = readme.index(end, i) if end else len(readme)
    h = markdown.markdown(readme[i:j], extensions=["tables"])
    h = h.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    return h.replace("<hr />", "")


# ------------------------------------------------------------------ findings
# One page per criterion, stating how many of the scored products met it and
# listing every scored row as evidence. The headline sentence is composed from
# the counts at build time, so a page can never state a figure the CSV does not
# support: re-score a row and the wording changes with it.

FINDINGS = {
    "criterion_1_exact_dose_disclosed": {
        "slug": "exact-doses-disclosed",
        "met": "disclose an exact amount for every active ingredient",
        "short": "disclose an exact amount for every active ingredient",
        "missing": "the panel hides at least one active ingredient inside a proprietary blend",
    },
    "criterion_2_standardization_pct": {
        "slug": "standardization-percentage-stated",
        "met": "state the standardization percentage wherever potency depends on one",
        "short": "state the standardization percentage",
        "missing": "an ingredient whose potency depends on a percentage carries no percentage",
    },
    "criterion_3_chemical_form_named": {
        "slug": "chemical-form-or-strain-named",
        "met": "name the chemical form or probiotic strain of every active ingredient",
        "short": "name every chemical form or probiotic strain",
        "missing": "at least one organism or mineral is named without its strain or form",
    },
    "criterion_4_dose_within_trial_range": {
        "slug": "dose-within-clinical-trial-range",
        "met": "disclose a dose inside the range human trials used for the outcome claimed",
        "short": "disclose a dose inside the clinical trial range",
        "missing": "the disclosed dose falls outside the trial range, or no dose is disclosed to check",
    },
    "criterion_5_coa_publicly_accessible": {
        "slug": "public-third-party-certificate-of-analysis",
        "met": "publish a third-party certificate of analysis reachable with no email gate and no account",
        "short": "publish a publicly accessible third-party certificate of analysis",
        "missing": "a documented search found no publicly accessible third-party certificate",
    },
    "criterion_6_per_serving_amounts": {
        "slug": "per-serving-amounts-complete",
        "met": "state both the serving size and the servings per container",
        "short": "state both serving size and servings per container",
        "missing": "serving size or servings per container is absent from the panel",
    },
}


def count_phrase(k, n, cap=False):
    """'None', 'Just one', 'Only 3' or '12' — chosen from the count itself."""
    if k == 0:
        p = "none"
    elif k == 1:
        p = "just one"
    elif k * 2 < n:
        p = f"only {k}"
    else:
        p = str(k)
    return p[:1].upper() + p[1:] if cap else p


def agree(phrase, k):
    """Conjugate a plural verb phrase for a count: 'disclose' -> 'discloses' when k is 1."""
    if k != 1:
        return phrase
    verb, _, rest = phrase.partition(" ")
    verb += "es" if verb.endswith(("s", "sh", "ch", "x", "z", "o")) else "s"
    return (verb + " " + rest).strip()


def findings_pages(pilot, ctx, ver, locked):
    """Build findings.html and one page per criterion. Returns the hub's teaser HTML."""
    n = len(pilot)
    stats = []
    for i, (key, label, desc) in enumerate(CRITERIA, 1):
        f = FINDINGS[key]
        met = [r for r in pilot if r[key] == "1"]
        unmet = [r for r in pilot if r[key] != "1"]
        stats.append((i, key, label, desc, f, met, unmet))

    # starkest first: the fewest products meeting a criterion is the story
    ranked = sorted(stats, key=lambda s: (len(s[5]), s[0]))

    for i, key, label, desc, f, met, unmet in stats:
        k = len(met)
        headline = f"{count_phrase(k, n, cap=True)} of {n} best-selling gut supplements {agree(f['short'], k)}"
        sentence = (f"{count_phrase(k, n, cap=True)} of the {n} best-selling gut-health supplements audited by "
                    f"Supplement Facts Check {agree(f['met'], k)}.")
        rows = ""
        for r in sorted(pilot, key=lambda r: (r[key] == "1", -int(r["total_score"]), r["product"])):
            _, why = split_notes(r["notes"])
            ok = r[key] == "1"
            rows += (f'<tr><td><a href="../products/{slugify(r["product"])}.html">{e(r["product"])}</a>'
                     f'<br><small style="color:var(--soft)">{e(r["brand"])}</small></td>'
                     f'<td class="n {"pass" if ok else "fail"}">{"1 ✓" if ok else "0 ✗"}</td>'
                     f'<td class="n">{e(r["total_score"])}/6</td>'
                     f'<td>{e(why.get(i, "No reasoning recorded."))}</td>'
                     f'<td class="n muted">{e(r["capture_date"])}</td></tr>')
        others = (f"The other {len(unmet)} do not: {f['missing']}." if met and unmet
                  else (f"For all {n}, {f['missing']}." if not met
                        else "Every product scored met this criterion."))
        coa_caveat = ("""<div class="note"><b class="sans">What a 0 means here.</b> A 0 records that a documented
search — product page, brand site, site-scoped search and the retail listing — did not find a publicly accessible
third-party certificate on the date shown. That is a negative finding about public accessibility, not a claim that
no certificate exists or that a product is contaminated.</div>""" if key == "criterion_5_coa_publicly_accessible" else "")
        path = f"findings/{f['slug']}.html"
        body = f"""
<p class="kicker" style="margin-top:40px">Headline finding · criterion {i} of 6</p>
<h1 style="margin-top:8px;font-size:clamp(30px,5vw,52px)">{e(headline)}</h1>
<p class="lede">{e(sentence)} {e(others)}</p>
<div class="note"><b class="sans">The sample.</b> {n} products scored so far from the top 30 of Amazon’s Best
Sellers in Probiotic Nutritional Supplements, captured 09/26/2026. Every inclusion and exclusion decision is
listed on the <a href="../">results page</a>. Read these as pilot results, not a ranking.</div>
{coa_caveat}

<h2>Criterion {i}: {e(label)}</h2>
<p class="prose">{e(desc)} It scores 1 or 0, with no weighting and no partial credit, under methodology v{ver},
locked {locked}. <a href="../methodology.html">Read the full methodology →</a></p>

<h2>All {n} scored products</h2>
<p class="lede" style="font-size:18px">Every row that went into the figure above, with the reasoning recorded
for this criterion and the date the label was read. Each product links to its full scorecard and the dated
label captures the score was read from.</p>
<div class="tablewrap"><table>
<tr><th>Product</th><th>Criterion {i}</th><th>Total</th><th>Reasoning recorded for this criterion</th><th>Label captured</th></tr>
{rows}
</table></div>
<p><a class="btn" href="{RAW_URL}pilot-scores.csv">See these rows in the dataset →</a></p>

<h2>Citing this finding</h2>
<p class="prose">The sentence above is generated from the dataset at build time, so it cannot drift from the rows
listed on this page. Quote it as:</p>
<p class="note" style="max-width:46em">{e(sentence)} Supplement Facts Check, methodology v{ver},
labels captured {min(r['capture_date'] for r in pilot)} to {max(r['capture_date'] for r in pilot)}.
{SITE_URL}/{path}</p>
<p class="prose">The underlying data is public domain under CC0 1.0 and needs no permission to reuse. The
<a href="{REPO_URL}">repository</a> holds the scores, the rubric and the commit history of every ruling.
Corrections are welcome as <a href="{REPO_URL}/issues">issues</a>.</p>
<p><a class="btn" href="../findings.html">All headline findings →</a></p>
"""
        title = f"{headline} | Supplement Facts Check"
        pdesc = (f"{sentence} Every scored product is listed with the reasoning recorded for criterion {i} "
                 f"and the date its label was read.")
        finding_ld = {
            "@type": "Report", "@id": page_url(path) + "#finding",
            "headline": headline, "name": title, "description": pdesc, "abstract": sentence,
            "url": page_url(path), "inLanguage": "en", "datePublished": locked, "dateModified": locked,
            "author": AUTHOR, "publisher": AUTHOR, "license": LICENSE_URL,
            "about": {"@id": f"{SITE_URL}/#dataset"}, "isBasedOn": {"@id": f"{SITE_URL}/#dataset"},
            "variableMeasured": {"@type": "PropertyValue", "name": label, "description": desc,
                                 "value": f"{k} of {n}"},
        }
        list_ld = {
            "@type": "ItemList", "@id": page_url(path) + "#rows",
            "name": f"Criterion {i} result for every scored product", "numberOfItems": n,
            "itemListElement": [{"@type": "ListItem", "position": j,
                                 "url": page_url(f"products/{slugify(r['product'])}.html"),
                                 "name": f"{r['product']} ({r['brand']}): criterion {i} scored {r[key]}"}
                                for j, r in enumerate(pilot, 1)],
        }
        page(path, title, pdesc, body, ctx,
             graph(website_node(),
                   webpage_node(path, title, pdesc, main=page_url(path) + "#finding", modified=locked),
                   finding_ld, list_ld))

    cards = ""
    for i, key, label, desc, f, met, unmet in ranked:
        k = len(met)
        cards += (f'<div><b>{count_phrase(k, n, cap=True)} of {n} {e(agree(f["short"], k))}</b>'
                  f'<span>Criterion {i}: {e(label)}. '
                  f'<a href="findings/{f["slug"]}.html">See all {n} rows →</a></span></div>')
    hub_body = f"""
<p class="kicker" style="margin-top:40px">Headline findings</p>
<h1 style="margin-top:8px">What {n} best-selling gut supplement labels actually disclose</h1>
<p class="lede">Six yes-or-no criteria, {n} products scored so far. Each finding below has its own page listing
every scored row, the reasoning recorded against it and the date the label was read, so any figure here can be
checked against the evidence it came from.</p>
<div class="note"><b class="sans">Pilot stage.</b> The sample is the top 30 of Amazon’s Best Sellers in Probiotic
Nutritional Supplements, captured 09/26/2026. Every inclusion and exclusion decision is on the
<a href="./">results page</a>. These are pilot results, not a ranking, and no product was lab-tested.</div>
<div class="crit">{cards}</div>
<p style="margin-top:28px"><a class="btn" href="{RAW_URL}pilot-scores.csv">Download the scores as CSV →</a></p>
"""
    hub_title = f"Headline findings: what {n} gut supplement labels disclose | Supplement Facts Check"
    hub_desc = (f"The {n}-product pilot in six figures, one page per criterion, each listing every scored row "
                f"as evidence.")
    hub_ld = {
        "@type": "ItemList", "@id": page_url("findings.html") + "#findings",
        "name": "Headline findings", "numberOfItems": len(ranked),
        "itemListElement": [{"@type": "ListItem", "position": j,
                             "url": page_url(f"findings/{f['slug']}.html"),
                             "name": f"{count_phrase(len(met), n, cap=True)} of {n} {agree(f['short'], len(met))}"}
                            for j, (i, key, label, desc, f, met, unmet) in enumerate(ranked, 1)],
    }
    page("findings.html", hub_title, hub_desc, hub_body, ctx,
         graph(website_node(),
               webpage_node("findings.html", hub_title, hub_desc,
                            main=page_url("findings.html") + "#findings", modified=locked),
               hub_ld))

    top3 = "".join(
        f'<div><b>{count_phrase(len(met), n, cap=True)} of {n} {e(agree(f["short"], len(met)))}</b>'
        f'<span>Criterion {i}: {e(label)}. <a href="findings/{f["slug"]}.html">See all {n} rows →</a></span></div>'
        for i, key, label, desc, f, met, unmet in ranked[:3])
    llms = ["", "## Headline findings", ""] + [
        f"- {count_phrase(len(met), n, cap=True)} of {n} {agree(f['short'], len(met))}"
        f" (criterion {i}): {SITE_URL}/findings/{f['slug']}.html"
        for i, key, label, desc, f, met, unmet in ranked]
    return llms, f"""
<h2>Headline findings</h2>
<p class="lede" style="font-size:18px">The three starkest results from the {n} products scored so far. Each has its
own page listing every scored row as evidence.</p>
<div class="crit">{top3}</div>
<p><a class="btn" href="findings.html">All headline findings →</a></p>
"""


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ver, locked = version_and_status(readme)
    ctx = {"ver": ver, "locked": locked}
    pilot = [r for r in read_csv("pilot-scores.csv") if r["total_score"].strip()]
    sample = read_csv("sample.csv")
    n_inc = sum(1 for r in sample if r["included"].strip() == "1")
    n_exc = sum(1 for r in sample if r["included"].strip() == "0")
    n_pend = sum(1 for r in sample if r["included"].strip() == "pending")
    appendix = read_csv("appendix-scores.csv")
    doses = read_csv("clinical-doses.csv")
    (OUT / "style.css").write_text(CSS.strip(), encoding="utf-8")
    # static icons live in site/assets and are copied to the site root (docs/ is wiped on every build)
    for icon in sorted((ROOT / "site" / "assets").iterdir()):
        shutil.copy2(icon, OUT / icon.name)
    (OUT / ".nojekyll").write_text("")
    shutil.copy(ROOT / "site" / OG_IMAGE, OUT / OG_IMAGE)

    # integrity check: totals must equal the sum of the criteria
    for r in pilot:
        s = sum(int(r[k]) for k, _, _ in CRITERIA)
        assert s == int(r["total_score"]), f"{r['product']}: criteria sum {s} != total {r['total_score']}"

    # captures, downsized for the web
    capdir = OUT / "captures"
    capdir.mkdir()
    caps = {}
    for p in sorted((ROOT / "captures").glob("*.png")):
        im = Image.open(p).convert("RGB")
        if im.width > 1400:
            im = im.resize((1400, round(im.height * 1400 / im.width)))
        name = p.stem + ".jpg"
        im.save(capdir / name, "JPEG", quality=82, optimize=True)
        caps[p.name] = (name, im.width, im.height)

    # --------------------------------------------------------- findings
    findings_llms, findings_teaser = findings_pages(pilot, ctx, ver, locked)

    # ------------------------------------------------------------ home
    n = len(pilot)
    no_blend = sum(r[CRITERIA[0][0]] == "1" for r in pilot)
    no_coa = sum(r[CRITERIA[4][0]] == "0" for r in pilot)
    in_range = sum(r[CRITERIA[3][0]] == "1" for r in pilot)
    top = max(int(r["total_score"]) for r in pilot)
    scored_line = (f"All {n_inc} eligible products are scored." if n == n_inc
                   else f"{n} of {n_inc} eligible products are scored so far.")
    _rank_src = "amazon-probiotics-bestsellers-top30-2026-09-26.png"
    if _rank_src in caps:
        _n, _w, _h = caps[_rank_src]
        rank_fig = (
            f'<figure><a href="captures/{_n}"><img loading="lazy" src="captures/{_n}" width="{_w}" height="{_h}" '
            f'alt="Amazon Best Sellers in Probiotic Nutritional Supplements, ranks 1 to 30, captured 09/26/2026."></a>'
            f'<figcaption>The ranking the sample was taken from, captured 09/26/2026. '
            f'<a href="{RAW_URL}captures/{_rank_src}">Original file</a></figcaption></figure>')
    else:
        rank_fig = ""
    _mark = {"1": '<span class="pass">included</span>', "0": '<span class="fail">excluded</span>',
              "pending": "undecided"}
    # a scored row in the sample table links to its scorecard: the table is the
    # site's fullest list of products, so it should also be a way into them.
    scored_slugs = {slugify(r["product"]) for r in pilot}

    def sample_name(r):
        sl = slugify(r["product"])
        return (f'<a href="products/{sl}.html">{e(r["product"])}</a>'
                if sl in scored_slugs else e(r["product"]))

    sample_rows = "".join(
        f'<tr><td class="n">{r["rank"]}</td><td>{sample_name(r)}<br><small style="color:var(--soft)">{e(r["brand"])}</small></td>'
        f'<td>{_mark.get(r["included"].strip(), "")}</td>'
        f'<td class="muted">{"scored " + r["scored_in"].split(".")[0].replace("pilot-scores", "") if r["scored_in"].strip() else ("not scored yet" if r["included"].strip() == "1" else "")}</td></tr>'
        for r in sample)
    sample_rows = sample_rows.replace("scored  ", "scored")
    crit = "".join(f"<div><b>{i}. {e(l)}</b><span>{e(d)}</span></div>" for i, (_, l, d) in enumerate(CRITERIA, 1))
    body = f"""
<p class="kicker" style="margin-top:40px">An independent audit of gut-health supplement labels</p>
<h1 style="margin-top:8px">Most gut supplements make the same claims. Few tell you what is in the bottle.</h1>
<p class="lede">Supplement Facts Check scores best-selling gut-health supplements on six yes-or-no questions about
what their labels disclose: the exact doses, the specific forms, and whether any of it can be verified. The rubric
was committed in public before any product data was collected, and every ruling made since is in the commit history.</p>
<div class="note"><b class="sans">Pilot stage.</b> {scored_line} The full sample is
the top 30 of Amazon’s Best Sellers in Probiotic Nutritional Supplements as captured on 09/26/2026, listed in full below
with every inclusion decision. Read these as pilot results, not a ranking.</div>

<h2>Pilot results</h2>
<p class="lede" style="font-size:18px">Of {n} products scored, {no_blend} disclosed an exact amount for every active
ingredient, a dose inside a published trial range could be confirmed for {in_range}, and a public third-party
certificate of analysis could not be located for {no_coa}. The highest score was {top} out of 6.</p>
{scorecard(pilot)}

<h3>Every scorecard in full</h3>
<div class="grid">{''.join(panel(r) for r in pilot)}</div>
{findings_teaser}
<h2>The sample</h2>
<p class="lede" style="font-size:18px">All {len(sample)} products in the captured ranking, in rank order.
{n_inc} pass the inclusion test, {n_exc} are excluded, {n_pend} are undecided. Exclusions stay visible: a sample
is only auditable if the rejections are shown alongside the acceptances.</p>
<div class="tablewrap"><table>
<tr><th>#</th><th>Product</th><th>Inclusion</th><th>Status</th></tr>
{sample_rows}
</table></div>
<p class="prose" style="font-size:15px">Full reasoning for every decision, including the exclusion reason on each
excluded row, is in <a href="{REPO_URL}/blob/main/sample.csv">sample.csv</a>.</p>
{rank_fig}

<h2>The six criteria</h2>
<p>Each one scores 1 or 0. The maximum is 6. A product using a generic ingredient at a studied dose scores the same
as one using a trademarked equivalent; price, taste and brand reputation are not scored at all.</p>
<div class="crit">{crit}</div>
<p><a class="btn" href="methodology.html">Read the full methodology →</a></p>

<h2>Check the work</h2>
<p class="prose">Every score links to a dated screenshot of the label it was read from. Every dose range links to the
trial it came from on PubMed. The dataset, the rubric and every revision to either are in a
<a href="{REPO_URL}">public repository</a>, released into the public domain. If a score is wrong, the evidence to
show it is one click away, and <a href="{REPO_URL}/issues">corrections are welcome</a>.</p>
<p class="prose">The author owns a supplement brand that competes with products scored here. That is stated plainly, along with
what was done about it, in the <a href="conflict-of-interest.html">conflict-of-interest statement</a>.</p>
"""
    dataset_ld = {
        "@type": "Dataset", "@id": f"{SITE_URL}/#dataset",
        "name": "Supplement Facts Check",
        "description": "An independent audit of dose disclosure on gut-health supplement labels, scoring products "
                       "on six binary criteria. Includes a reference table of clinical trial dose ranges with PubMed IDs.",
        "license": LICENSE_URL, "creator": AUTHOR, "publisher": AUTHOR,
        "version": ver, "isAccessibleForFree": True, "url": SITE_URL, "sameAs": REPO_URL,
        "dateModified": locked, "inLanguage": "en",
        "measurementTechnique": "Manual reading of the Supplement Facts panel and product listing from a dated "
                                "screenshot capture of the live label, scored against a rubric committed to public "
                                "version control before any product data was collected.",
        "variableMeasured": [{"@type": "PropertyValue", "name": label, "description": desc}
                             for _, label, desc in CRITERIA],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                          "contentUrl": f"{REPO_URL}/raw/main/{f}"}
                         for f in ("pilot-scores.csv", "clinical-doses.csv", "sample.csv")],
        "creditText": "Supplement Facts Check (supplementfactscheck.org), CC0 1.0",
    }
    results_ld = {
        "@type": "ItemList", "@id": f"{SITE_URL}/#pilot-results",
        "name": "Pilot results: label disclosure scores", "numberOfItems": n,
        "itemListElement": [{"@type": "ListItem", "position": i,
                             "url": page_url(f"products/{slugify(r['product'])}.html"),
                             "name": f"{r['product']} ({r['brand']}): {r['total_score']}/6"}
                            for i, r in enumerate(pilot, 1)],
    }
    title = "Supplement Facts Check: what gut-health labels disclose"
    desc = ("Independent open-data audit scoring best-selling gut-health supplements on six yes-or-no "
            "dose disclosure questions. Rubric locked before scoring.")
    page("index.html", title, desc, body, ctx,
         graph(website_node(), webpage_node("index.html", title, desc, main=f"{SITE_URL}/#dataset",
                                           modified=locked),
               dataset_ld, results_ld))

    # ------------------------------------------------------------ products
    # Scorecards are walked in the order of the captured ranking, so "previous"
    # and "next" on a product page mean the same thing as the sample table.
    sample_rank = {slugify(x["product"]): int(x["rank"]) for x in sample}
    order = sorted((slugify(r["product"]) for r in pilot),
                   key=lambda sl: (sample_rank.get(sl, 10 ** 6), sl))
    for r in pilot:
        pre, why = split_notes(r["notes"])
        slug = slugify(r["product"])
        rows = ""
        for i, (key, label, _) in enumerate(CRITERIA, 1):
            ok = r[key] == "1"
            rows += (f'<div class="why"><div class="m {"pass" if ok else "fail"}">{r[key]}</div><div>'
                     f'<b>{i}. {e(label)}</b><p>{e(why.get(i, "No reasoning recorded."))}</p></div></div>')
        srcs = [src for src in caps
                if src in r["notes"] or src.startswith(slug_prefix(r, caps))]
        figs = ""
        for src in sorted(srcs, key=capture_date):
            name, w, h = caps[src]
            view = "Supplement Facts panel" if "-panel-" in src else "Product listing"
            # Each capture is dated from its own filename, not from the row: a
            # re-capture pass adds files without restating when the score was read.
            when = capture_date(src) or r["capture_date"]
            later = " (later capture, after this score was read)" if when > r["capture_date"] else ""
            figs += (f'<figure><a href="../captures/{name}"><img loading="lazy" src="../captures/{name}" width="{w}" '
                     f'height="{h}" alt="{e(view)} of {e(r["product"])}, captured {e(when)}"></a>'
                     f'<figcaption>{view}, captured {e(when)}{later}. '
                     f'<a href="{RAW_URL}captures/{src}">Original file</a></figcaption></figure>')
        body = f"""
<p class="kicker" style="margin-top:40px">Pilot scorecard</p>
<h1 style="margin-top:8px;font-size:clamp(30px,5vw,48px)">{e(r['product'])}</h1>
<p class="lede">{e(r['brand'])} scored <b>{e(r['total_score'])} out of 6</b> for label disclosure under methodology
v{ver}, read from the label as captured on {e(r['capture_date'])}.</p>
<div style="max-width:440px">{panel(r, '../', link=False)}</div>
<h2>Why it scored this way</h2>
{f'<p><i>{e(pre)}</i></p>' if pre else ''}
{rows}
<h2>The evidence</h2>
<p class="prose">Scores are read from the live label, captured by screenshot on the date shown. A score describes
what the label discloses. It says nothing about whether the product works, and nothing here was lab-tested.</p>
{'' if 'Product listing' in figs else '<div class="note"><b class="sans">Incomplete evidence.</b> No product-listing capture is on file for this product yet. Under the methodology, a scored row without both captures is incomplete.</div>'}
<div class="caps">{figs or '<p>No captures on file.</p>'}</div>
<p><a class="btn" href="{RAW_URL}pilot-scores.csv">See this row in the dataset →</a></p>
{related(r, pilot, order)}
"""
        path = f"products/{slug}.html"
        title = f"{r['product']}: label score {r['total_score']}/6"
        desc = (f"{r['product']} scored {r['total_score']} of 6 on label disclosure. See the reasoning for "
                f"each criterion and the dated label captures.")
        images = capture_nodes(r, srcs, caps)
        page(path, title, desc, body, ctx,
             graph(website_node(),
                   webpage_node(path, title, desc, main=page_url(path) + "#review",
                                modified=r["capture_date"], image=images[0] if images else None),
                   *review_node(r, pre, why, path, images)))

    # ------------------------------------------------------------ comparisons
    by_name = {r["product"]: r for r in pilot}
    pairs = []
    for name_a, name_b in COMPARISONS:
        # A pair naming a product that is not scored is a bug in the list above,
        # not a page to skip quietly: the build stops rather than ship a gap.
        for name in (name_a, name_b):
            assert name in by_name, f"comparison names unscored product: {name!r}"
        pairs.append((by_name[name_a], by_name[name_b]))

    cmp_pages = []
    for a, b in pairs:
        # Pairs sharing a product with this one are the useful next click, so
        # they lead the in-page list; the rest follow in the order declared.
        rest = [(x, y) for x, y in pairs if (x, y) != (a, b)]
        shared = [pr for pr in rest if a in pr or b in pr]
        others = shared + [pr for pr in rest if pr not in shared]
        cmp_pages.append((compare_page(a, b, others, ctx, ver), a, b))

    cmp_rows = "".join(
        f'<tr><td><a href="{e(path)}">{e(a["product"])} vs {e(b["product"])}</a></td>'
        f'<td class="n">{e(a["total_score"])}/6</td><td class="n">{e(b["total_score"])}/6</td>'
        f'<td class="muted">{len(criterion_rows(a, b)[0])} of 6</td></tr>'
        for (path, _), a, b in cmp_pages)
    body = f"""
<p class="kicker" style="margin-top:40px">Head to head</p>
<h1 style="margin-top:8px">Comparisons</h1>
<p class="lede">{len(cmp_pages)} head-to-head pages, each one putting two scored labels side by side on the same six
criteria. Every figure on them is read from the same two rows as the two product pages, so a comparison cannot
disagree with the pages it compares.</p>
<div class="note"><b class="sans">What a comparison does not say.</b> A higher score means the label discloses more,
not that the product is better or that it works. Nothing here was lab-tested, and no product on this site is
recommended over another. Only products scored in the pilot can be compared, so a pair a shopper might want is
missing whenever one of the two is not yet scored.</div>
<div class="tablewrap"><table>
<tr><th>Comparison</th><th>Score</th><th>Score</th><th>Criteria they differ on</th></tr>
{cmp_rows}
</table></div>
<p class="prose">Pairs are taken from the ranking the sample was drawn from: products near each other in the
top 30, the two highest scorers, the drugstore shelf neighbours, two of one brand’s own formulas, the two
children’s products and the two gummies. The full sample, including the {n_exc} excluded products, is on the
<a href="./">results page</a>.</p>
<p><a class="btn" href="methodology.html">How the six criteria are applied →</a></p>
"""
    title = "Probiotic label comparisons | Supplement Facts Check"
    desc = (f"{len(cmp_pages)} head-to-head comparisons of best-selling probiotic labels, scored on the same six "
            f"dose-disclosure criteria, with the reasoning for every ruling.")
    hub_ld = {
        "@type": "ItemList", "@id": page_url("comparisons.html") + "#comparisons",
        "name": "Label disclosure comparisons", "numberOfItems": len(cmp_pages),
        "description": desc, "about": {"@id": f"{SITE_URL}/#dataset"},
        "itemListElement": [{"@type": "ListItem", "position": i, "url": page_url(path), "name": t}
                            for i, ((path, t), _, _) in enumerate(cmp_pages, 1)],
    }
    page("comparisons.html", title, desc, body, ctx,
         graph(website_node(),
               webpage_node("comparisons.html", title, desc,
                            main=page_url("comparisons.html") + "#comparisons", modified=locked),
               hub_ld))

    # ------------------------------------------------------------ methodology
    body = f"""<p class="kicker" style="margin-top:40px">Version {ver} · locked {locked}</p>
<h1 style="margin-top:8px">Methodology</h1>
<p class="lede">This page is generated from the repository’s README, which is the governing text. Every change
to it is in the <a href="{REPO_URL}/commits/main/README.md">commit history</a>.</p>
<div class="prose">{md_section(readme, "### Scoring rubric", "### Conflict of interest")}</div>"""
    title = f"Methodology v{ver} | Supplement Facts Check"
    desc = ("The six-criterion rubric, how each criterion is applied, how the sample was chosen, and what was "
            "deliberately left out.")
    method_ld = {
        "@type": "TechArticle", "@id": page_url("methodology.html") + "#article",
        "headline": f"Supplement Facts Check methodology v{ver}", "name": title, "description": desc,
        "version": ver, "datePublished": locked, "dateModified": locked,
        "author": AUTHOR, "publisher": AUTHOR, "license": LICENSE_URL,
        "url": page_url("methodology.html"), "inLanguage": "en",
        "about": {"@id": f"{SITE_URL}/#dataset"},
        "sameAs": f"{REPO_URL}/blob/main/README.md",
    }
    page("methodology.html", title, desc, body, ctx,
         graph(website_node(),
               webpage_node("methodology.html", title, desc,
                            main=page_url("methodology.html") + "#article", modified=locked),
               method_ld))

    # ------------------------------------------------------------ COI
    coi = md_section(readme, "### Conflict of interest", "## Repository contents").replace("<h3>Conflict of interest</h3>", "")
    # The author's own brand is linked once, here, and passes no ranking signal:
    # a followed link from an audit to a site its author sells from would be the
    # self-dealing this page exists to disclose.
    coi = coi.replace('<a href="https://shuven.co">', '<a href="https://shuven.co" rel="nofollow">')
    coi = coi.replace('<a href="https://abovance.com">', '<a href="https://abovance.com" rel="nofollow">')
    scored_app = [a for a in appendix if a["total_score"].strip()]
    if scored_app:
        app_html = f'<div class="grid">{"".join(panel(a) for a in scored_app)}</div>'
    else:
        parts = []
        for a in appendix:
            note = a["notes"].strip()
            parts.append(f"{e(a['product'])} — {e(note)}" if note else e(a["product"]))
        names = "; ".join(parts) or "none listed"
        app_html = (f"<p>Author-owned products on file: {names}</p>"
                    f"<p>When scored, they will be shown here by the identical rubric, never in the ranked results.</p>")
    body = f"""<h1>Conflict of interest</h1><div class="prose">{coi}</div>
<h2>Appendix: the author’s own products</h2><div class="prose">{app_html}</div>"""
    title = "Conflict of interest | Supplement Facts Check"
    desc = ("The author owns a competing supplement brand. What that means for this audit and what was done "
            "about it.")
    # The disclosure in machine-readable form: anything citing this audit can read
    # the competing interest off the page instead of having to find the prose.
    coi_ld = {
        "@type": "WebPage", "@id": page_url("conflict-of-interest.html") + "#page",
        "url": page_url("conflict-of-interest.html"), "name": title, "description": desc,
        "isPartOf": {"@id": f"{SITE_URL}/#website"}, "license": LICENSE_URL, "author": AUTHOR,
        "about": {"@id": f"{SITE_URL}/#dataset"},
        "disambiguatingDescription": "The author of this audit, Ryan Pepple, owns CalmGut (operating as SHUVEN), "
                                     "a gut-brain axis supplement brand whose products compete with products "
                                     "scored here. Author-owned products are excluded from the ranked results and "
                                     "scored in a physically separate appendix file using the identical rubric. "
                                     "The rubric was committed to public version control before any product data "
                                     "was collected.",
        "mentions": [{"@type": "Brand", "name": "CalmGut", "alternateName": "SHUVEN"}],
    }
    page("conflict-of-interest.html", title, desc, body, ctx, graph(website_node(), coi_ld))

    # ------------------------------------------------------------ reference
    trs = ""
    for d in doses:
        lo, hi, unit = d["dose_low"].strip(), d["dose_high"].strip(), d["unit"].strip()
        if lo and hi and lo != hi:
            rng = f"{lo}–{hi} {unit}"
        elif lo and hi:
            rng = f"{lo} {unit}"
        elif lo:
            rng = f"≥ {lo} {unit}"
        else:
            rng = "No range set"
        pm = d["pmid"].strip()
        link = f'<a href="https://pubmed.ncbi.nlm.nih.gov/{e(pm)}/">{e(pm)}</a>' if pm else "—"
        clean, caveat = source_caveat(d)
        text = (clean or d["outcome_measured"]) + (" " + d["notes"] if d["notes"].strip() else "")
        flag = (f'<span class="cav"><b>Unresolved problem in the source.</b> {e(caveat)}</span>'
                if caveat else "")
        trs += (f'<tr><td class="n">{e(d["ingredient"])}</td><td>{e(d["form"])}</td>'
                f'<td class="n{"" if lo else " muted"}">{e(rng)}</td><td>{e(text)}{flag}</td>'
                f'<td class="n">{link}</td></tr>')
    flagged = [(d, source_caveat(d)[1]) for d in doses if source_caveat(d)[1]]
    with_range = sum(1 for d in doses if d["dose_low"].strip())
    body = f"""<h1>Dose reference table</h1>
<p class="lede">Criterion 4 checks a label’s dose against the range human trials actually used for the outcome the
product claims. This is that table: {len(doses)} rows, {with_range} with a range set. Rows without one record why,
including the date the literature was searched.</p>
<p><input type="search" id="q" placeholder="Filter by ingredient, form or outcome" aria-label="Filter the table"></p>
<div class="tablewrap"><table id="t"><thead><tr><th>Ingredient</th><th>Form</th><th>Daily range</th>
<th>Outcome measured, and basis</th><th>PubMed ID</th></tr></thead><tbody>{trs}</tbody></table></div>
<p><a class="btn" href="{RAW_URL}clinical-doses.csv">Download the CSV →</a></p>

<h2>Known limitations</h2>
<p class="prose">A dose range is only as good as the paper it came from. Where a source turned out to contain a
problem that could not be resolved from its full text, the problem is recorded against the row rather than quietly
dropped, and the row stays in the table so the judgment can be checked. {len(doses) - with_range} of
{len(doses)} rows have no range set at all; each one records why, and criterion 4 cannot be scored from them.</p>
{"".join(f'''<div class="why"><div class="m fail">!</div><div><b>{e(d["ingredient"])} ({e(d["form"])}) — PMID
<a href="https://pubmed.ncbi.nlm.nih.gov/{e(d["pmid"].strip())}/">{e(d["pmid"].strip())}</a></b>
<p>{e(cav)}</p></div></div>''' for d, cav in flagged) or "<p>No source on file currently carries an unresolved problem.</p>"}
<script>const q=document.getElementById('q'),rows=[...document.querySelectorAll('#t tbody tr')];
q.addEventListener('input',()=>{{const s=q.value.toLowerCase();rows.forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(s))}});</script>"""
    title = "Clinical dose reference table | Supplement Facts Check"
    desc = ("Human-trial dose ranges for common gut-health supplement ingredients, each tied to the outcome "
            "measured and a PubMed ID.")
    pmids = sorted({d["pmid"].strip() for d in doses if d["pmid"].strip()})
    doses_ld = {
        "@type": "Dataset", "@id": page_url("reference.html") + "#dose-reference",
        "name": "Clinical dose reference table", "description": desc,
        "url": page_url("reference.html"), "license": LICENSE_URL,
        "creator": AUTHOR, "publisher": AUTHOR, "isAccessibleForFree": True,
        "dateModified": locked, "inLanguage": "en", "isPartOf": {"@id": f"{SITE_URL}/#dataset"},
        "variableMeasured": [{"@type": "PropertyValue", "name": v} for v in
                             ("ingredient", "form", "daily dose range", "outcome measured", "PubMed ID")],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                          "contentUrl": f"{REPO_URL}/raw/main/clinical-doses.csv"}],
        "citation": [{"@type": "ScholarlyArticle", "@id": f"https://pubmed.ncbi.nlm.nih.gov/{p}/",
                      "url": f"https://pubmed.ncbi.nlm.nih.gov/{p}/",
                      "identifier": {"@type": "PropertyValue", "propertyID": "PMID", "value": p}}
                     for p in pmids],
        "disambiguatingDescription":
            f"{len(doses) - with_range} of {len(doses)} rows have no dose range set, each recording why; "
            f"criterion 4 cannot be scored from those. {len(flagged)} row(s) carry an unresolved problem found "
            f"in the source paper itself, stated on the page against the row: "
            + " ".join(f"{d['ingredient']} ({d['form']}), PMID {d['pmid'].strip()}." for d, _ in flagged),
    }
    page("reference.html", title, desc, body, ctx,
         graph(website_node(),
               webpage_node("reference.html", title, desc,
                            main=page_url("reference.html") + "#dose-reference", modified=locked),
               doses_ld))

    # ------------------------------------------------------------ llms.txt, sitemap
    lines = ["# Supplement Facts Check", "",
             "> An independent, open-data audit of dose disclosure on gut-health supplement labels. Six binary "
             f"criteria, 0-6 scale. Methodology v{ver}, locked {locked}. Sample: the top 30 of Amazon's Best Sellers in "
             f"Probiotic Nutritional Supplements captured 09/26/2026; {n_inc} pass the inclusion test, {n_exc} are excluded "
             f"as not gut-health-first, {n_pend} undecided. {scored_line} "
             "Authored by Ryan Pepple, who owns a competing brand (CalmGut, operating as SHUVEN); author-owned "
             "products are scored separately and never ranked.", "", "## Pilot scores", ""]
    lines += [f"- {r['product']} ({r['brand']}): {r['total_score']}/6, label captured {r['capture_date']}" for r in pilot]
    lines += ["", "## Comparisons", "",
              "Head-to-head pages, each comparing two scored labels on the same six criteria. "
              "A higher score means the label discloses more, not that the product works better."]
    lines += [f"- {a['product']} ({a['total_score']}/6) vs {b['product']} ({b['total_score']}/6): "
              f"{SITE_URL}/{path}" for (path, _), a, b in cmp_pages]
    lines += findings_llms
    lines += ["", "## Known limitations", "",
              f"- {len(doses) - with_range} of {len(doses)} dose-reference rows have no range set; each records "
              "why, and criterion 4 cannot be scored from them.",
              "- Criterion 5 records a certificate of analysis as not publicly accessible when a documented search "
              "failed to find one. That is a negative finding, not a claim that none exists.",
              "- Scores describe what a label discloses on the capture date. Nothing here was lab-tested, and no "
              "claim is made about whether a product works."]
    lines += [f"- Source problem, {d['ingredient']} ({d['form']}), PMID {d['pmid'].strip()}: {cav}"
              for d, cav in flagged]
    lines += ["", "## Data", "", f"- Repository: {REPO_URL}", f"- Scores: {REPO_URL}/raw/main/pilot-scores.csv",
              f"- Dose reference: {REPO_URL}/raw/main/clinical-doses.csv", "- License: CC0 1.0", ""]
    (OUT / "llms.txt").write_text("\n".join(lines), encoding="utf-8")
    if SITE_URL:
        urls = [p.relative_to(OUT).as_posix() for p in sorted(OUT.rglob("*.html"))]
        sm = "".join(f"<url><loc>{SITE_URL}/{'' if u == 'index.html' else u}</loc></url>" for u in urls)
        (OUT / "sitemap.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>')
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
        (OUT / "CNAME").write_text(SITE_URL.split("//", 1)[1] + "\n")
    print(f"Built {len(list(OUT.rglob('*.html')))} pages into {OUT.relative_to(ROOT)}/ (methodology v{ver})")


def slug_prefix(row, caps):
    """Match captures to a product by the longest shared filename prefix."""
    s = slugify(row["brand"] + " " + row["product"])
    best = ""
    for src in caps:
        stem = re.sub(r"-(panel|listing)-\d{4}-\d{2}-\d{2}\.png$", "", src)
        if all(tok in s for tok in stem.split("-")) and len(stem) > len(best):
            best = stem
    return best or "\0"


if __name__ == "__main__":
    build()
