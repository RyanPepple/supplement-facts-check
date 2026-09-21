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
3. ~~Seed DS-01 listing capture~~ Resolved 2026-09-21: `captures/seed-ds-01-listing-2026-09-07.png` committed; inclusion applied in `sample.csv`.
   inclusion test has not been applied from evidence. Needs
   `captures/seed-ds-01-listing-<date>.png`. The site flags this on Seed's page
   automatically and drops the flag once the capture exists.
4. **`appendix-scores.csv`: SHUVEN Reset is unscored.** The methodology excludes
   products that cannot be verified against a current live label. Decide whether
   Reset has a label that qualifies yet; if not, the honest entry is "not scored:
   no production label" rather than a score from a formula sheet.
5. **L-glutamine >30 g/d row** carries its own warning that the source abstract
   is internally inconsistent and should be checked against the full text before
   it scores any product. Still open.
6. **Domain.** supplementfactscheck.org (Cloudflare DNS). `SITE_URL` is set in `site/build.py`; the build writes canonical tags, `sitemap.xml`, `robots.txt` and `CNAME`.
7. **Publishing.** Repo Settings -> Pages -> Deploy from a branch -> `main`, `/docs`.
