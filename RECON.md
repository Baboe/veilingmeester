# RECON.md — Step 0 Findings: onlineveilingmeester.nl

**Date**: 2026-06-16  
**Method**: WebFetch, WebSearch, robots.txt, sitemap.xml analysis  
**Status**: Initial recon complete. Phase 2 (live Playwright probe) required before scraper code is final.

---

## 1. Site architecture

**Critical finding: Full JavaScript SPA. Static HTML scraping is impossible.**

Every URL — homepage, lot listings, lot detail pages, category pages, API guesses — returns
an identical HTML shell:

```html
<title>AuctionMaster.com | Explore our auctions. Secure your winning bid.</title>
<!-- body: empty div, all content injected by JS bundle -->
```

BeautifulSoup will see only this shell on every request. **Playwright is mandatory.**
The Apify template to use is `apify/python-playwright` (Crawlee for Python).

The platform is branded as both **onlineveilingmeester.nl** (Dutch) and
**auctionmaster.com** (English/international). Both domains serve the same application.

---

## 2. URL structure (confirmed from sitemap_nl.xml and search results)

| Page type | URL pattern |
|---|---|
| Auction session (Dutch) | `/nl/veilingen/{auction_id}` |
| Auction session (English) | `/en/auctions/{auction_id}` |
| All lots in a session (Dutch) | `/nl/veilingen/{auction_id}/kavels` |
| All lots in a session (English) | `/en/auctions/{auction_id}/lots` |
| Individual lot (Dutch) | `/nl/veilingen/{auction_id}/kavels/{lot_id}` |
| Individual lot (English) | `/en/auctions/{auction_id}/lots/{lot_id}` |
| Category listing (Dutch) | `/nl/c/{category-slug}/?categorie={category_id}` |
| Subcategory | `/nl/c/{parent}/{sub-slug}/?categorie={sub_id}` |

Auction IDs in sitemap range from ~8106 to ~9198 (as of June 2026), suggesting ~1000+
auction sessions total. Only active auctions matter for this project.

---

## 3. Robots.txt — critical rules

```
User-agent: *
Crawl-delay: 10

Disallow: /nl/veilingen/archief
Disallow: /en/auctions/archive
Disallow: /de/auktionen/archive
Disallow: *?sortBy=
Disallow: *?sortDir=
Disallow: *?q=       ← SEARCH RESULTS ARE DISALLOWED
```

**Key implication**: The search endpoint (`?q=dell+optiplex`) is explicitly disallowed
for bots. We **must not** use keyword search URLs as the entry point. Instead:

**Recommended scraping strategy**: 
1. Fetch the current active auctions list from the auctions index page
2. For each active auction session, fetch its lots listing page
3. Filter lots by keyword matching on title/description (done in Python, not via search URL)

This is actually better for our use case: we get ALL lots and do precise filtering
in code, rather than relying on the site's search which may miss partial matches.

---

## 4. Anti-bot assessment

| Mechanism | Status | Notes |
|---|---|---|
| CAPTCHA | Not observed | No evidence in any response |
| JS challenge / redirect | Not observed | Responses are instant app shell |
| `Crawl-delay` in robots.txt | **10 seconds** | Must respect — implement via `asyncio.sleep(10)` |
| Headless detection | Unknown | Needs live Playwright test to determine |
| IP blocking | Unknown | Not triggered during recon |
| Rate limiting | Unknown | Needs live test |

**Recommendation**: Start with datacenter proxies (Apify free tier default). No residential
proxies until blocking is actually observed. The 10-second crawl delay is the main
constraint — respect it unconditionally.

---

## 5. Data availability — what is known vs. what needs Playwright

### Known (from sitemap / URL structure)
- Individual lot pages exist at `/nl/veilingen/{id}/kavels/{lot_id}`
- Category pages exist with numeric IDs (`?categorie=5` appears to be computers)
- The platform supports Dutch/English/German

### Unknown — requires Playwright to determine

These questions cannot be answered without actually rendering a page:

- **Index page data**: Which lot fields are visible in the listing view vs. detail-only?
  (title, bid, end time, thumbnail — likely on index; specs — likely detail-only)
- **Spec format**: Are specs in a structured table/labelled fields, or free-text Dutch prose?
  (both are possible; free-text is common for this type of auction)
- **End times**: Per-lot timestamps or per-auction-session (batch closing)?
  Dutch auction platforms often close lots in waves (lot 1 closes at 14:00, lot 2 at 14:02, etc.)
- **Bid data**: Is current bid visible on the listing page, or only on detail page?
- **Internal API**: The JS frontend likely calls a REST or GraphQL API. Playwright's
  network interception can capture these XHR calls. If the API returns JSON directly,
  we can call it without browser rendering (much faster and cheaper).
- **Pagination**: How many lots per page? What is the pagination mechanism (page param, scroll)?
- **Headless detection**: Does the site serve different content or block Playwright?

---

## 6. Template decision

**Chosen template**: `apify/python-playwright`

Reason: The site is a JavaScript SPA. Static HTML (BeautifulSoup) cannot render content.
Playwright is the only viable option without reverse-engineering the internal API first.

**Optimisation path** (post-initial-build):
If Playwright network interception reveals a clean JSON API (XHR calls during page load),
the scraper can be refactored to call the API directly using `httpx` or `requests`,
bypassing the browser entirely. This would reduce compute cost significantly and is
the preferred final state. Flag this during first live test.

---

## 7. Category ID for computers

From the sitemap, category structure observed:
- `/nl/c/{category-slug}/?categorie={id}` 

The category ID for electronics/computers is not yet confirmed from static recon alone.
Possible candidates: `categorie=5` (guessed). Playwright must confirm.

**Alternative approach** (recommended): Rather than limiting to a category, scrape all
active auction lots and filter by keyword. This is safer (new auctions may not be
categorised correctly) and the robots.txt does not disallow lot listing pages.

---

## 8. Apify compute cost estimate (preliminary)

Assumptions for a twice-weekly lightweight run:
- ~20–50 active auctions at any given time
- ~50–200 lots per auction (estimate; needs Playwright to confirm)
- Total lots to check: ~1000–10000 per run
- With Playwright: ~2–5 seconds per page rendered + 10s crawl delay = ~12–15s per lot
- **Worst case**: 10000 lots × 15s = 41 hours of browser time per run — clearly unviable

**Mitigation strategies** (must apply at least one):
1. **Keyword pre-filter at index level**: If lot titles are visible on the listing page,
   skip detail page fetches for lots that don't match keywords. This reduces detail
   page visits to ~10–50 per run instead of 10000.
2. **Internal API shortcut**: If XHR interception reveals a JSON API, ditch Playwright
   for data fetching entirely.
3. **Category scoping**: Only scrape the computers/electronics category, not all auctions.

The scraper design must implement strategy #1 at minimum. The Apify free tier provides
$5/month of compute. Playwright is ~0.001 CU per page. 50 detail pages per run = 
0.05 CU per run × ~8 runs/month = 0.4 CU/month — well within free tier.

**This estimate is preliminary and subject to revision after Playwright test run.**

---

## 8b. REST API — DISCOVERED (supersedes most of Section 5)

The Playwright probe captured the XHR calls made by the frontend. The site exposes a
**clean, unauthenticated REST API** at `https://onlineveilingmeester.nl/rest/`. No
browser rendering is needed at all. This changes the template selection (see Section 6b).

### Confirmed API endpoints

| Endpoint | Method | Returns |
|---|---|---|
| `/rest/nl/veilingen?status=open&domein=ONLINEVEILINGMEESTER` | GET | All 38 open auction sessions |
| `/rest/nl/v2/veilingen/{id}/kavels?page=1&size=100&status=OPEN&sortBy=volgNummer&veiling={id}` | GET | All lots in an auction (paginated) |
| `/rest/nl/v2/veilingen/{id}/kavels/{lot_number}` | GET | Full lot detail with specs |
| `/rest/nl/veilingen/{id}?categorieen=true` | GET | Auction session metadata |
| `/rest/nl/categorieen` | GET | All category IDs and names |
| `/rest/tijd` | GET | Server time (ISO 8601, UTC) |
| `/rest/jwt` | GET | 401 — auth required, not needed |

All data endpoints return **200 with no auth** for public lot data.

### Lot listing API response fields (per lot object in `content[]`)

```json
{
  "id": 1871080,
  "naam": "Diamant - 0.35 carat...",
  "hoogsteBod": 211.0,
  "openingsBod": 10.0,
  "sluitingsDatumISO": "2026-06-17T17:00:32Z",
  "volgNummer": "1",
  "aantalBiedingen": 16,
  "categorie": {"id": 3089, "naam": "Diamanten en edelstenen"},
  "veiling": {"id": 9062, "naam": "Edelstenen veiling"}
}
```

Key: `hoogsteBod` = current highest bid (€ float). `sluitingsDatumISO` = **per-lot** end
time in UTC. End times are spaced ~60 seconds apart per lot (lot 1 at 19:00:32, lot 2
at 19:01:32, etc.). **Per-lot closing confirmed.**

### Lot detail API response (additional fields beyond listing)

```json
{
  "kavelData": {
    "specificaties": "<p>Merk: Dell<br ...>Processor: i5<br ...>RAM: 8GB<br ...></p>",
    "bijzonderheden": "<p>Extra auction info...</p>",
    "naam": "lot name",
    "conditie": "",
    "bouwjaar": ""
  },
  "views": 528,
  "biedingen": []
}
```

Specs are in `kavelData.specificaties` as an HTML string with `<br class="editor-hard-break">`
separating fields. Strip HTML tags to get plain text for Dutch keyword matching.

### Auction listing API response (per auction object in `veilingen[]`)

```json
{
  "id": 9093,
  "naam": "Autoveiling",
  "sluitingsDatumISO": "2026-06-17T17:30:25Z",
  "zichtbareKavels": 101,
  "totaalKavels": 104,
  "type": "NORMAAL"
}
```

### Categories (from `/rest/nl/categorieen`)

9 top-level categories. ID for computers/electronics not yet confirmed (probe was on
gems auction). However, filtering all auctions by keyword is preferred over category
scoping — see Section 3.

### Pagination

Lots endpoint uses Spring pagination format. `size=100` fits most auctions. For auctions
with >100 visible lots, check `zichtbareKavels` and fetch additional pages.

---

## 6b. Template decision — REVISED

**Chosen template: Plain Python + `httpx`** (no browser at all)

The REST API is fully public and unauthenticated for lot data. A pure HTTP scraper is:
- 100× cheaper than Playwright on Apify compute
- Faster (no browser startup, no JS rendering wait)
- More reliable (structured JSON, no DOM changes)
- Simpler to maintain

The Dockerfile changes from `apify/actor-python-playwright` to `apify/actor-python` or
a lightweight Python base image.

The previous Playwright template decision (Section 6) is **superseded by this finding.**

---

## 9. Open questions for Phase 2 (Playwright test)

1. What HTML/CSS classes does the lot listing use? (needed for selector-based scraping)
2. What XHR/fetch calls does the page make? (potential API shortcut)
3. Are specs in structured fields or free Dutch prose?
4. Are end times per-lot or per-session (batch)?
5. Does the site serve 10-second delay worth of responses, or does it block headless?
6. What is the computers/electronics category ID?
7. How many lots per page? Is there infinite scroll or traditional pagination?

---

## 10. Terms of service note

The robots.txt is explicit: 10-second crawl delay. No scraping of search results,
archives, or sort-parameter URLs. We comply with all three. Lot listing pages and
detail pages are not disallowed. Scraping for personal price monitoring is within
normal personal use.
