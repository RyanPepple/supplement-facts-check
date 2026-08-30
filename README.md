# Supplement Facts Check

An independent audit of dose disclosure on gut-health supplement labels.

- **Status:** Methodology locked. Data collection not yet begun.
- **Author:** Ryan Pepple
- **Methodology version:** 1.2 — locked 2026-08-30

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

## Methodology v1.2

### Scoring rubric

Each product is scored 0 or 1 on each of six criteria. No weighting, no
partial credit. Maximum score: 6.

| # | Criterion | Scores 1 when |
|---|-----------|---------------|
| 1 | Exact amount disclosed for every active ingredient | No proprietary blend appears anywhere on the Supplement Facts panel |
| 2 | Standardization percentage stated where potency depends on it | e.g. % withanolides, % curcuminoids |
| 3 | Specific chemical form named | "Magnesium glycinate," not "magnesium" |
| 4 | Disclosed dose falls within the trial range for the outcome the product claims | Cross-checked against `clinical-doses.csv` |
| 5 | Third-party certificate of analysis publicly accessible | No email gate, no account required |
| 6 | Amounts stated per serving, with serving size and servings per container both visible | Both figures present on the panel |
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

**Probiotics.** Clinical trials of probiotic strains report dosing
predominantly in milligrams of preparation rather than colony-forming
units, while product labels almost universally report CFU. These units are
not reliably interconvertible, as CFU per milligram varies by manufacturer
and by viability at manufacture versus expiry. Probiotic ingredients are
therefore excluded from criterion 4 and assessed on criteria 1, 2, 3, 5
and 6 only.

### Criteria deliberately excluded

The following were considered and rejected as scoring criteria:

- **Use of branded or trademarked ingredients.** Would reward marketing
  spend rather than transparency. A product using generic ashwagandha at a
  clinically studied dose scores identically to one using a branded
  equivalent.
- **Price or value.** Not a transparency measure.
- **Taste, packaging, brand reputation.** Subjective.

### Sample selection

[TO BE FINALIZED — stated rule, fixed date, applied without exception]

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

### Conflict of interest

This project is authored by Ryan Pepple, who has a commercial interest in
the dietary supplement category. Mitigations:

- The rubric was written and committed to version control before any
  product data was collected. The commit history in this repository is the
  record.
- No criterion rewards any attribute specific to the author's own products.
- Products in which the author has a commercial interest are excluded from
  the ranking and scored separately in an appendix, using the identical
  rubric.

---

## Repository contents

| File | Contents |
|------|----------|
| `README.md` | This methodology |
| `clinical-doses.csv` | Reference table: ingredient, form, trial dose range, PubMed ID |
| `labels-raw.csv` | One row per ingredient per product, as captured |
| `scores.csv` | One row per product, scored per criterion |

_(Data files added as collection proceeds.)_

---

## License

All data in this repository is released under
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) —
public domain. No attribution required, though it is appreciated.

## Suggested citation

Pepple, R. (2026). *Supplement Facts Check: an audit of dose disclosure on
gut-health supplement labels.* Version 1.2.
https://github.com/RyanPepple/supplement-facts-check
