"""
One-shot Playwright probe for onlineveilingmeester.nl.
Run locally (not on Apify) to capture real HTML structure and XHR calls.

Usage:
  pip install playwright httpx
  playwright install chromium
  python probe.py

Writes probe_output/ with:
  - api_calls.json   — all XHR/fetch requests captured during page load
  - auctions.html    — raw HTML of the active auctions listing
  - lots.html        — raw HTML of one auction's lots listing
  - lot_detail.html  — raw HTML of one individual lot page
"""

import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright, Request, Response

OUTPUT = Path("probe_output")
OUTPUT.mkdir(exist_ok=True)

BASE = "https://www.onlineveilingmeester.nl"
LANG = "nl"

api_calls: list[dict] = []


async def capture_request(request: Request) -> None:
    if request.resource_type in ("xhr", "fetch"):
        try:
            post_data = request.post_data
        except Exception:
            post_data = None
        api_calls.append({
            "method": request.method,
            "url": request.url,
            "post_data": post_data,
        })


async def capture_response(response: Response) -> None:
    if response.request.resource_type in ("xhr", "fetch"):
        try:
            body = await response.json()
            for call in api_calls:
                if call["url"] == response.url:
                    call["response_json"] = body
                    call["status"] = response.status
                    break
        except Exception:
            pass


async def fetch_page(page, url: str, label: str, wait_selector: str | None = None) -> str:
    print(f"  Navigating to {url}")
    await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    # Give JS 4 seconds to render content
    await asyncio.sleep(4)
    if wait_selector:
        try:
            await page.wait_for_selector(wait_selector, timeout=8_000)
        except Exception:
            print(f"  WARNING: selector '{wait_selector}' not found on {label}")
    html = await page.content()
    (OUTPUT / f"{label}.html").write_text(html, encoding="utf-8")
    print(f"  Saved {label}.html ({len(html):,} bytes)")
    await asyncio.sleep(3)
    return html


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="nl-NL",
        )
        page = await context.new_page()
        page.on("request", capture_request)
        page.on("response", capture_response)

        # --- Step 1: active auctions listing ---
        print("\n[1] Fetching active auctions listing...")
        await fetch_page(page, f"{BASE}/{LANG}/veilingen", "auctions")

        # Try to find first active auction ID from the page
        auction_url = None
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href)"
        )
        for link in links:
            m = re.search(r"/veilingen/(\d+)", link)
            if m:
                auction_url = f"{BASE}/{LANG}/veilingen/{m.group(1)}/kavels"
                auction_id = m.group(1)
                print(f"  Found auction ID: {auction_id}")
                break

        if not auction_url:
            print("  ERROR: Could not find any auction ID. Trying hardcoded recent ID...")
            auction_id = "9131"
            auction_url = f"{BASE}/{LANG}/veilingen/{auction_id}/kavels"

        # --- Step 2: lots listing for one auction ---
        print(f"\n[2] Fetching lots listing for auction {auction_id}...")
        lots_html = await fetch_page(page, auction_url, "lots")

        # Try to find first lot ID
        lot_url = None
        links = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.href)"
        )
        # Skip lot 1 — try lot 5 for a more representative example
        target_lot = None
        for link in links:
            m = re.search(rf"/veilingen/{auction_id}/kavels/(\d+)", link)
            if m and int(m.group(1)) == 5:
                target_lot = m.group(1)
                break
        if not target_lot:
            for link in links:
                m = re.search(rf"/veilingen/{auction_id}/kavels/(\d+)", link)
                if m and int(m.group(1)) > 1:
                    target_lot = m.group(1)
                    break
        if target_lot:
            lot_url = f"{BASE}/{LANG}/veilingen/{auction_id}/kavels/{target_lot}"
            lot_id = target_lot
            print(f"  Found lot ID: {lot_id}")

        if not lot_url:
            print("  ERROR: Could not find any lot ID in lots listing.")
        else:
            # --- Step 3: individual lot detail ---
            print(f"\n[3] Fetching lot detail for lot {lot_id}...")
            await fetch_page(page, lot_url, "lot_detail")

        # --- Save API calls ---
        print(f"\n[4] Saving {len(api_calls)} captured XHR/fetch calls...")
        (OUTPUT / "api_calls.json").write_text(
            json.dumps(api_calls, indent=2, default=str),
            encoding="utf-8"
        )

        # Print summary
        print("\n=== API CALLS SUMMARY ===")
        for call in api_calls:
            status = call.get("status", "?")
            has_json = "json" if "response_json" in call else "no-json"
            print(f"  [{status}] {call['method']} {call['url'][:120]} ({has_json})")

        await browser.close()
        print(f"\nDone. Output in: {OUTPUT.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
