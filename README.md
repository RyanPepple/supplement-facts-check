# Supplement Facts Check

An independent audit of dose disclosure on gut-health supplement labels.

**Status:** Methodology locked. Data collection not yet begun.
**Author:** Ryan Pepple 
**Methodology version:** 1.0 — locked 08/30/2026

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

## Methodology v1.0

### Scoring rubric

Each product is scored 0 or 1 on each of six criteria. No weighting, no
partial credit. Maximum score: 6.

| # | Criterion | Scores 1 when |
|---|-----------|---------------|
| 1 | Exact amount disclosed for every active ingredient | No proprietary blend appears anywhere on the Supplement Facts panel |
| 2 | Standardization percentage stated where potency depends on it | e.g. % withanolides, % curcuminoids |
| 3 | Specific chemical form named | "Magnesium glycinate," not "magnesium" |
| 4 | Disclosed dose falls within published human-trial range | Cross-checked against the reference table in this repository |
| 5 | Third-party certificate of analysis publicly accessible | No email gate, no account required |
| 6 | Amounts stated per serving, with serving size and servings per container both visible | Both figures present on the panel |

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
gut-health supplement labels.* Version 1.0.
https://github.com/RyanPepple/supplement-facts-check
