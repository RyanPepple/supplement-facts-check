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


def version_and_status(readme):
    ver = re.search(r"\*\*Methodology version:\*\*\s*([\d.]+)\s*—\s*locked\s*([\d-]+)", readme)
    return (ver.group(1), ver.group(2)) if ver else ("", "")


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
nav a{margin-right:18px;font-size:14px;font-weight:700;text-decoration:none;text-transform:uppercase;letter-spacing:.04em}
nav a:last-child{margin-right:0}nav a[aria-current]{text-decoration:underline;text-decoration-thickness:2px}
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
input[type=search]{font:16px "Helvetica Neue",Helvetica,Arial,sans-serif;width:100%;max-width:420px;padding:10px 12px;border:2px solid var(--rule);background:var(--card);color:var(--ink)}
.why{display:grid;grid-template-columns:auto 1fr;gap:6px 18px;border-bottom:1px solid var(--hair);padding:16px 0;max-width:52em}
.why .m{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-weight:900;font-size:26px;line-height:1}
.why b{font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}.why p{margin:4px 0 0;font-size:16px}
figure{margin:20px 0;max-width:520px}figure img{max-width:100%;height:auto;border:2px solid var(--rule);background:#fff}
figcaption{font-size:14px;color:var(--soft);font-family:"Helvetica Neue",Helvetica,Arial,sans-serif}
.caps{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
footer{margin-top:80px;border-top:6px solid var(--rule);font-size:14px;color:var(--soft)}
footer .wrap{padding-top:18px;padding-bottom:40px}footer a{color:var(--soft)}
"""

NAV = [("index.html", "Results"), ("methodology.html", "Methodology"),
       ("reference.html", "Dose reference"), ("conflict-of-interest.html", "Conflict of interest")]


def page(path, title, desc, body, ctx, jsonld=None):
    depth = path.count("/")
    rel = "../" * depth
    cur = ' aria-current="page"'
    nav = "".join(f'<a href="{rel}{h}"{cur if h == path else ""}>{t}</a>' for h, t in NAV)
    canon = f'<link rel="canonical" href="{SITE_URL}/{"" if path == "index.html" else path}">' if SITE_URL else ""
    ld = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
{canon}
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<link rel="stylesheet" href="{rel}style.css">{ld}
</head><body>
<header class="site"><div class="wrap"><a class="brand" href="{rel}index.html">Supplement Facts Check</a><nav>{nav}</nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap">
<p>Methodology v{ctx['ver']}, locked {ctx['locked']}. All data is public domain under
<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0 1.0</a>. Every figure on this site is generated from the
<a href="{REPO_URL}">public repository</a>, where the full commit history is the record.</p>
<p>Authored by Ryan Pepple, who owns a competing supplement brand. Read the
<a href="{rel}conflict-of-interest.html">conflict-of-interest statement</a>. This site reports what labels disclose.
It does not test products, and it is not medical advice.</p>
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


def md_section(readme, start, end=None):
    i = readme.index(start)
    j = readme.index(end, i) if end else len(readme)
    h = markdown.markdown(readme[i:j], extensions=["tables"])
    h = h.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    return h.replace("<hr />", "")


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    ver, locked = version_and_status(readme)
    ctx = {"ver": ver, "locked": locked}
    pilot = [r for r in read_csv("pilot-scores.csv") if r["total_score"].strip()]
    appendix = read_csv("appendix-scores.csv")
    doses = read_csv("clinical-doses.csv")
    (OUT / "style.css").write_text(CSS.strip(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")

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

    # ------------------------------------------------------------ home
    n = len(pilot)
    no_blend = sum(r[CRITERIA[0][0]] == "1" for r in pilot)
    no_coa = sum(r[CRITERIA[4][0]] == "0" for r in pilot)
    top = max(int(r["total_score"]) for r in pilot)
    crit = "".join(f"<div><b>{i}. {e(l)}</b><span>{e(d)}</span></div>" for i, (_, l, d) in enumerate(CRITERIA, 1))
    body = f"""
<p class="kicker" style="margin-top:40px">An independent audit of gut-health supplement labels</p>
<h1 style="margin-top:8px">Most gut supplements make the same claims. Few tell you what is in the bottle.</h1>
<p class="lede">Supplement Facts Check scores best-selling gut-health supplements on six yes-or-no questions about
what their labels disclose: the exact doses, the specific forms, and whether any of it can be verified. The rubric
was committed in public before any product data was collected, and every ruling made since is in the commit history.</p>
<div class="note"><b class="sans">Pilot stage.</b> {n} products are scored so far, to test the rubric. The full sample is
the top 30 of Amazon’s Best Sellers in Probiotic Nutritional Supplements as captured on 09/05/2026, and scoring of
that sample has not started. Read these as pilot results, not a ranking.</div>

<h2>Pilot results</h2>
<p class="lede" style="font-size:18px">Of {n} products scored, {no_blend} disclosed an exact amount for every active
ingredient, and a public third-party certificate of analysis could not be located for {no_coa}. The highest score was {top} out of 6.</p>
<div class="grid">{''.join(panel(r) for r in pilot)}</div>

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
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Supplement Facts Check",
        "description": "An independent audit of dose disclosure on gut-health supplement labels, scoring products "
                       "on six binary criteria. Includes a reference table of clinical trial dose ranges with PubMed IDs.",
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "creator": {"@type": "Person", "name": "Ryan Pepple"},
        "version": ver, "isAccessibleForFree": True, "url": SITE_URL or REPO_URL, "sameAs": REPO_URL,
        "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv",
                          "contentUrl": f"{REPO_URL}/raw/main/{f}"}
                         for f in ("pilot-scores.csv", "clinical-doses.csv", "sample.csv")],
    }
    page("index.html", "Supplement Facts Check: what gut-health supplement labels actually disclose",
         "An independent, open-data audit scoring best-selling gut-health supplements on six yes-or-no questions "
         "about dose disclosure. Rubric locked before scoring. All data public domain.", body, ctx, dataset_ld)

    # ------------------------------------------------------------ products
    for r in pilot:
        pre, why = split_notes(r["notes"])
        slug = slugify(r["product"])
        rows = ""
        for i, (key, label, _) in enumerate(CRITERIA, 1):
            ok = r[key] == "1"
            rows += (f'<div class="why"><div class="m {"pass" if ok else "fail"}">{r[key]}</div><div>'
                     f'<b>{i}. {e(label)}</b><p>{e(why.get(i, "No reasoning recorded."))}</p></div></div>')
        figs = ""
        for src, (name, w, h) in caps.items():
            if src in r["notes"] or src.startswith(slug_prefix(r, caps)):
                view = "Supplement Facts panel" if "-panel-" in src else "Product listing"
                figs += (f'<figure><a href="../captures/{name}"><img loading="lazy" src="../captures/{name}" width="{w}" '
                         f'height="{h}" alt="{e(view)} of {e(r["product"])}, captured {e(r["capture_date"])}"></a>'
                         f'<figcaption>{view}, captured {e(r["capture_date"])}. '
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
"""
        page(f"products/{slug}.html", f"{r['product']}: label disclosure score {r['total_score']}/6",
             f"{r['product']} scored {r['total_score']} of 6 on dose and label disclosure. See the reasoning for "
             f"each criterion and the dated label capture behind it.", body, ctx)

    # ------------------------------------------------------------ methodology
    body = f"""<p class="kicker" style="margin-top:40px">Version {ver} · locked {locked}</p>
<h1 style="margin-top:8px">Methodology</h1>
<p class="lede">This page is generated from the repository’s README, which is the governing text. Every change
to it is in the <a href="{REPO_URL}/commits/main/README.md">commit history</a>.</p>
<div class="prose">{md_section(readme, "### Scoring rubric", "### Conflict of interest")}</div>"""
    page("methodology.html", f"Methodology v{ver} | Supplement Facts Check",
         "The six-criterion rubric, how each criterion is applied, how the sample was chosen, and what was "
         "deliberately left out.", body, ctx)

    # ------------------------------------------------------------ COI
    coi = md_section(readme, "### Conflict of interest", "## Repository contents").replace("<h3>Conflict of interest</h3>", "")
    scored_app = [a for a in appendix if a["total_score"].strip()]
    if scored_app:
        app_html = f'<div class="grid">{"".join(panel(a) for a in scored_app)}</div>'
    else:
        names = ", ".join(e(a["product"]) for a in appendix) or "none listed"
        app_html = (f"<p>Author-owned products on file: {names}. <b>Not yet scored.</b> When they are, they will be "
                    f"scored by the identical rubric and shown here, never in the ranked results.</p>")
    body = f"""<h1>Conflict of interest</h1><div class="prose">{coi}</div>
<h2>Appendix: the author’s own products</h2><div class="prose">{app_html}</div>"""
    page("conflict-of-interest.html", "Conflict of interest | Supplement Facts Check",
         "The author owns a competing supplement brand. What that means for this audit and what was done about it.",
         body, ctx)

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
        text = d["outcome_measured"] + (" " + d["notes"] if d["notes"].strip() else "")
        trs += (f'<tr><td class="n">{e(d["ingredient"])}</td><td>{e(d["form"])}</td>'
                f'<td class="n{"" if lo else " muted"}">{e(rng)}</td><td>{e(text)}</td><td class="n">{link}</td></tr>')
    with_range = sum(1 for d in doses if d["dose_low"].strip())
    body = f"""<h1>Dose reference table</h1>
<p class="lede">Criterion 4 checks a label’s dose against the range human trials actually used for the outcome the
product claims. This is that table: {len(doses)} rows, {with_range} with a range set. Rows without one record why,
including the date the literature was searched.</p>
<p><input type="search" id="q" placeholder="Filter by ingredient, form or outcome" aria-label="Filter the table"></p>
<div class="tablewrap"><table id="t"><thead><tr><th>Ingredient</th><th>Form</th><th>Daily range</th>
<th>Outcome measured, and basis</th><th>PubMed ID</th></tr></thead><tbody>{trs}</tbody></table></div>
<p><a class="btn" href="{RAW_URL}clinical-doses.csv">Download the CSV →</a></p>
<script>const q=document.getElementById('q'),rows=[...document.querySelectorAll('#t tbody tr')];
q.addEventListener('input',()=>{{const s=q.value.toLowerCase();rows.forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(s))}});</script>"""
    page("reference.html", "Clinical dose reference table | Supplement Facts Check",
         "Human-trial dose ranges for common gut-health supplement ingredients, each tied to the outcome measured "
         "and a PubMed ID.", body, ctx)

    # ------------------------------------------------------------ llms.txt, sitemap
    lines = ["# Supplement Facts Check", "",
             "> An independent, open-data audit of dose disclosure on gut-health supplement labels. Six binary "
             f"criteria, 0-6 scale. Methodology v{ver}, locked {locked}. Pilot stage: {n} products scored. "
             "Authored by Ryan Pepple, who owns a competing brand (CalmGut, operating as SHUVEN); author-owned "
             "products are scored separately and never ranked.", "", "## Pilot scores", ""]
    lines += [f"- {r['product']} ({r['brand']}): {r['total_score']}/6, label captured {r['capture_date']}" for r in pilot]
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
