# Supplement Facts Check

An independent audit of dose disclosure on gut-health supplement labels.

- **Status:** Methodology locked. Pilot scoring under way; full data
  collection not yet begun.
- **Author:** Ryan Pepple
- **Methodology version:** 1.6 — locked 2026-09-07

---

## What this is

Most gut-health supplements make similar claims. Far fewer disclose what
is actually in the bottle, in what amount, and in what form.

This project scores a fixed sample of gut-health supplement products
against six binary criteria covering dose disclosure, ingredient
specificity, and third-party verification. Every product is scored by the
same rubric. The rubric was finalized before any product data was
collected.

The complete dataset is published alongside the findings so that anyone
can reproduce, check, or dispute the results.

---

## Methodology v1.6

### Scoring rubric

Each product is scored 0 or 1 on each of six criteria. No weighting, no
partial credit. Maximum score: 6.

| # | Criterion | Scores 1 when |
|---|-----------|---------------|
| 1 | Exact amount disclosed for every active ingredient | No proprietary blend appears anywhere on the Supplement Facts panel |
| 2 | Standardization percentage stated where potency depends on it | e.g. % withanolides, % curcuminoids |
| 3 | Specific chemical form named, or strain designation for live organisms | "Magnesium glycinate," not "magnesium"; "*L. rhamnosus* GG," not "*L. rhamnosus*" |
| 4 | Disclosed dose falls within the trial range for the outcome the product claims | Cross-checked against `clinical-doses.csv` |
| 5 | Third-party certificate of analysis publicly accessible | No email gate, no account required |
| 6 | Amounts stated per serving, with serving size and servings per container both visible | Both figures present on the panel |

### How criterion 2 is applied

Criterion 2 applies only where potency depends on a marker compound:
standardized herbal or botanical extracts (e.g., % withanolides,
% curcuminoids). Products containing no such ingredient are not
penalized for its absence. Criterion 2 scores 1 by default when
nothing in the formula requires a stated percentage.

Unlike the probiotic exclusion under criterion 4, this is not a
unit-mismatch problem; the requirement simply does not apply. The
criterion therefore remains a scored point rather than reducing the
total possible score, keeping every product comparable on the same
6-point scale.

### How criterion 3 is applied

Criterion 3 asks whether the specific chemical form is named, because the
form determines what the body actually receives. "Magnesium glycinate"
scores 1; "magnesium" scores 0.

**Probiotics.** The equivalent of chemical form for a live microorganism is
the strain designation. Probiotic effects are strain-specific and do not
generalize across a species: *Lactobacillus rhamnosus* GG has been trialled
for outcomes that other *L. rhamnosus* strains have not, and evidence for
one *Bifidobacterium longum* strain is not evidence for another. A label
naming only genus and species does not identify what is in the bottle, and
the published literature cannot be matched to it.

Criterion 3 therefore scores 1 for a probiotic product only when every
listed organism carries a strain designation — for example
*Lactobacillus rhamnosus* GG or *Bifidobacterium longum* 35624. Genus and
species alone — "*Lactobacillus acidophilus*" — scores 0, and a single
undesignated organism anywhere in the formula is enough to score 0. A
strain designation means a specific identifier assigned by a culture
depositary or the manufacturer, not a marketing name for a blend.

This rule governs the criterion 3 point only. Probiotics remain excluded
from criterion 4 for the separate unit-mismatch reason given below.

### How criterion 4 is applied

Clinical dose ranges are outcome-specific. Glutamine trials measuring
intestinal permeability and glutamine trials measuring IBS symptom
severity used different doses; zinc carnosine trials for permeability and
for gastric ulcer healing used different doses. There is no single
"clinical dose" for most ingredients.

Criterion 4 is therefore scored against the outcome the product claims on
its label or product page. A product marketed for intestinal permeability
is scored against permeability trials. A product marketed for symptom
relief is scored against symptom trials.

Where the literature is contested, the reference table records the range
and the disagreement in the notes field, and the product is given the
benefit of the doubt: falling within any credible published range for the
claimed outcome scores 1.

Where no adequate human trial exists for an ingredient at all, that
ingredient is marked "no adequate human trial identified" and excluded
from the product's criterion 4 assessment. A product scores 0 on
criterion 4 only if at least one of its actives has a reference range and
falls outside it.

**Human trials only.** Animal and in vitro studies are excluded from the
reference table. Criterion 4 requires published human-trial evidence for
the claimed outcome. An ingredient with substantial preclinical support
but no human trial is treated as having no reference range.

**Positive-outcome trials only.** Reference dose ranges are drawn from
trials that found a significant effect on the outcome measured. Trials
that found no effect are recorded in the notes field but do not set the
range. A dose shown not to work is not evidence that the dose is correct.

**Absorption enhancers.** Ingredients included to increase the
bioavailability of other ingredients rather than to produce an
independent effect are excluded from criterion 4. Their doses are
recorded in the reference table where trials state them, but no trial
tests them against the outcome the product claims.

**Probiotics.** Clinical trials of probiotic strains report dosing
predominantly in milligrams of preparation rather than colony-forming
units, while product labels almost universally report CFU. These units are
not reliably interconvertible, as CFU per milligram varies by manufacturer
and by viability at manufacture versus expiry. Probiotic ingredients are
therefore excluded from criterion 4 and assessed on criteria 1, 2, 3, 5
and 6 only.

### How criterion 5 is applied

Criterion 5 asks whether a third-party certificate of analysis for the
product is publicly accessible: reachable without an email address, an
account, or a support request. A batch-number lookup that returns a
certificate scores 1, provided no email or account is required to use it.

Three things are not a certificate of analysis:

- A "third-party tested" claim, badge, or seal with no document behind it.
  The criterion is about the document being accessible, not the claim being
  made.
- A GMP or facility registration certificate, which covers the
  manufacturing site rather than the product.
- A certificate issued by the manufacturer's own laboratory, which is not
  third-party.

**A zero is a negative finding and is recorded as one.** The search covers
the product page, the brand site (footer links commonly named Quality,
Testing, Lab Results, Transparency, or Certificate of Analysis), a
site-scoped web search for "certificate of analysis", and the retail
listing's images. Where that search returns nothing, the row records that
no publicly accessible certificate was *located* on the capture date — not
that none exists. A certificate published later, or reachable by a route
this search did not cover, would change the score, and the dated record
makes that revision auditable rather than silent.

### Criteria deliberately excluded

The following were considered and rejected as scoring criteria:

- **Use of branded or trademarked ingredients.** Would reward marketing
  spend rather than transparency. A product using generic ashwagandha at a
  clinically studied dose scores identically to one using a branded
  equivalent.
- **Price or value.** Not a transparency measure.
- **Taste, packaging, brand reputation.** Subjective.

### Sample selection

The top 30 gut-health supplements ranked in Amazon Best Sellers in Probiotic Nutritional Supplements,
captured on 09/05/2026. This list
is fixed at capture and not revised as rankings change afterward.

A product is included only if the digestive/gut-health benefit is the
first-listed claim in its product title or primary bullet. Products
whose first-listed claim is vaginal/urinary tract health, oral/dental
health, or an unrelated function (e.g., pre-alcohol support) are
excluded, even if digestive support is mentioned secondarily. This test
is applied to every product in the category ranking, in rank order,
without exception.

### Data sources

Primary: the NIH Office of Dietary Supplements
[Dietary Supplement Label Database](https://dsld.od.nih.gov) (DSLD).

Important limitations of DSLD, stated openly:

- Manufacturer submission is voluntary, so coverage is incomplete.
- The database contains both on-market and off-market products.
- NIH does not verify that label information conforms to FDA requirements.

Accordingly, every scored product is verified against its current live
label, captured by screenshot with a capture date recorded. Where the live
label differs from the DSLD record, the live label governs and the
discrepancy is noted in the dataset.

Products that cannot be verified against a current label are excluded
from scoring.

Label captures are stored in `captures/`, named
`<brand>-<product>-<view>-<YYYY-MM-DD>.png`, where `<view>` is `panel`
for the Supplement Facts panel or `listing` for the product page carrying
the claims that criterion 4 is scored against. Both views are captured for
each product, and the same date is recorded in the `capture_date` field of
the row that cites them. A scored row without a
corresponding capture is incomplete, not merely undocumented.

### Conflict of interest

This project is authored by Ryan Pepple, who owns CalmGut (operating as
SHUVEN), a gut-brain axis supplement brand. CalmGut/SHUVEN products
compete directly with several products scored in this report. Mitigations:

- The rubric was written and committed to version control before any
  product data was collected. The commit history in this repository is the
  record.
- No criterion rewards any attribute specific to the author's own products.
- Products in which the author has a commercial interest are excluded from
  the ranking and scored separately in an appendix, using the identical
  rubric. The appendix is a physically separate file
  (`appendix-scores.csv`, and `appendix-*.csv` for the full run) sharing
  the ranked file's header, so no ranking, mean, or count computed over
  the ranked data can include an author-owned product without a deliberate
  choice to combine the two files.

---

## Repository contents

| File | Contents |
|------|----------|
| `README.md` | This methodology |
| `clinical-doses.csv` | Reference table: ingredient, form, trial dose range, unit, outcome measured, PubMed ID |
| `pilot-scores.csv` | Pilot scoring worksheet: one row per ranked product, scored per criterion |
| `captures/` | Label captures backing every scored row: Supplement Facts panel and product listing per product |
| `appendix-scores.csv` | Same rubric, same columns, for products in which the author has a commercial interest — kept out of the ranked file so they cannot be aggregated into it by accident |

Planned, not yet created:

| File | Contents |
|------|----------|
| `labels-raw.csv` | One row per ingredient per product, as captured |
| `scores.csv` | One row per product in the full sample, scored per criterion |

_(Data files added as collection proceeds.)_

---

## License

All data in this repository is released under
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) —
public domain. No attribution required, though it is appreciated.

## Suggested citation

Pepple, R. (2026). *Supplement Facts Check: an audit of dose disclosure on
gut-health supplement labels.* Version 1.6.
https://github.com/RyanPepple/supplement-facts-check
