
## Home facts (`data/home-facts.json`)

The same file in the homes repo. The generator (`scripts/seo_pages.py`) reads it when it
writes each listing. Prices, down payment, monthly payment and status stay in `homes.js`
from the portal sync and never go in this file. A missing value means "Aún no se sabe"
(English: "Not yet known"). Condition rows are seeded only from `contractor` notes that
name the system. Status on those rows is `reported`, never `verified`.

```json
{"version": 1, "updated": "YYYY-MM-DD",
 "homes": {"<home id>": {
   "condition": {"furnace|plumbing|electrical|roof|foundation":
      {"status": "verified|reported|unknown", "en": "...", "es": "...", "source": "...", "as_of": "YYYY-MM-DD"}},
   "fit": {"family_en": null, "family_es": null, "rental_en": null, "rental_es": null}}}}
```

Interest rate, taxes, insurance, closing costs, what the monthly payment covers, and
deed-transfer timing are not stored and are not shown. Cash before the keys is the
down payment already in `homes.js`.

`data/stories.json` is the only source for buyer stories. An entry needs `en`, `es`,
`source`, `consent_date` and `verified_by`. `"placeholder": true` renders only with
`?preview=1`.

ZIP search loads `data/zip-centroids.json` after a 5-digit value is typed. It is the
Census 2023 ZCTA gazetteer (public domain), limited to the states that have homes.

## Excluded homes (junk / duplicate ids)
`data/excluded-homes.json` (same file as in the homes repo; keep both in step) lists site ids that
must never be on the site. `scripts/excluded_homes.py` enforces it from `scripts/build_casas.py`
(Mac layout pass; also reads the sibling homes clone's list) and from the homes repo's
`portal_sync.py` (daily sync). Each run removes the id from homes.js and sitemap.xml and leaves
`<id>.html` as a redirect to `/`.
