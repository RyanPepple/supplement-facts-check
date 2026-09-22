# Open items before the pilot can be called complete

Recorded 2026-09-21. Nothing below was filled in by guesswork: each item needs
evidence that only the 09/05/2026 ranking capture or a fresh screenshot can supply.

1. **`sample.csv` rank column is blank for all three rows.** Each row says
   "Rank pending from the 09/05/2026 ranking capture", and that capture is not in
   the repository. Commit it to `captures/` and fill the ranks from it. Until it
   is committed, the claim that the list was fixed at capture cannot be checked.
2. **ASINs are blank on every row.** The ASIN has to be the one that held the
   rank in the capture. Seed alone has several live listings, so it cannot be
   inferred. Candidates only, to be confirmed against the ranking capture:
   - Seed DS-01, "30-Days with Jar": B0CMJR4XGR. The committed panel capture shows
     "Style: 30-Day Starter", which is consistent with this listing.
   - Seed DS-01, "30-Day Refill": B0G99WQ4PG. "60-Day Refill": B0G99BV4K9.
3. ~~Seed DS-01 listing capture.~~ Resolved 2026-09-21: `captures/seed-ds-01-listing-2026-09-07.png` committed; inclusion test applied in `sample.csv`.
4. ~~`appendix-scores.csv`: SHUVEN Reset is unscored.~~ Resolved 2026-09-22:
   SHUVEN Reset has no current live production label — pages are in draft,
   sellable launch gated on trademark resolution. Per methodology, only
   products with a current live label are scored. Row left unscored, `notes`
   field updated with that status, conflict-of-interest page now surfaces it
   instead of a blanket "Not yet scored."
5. **L-glutamine >30 g/d row** carries its own warning that the source abstract
   is internally inconsistent and should be checked against the full text before
   it scores any product. Still open.
6. **Domain.** supplementfactscheck.org (Cloudflare DNS). `SITE_URL` is set in `site/build.py`; the build writes canonical tags, `sitemap.xml`, `robots.txt` and `CNAME`.
7. **Publishing.** Repo Settings -> Pages -> Deploy from a branch -> `main`, `/docs`.
