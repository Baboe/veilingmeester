"""Extract bid text element and lot card full structure."""
import re
import json
from pathlib import Path

html = Path("probe_output/lots.html").read_text(encoding="utf-8")

# Find c-lot-row__bid-text context
print("=== BID TEXT ELEMENT CONTEXT ===")
idx = html.find("c-lot-row__bid-text")
print(html[idx-50:idx+400].replace("<", "\n<")[:600])

print()
# Find all lot card rows - look for c-lot-row patterns
print("=== LOT CARD FULL STRUCTURE (first lot) ===")
# Find first lot row container
idx = html.find('c-lot-row__cell--image')
if idx > 0:
    # Go back to find the card start
    card_start = html.rfind('<div', 0, idx)
    card_start = html.rfind('<div', 0, card_start)
    print(html[card_start:card_start+1500].replace("<", "\n<")[:1500])

print()
# Check all data-track-click for bid amount (price field)
print("=== FULL FIRST TRACK-CLICK JSON (all fields) ===")
track_data = re.findall(r'data-track-click="([^"]+)"', html)
if track_data:
    decoded = track_data[0].replace("&quot;", '"').replace("&#39;", "'")
    obj = json.loads(decoded)
    print(json.dumps(obj, indent=2, ensure_ascii=False))

print()
# Look for "prijs", "price", "amount", "bedrag" in the HTML
for kw in ["prijs", "price", "amount", "bedrag", "startbod", "Startbod", "lotPrice", "lotAmount"]:
    count = html.count(kw)
    if count:
        idx = html.find(kw)
        print(f"'{kw}' ({count}x): ...{html[idx:idx+200].replace(chr(10),' ')}...")
