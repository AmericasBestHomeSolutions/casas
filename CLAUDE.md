
## Excluded homes (junk / duplicate ids)
`data/excluded-homes.json` (same file as in the homes repo; keep both in step) lists site ids that
must never be on the site. `scripts/excluded_homes.py` enforces it from `scripts/build_casas.py`
(Mac layout pass; also reads the sibling homes clone's list) and from the homes repo's
`portal_sync.py` (daily sync). Each run removes the id from homes.js and sitemap.xml and leaves
`<id>.html` as a redirect to `/`.
