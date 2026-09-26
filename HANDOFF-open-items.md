# Open items before the pilot can be called complete

Recorded 2026-09-21. Nothing below was filled in by guesswork: each item needs
evidence that only the 09/05/2026 ranking capture or a fresh screenshot can supply.

1. ~~`sample.csv` rank column is blank~~ Resolved 2026-09-26. The 09/05/2026
   capture was never taken; searched the repository, both clones, Desktop,
   Downloads, Pictures (including the Photos originals) and the Trash, and no such
   file exists. The sample was re-captured on 09/26/2026 and committed at
   `captures/amazon-probiotics-bestsellers-top30-2026-09-26.png`. All 30 ranks are
   filled from it.
2. ~~ASINs are blank on every row~~ Resolved 2026-09-26 from the ranking capture.
   Physician's CHOICE B079H53D2B (#1), Seed DS-01 B0CMJR4XGR (#4), BIOMA
   B0F5J1XZHC (#15). The Seed candidate recorded here was correct and is now
   confirmed against the capture rather than inferred.
3. ~~Seed DS-01 listing capture.~~ Resolved 2026-09-21: `captures/seed-ds-01-listing-2026-09-07.png` committed; inclusion test applied in `sample.csv`.
4. ~~`appendix-scores.csv`: SHUVEN Reset is unscored.~~ Resolved 2026-09-22:
   SHUVEN Reset has no current live production label — pages are in draft,
   sellable launch gated on trademark resolution. Per methodology, only
   products with a current live label are scored. Row left unscored, `notes`
   field updated with that status, conflict-of-interest page now surfaces it
   instead of a blanket "Not yet scored."
5. ~~L-glutamine >30 g/d row carries its own warning...~~ Resolved 2026-09-22:
   full text checked (PMID 39397201, PMC11471693). 30 g/day confirmed correct
   via Methods, Table 1, and Table 2's per-study doses; the source paper's own
   Discussion/Conclusion repeat the "30 mg/day" error, not just the abstract.
   CI inconsistency on the subgroup statistic remains unresolved -- no fix
   available from full text. A second, separate duration-subgroup mismatch
   found in the same paper, noted in clinical-doses.csv.
6. **Domain.** supplementfactscheck.org (Cloudflare DNS). `SITE_URL` is set in `site/build.py`; the build writes canonical tags, `sitemap.xml`, `robots.txt` and `CNAME`.
7. **Publishing.** Repo Settings -> Pages -> Deploy from a branch -> `main`, `/docs`.

8. **Four inclusion decisions are undecided** (added 2026-09-26). Ranks 7 and 18
   turn on whether the literal first-listed test or the "fundamentally about
   something else" test governs when they conflict; they are mirror images and
   must be ruled on together. Ranks 20 and 25 carry no benefit phrase in the title
   and need the primary-bullet test applied from a listing capture, per the
   precedent set at rank 4. All four are marked `pending` in `sample.csv`.
