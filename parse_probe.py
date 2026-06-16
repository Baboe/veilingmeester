"""Quick HTML structure extractor for probe output."""
import re
from pathlib import Path

def analyze(filename: str) -> None:
    path = Path("probe_output") / filename
    if not path.exists():
        print(f"MISSING: {filename}")
        return
    html = path.read_text(encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"FILE: {filename}  ({len(html):,} bytes)")
    print(f"{'='*60}")

    lot_links = re.findall(r'href="(/nl/veilingen/\d+/kavels/\d+)"', html)
    print(f"Lot links: {len(lot_links)}  first 10: {lot_links[:10]}")

    auction_links = re.findall(r'href="(/nl/veilingen/\d+)"', html)
    print(f"Auction links: {len(auction_links)}  first 10: {auction_links[:10]}")

    bids = re.findall(r'€\s*[\d.,]+', html)
    print(f"Euro amounts: {len(bids)}  first 10: {bids[:10]}")

    dt_nl = re.findall(r'\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}', html)
    print(f"Dutch datetimes: {len(dt_nl)}  first 5: {dt_nl[:5]}")

    dt_iso = re.findall(r'20\d\d-\d\d-\d\dT\d\d:\d\d', html)
    print(f"ISO datetimes: {len(dt_iso)}  first 5: {dt_iso[:5]}")

    # class names (unique, sorted)
    classes = re.findall(r'class="([^"]{3,80})"', html)
    unique_classes = sorted(set(c.strip() for c in classes if c.strip()))
    print(f"Unique class strings: {len(unique_classes)}")
    for c in unique_classes[:40]:
        print(f"  {c}")

    data_attrs = re.findall(r'(data-[a-z-]+)=', html)
    unique_data = sorted(set(data_attrs))
    print(f"Data-* attributes: {unique_data}")

    # title tags / heading text
    titles = re.findall(r'<h[123][^>]*>([^<]{5,120})</h[123]>', html)
    print(f"Headings: {titles[:20]}")

    # any Dutch auction keywords
    for kw in ["voeding", "oplader", "lader", "adapter", "i5", "i7", "ssd", "nvme", "veiling", "bod", "bieden"]:
        count = html.lower().count(kw)
        if count:
            print(f"  keyword '{kw}': {count} occurrences")


analyze("auctions.html")
analyze("lots.html")
analyze("lot_detail.html")
