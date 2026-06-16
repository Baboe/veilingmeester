"""Deep structural extraction from lots.html."""
import re
import json
from pathlib import Path

html = Path("probe_output/lots.html").read_text(encoding="utf-8")

# Extract "Huidig bod" context to find bid amount
print("=== HUIDIG BOD CONTEXT ===")
idx = html.find("Huidig bod")
ctx = html[idx-50:idx+300]
print(ctx)

print()
# Extract full data-track-click JSON payloads
print("=== DATA-TRACK-CLICK JSON ===")
track_data = re.findall(r'data-track-click="([^"]+)"', html)
print(f"Found {len(track_data)} data-track-click attrs")
for td in track_data[:3]:
    try:
        decoded = td.replace("&quot;", '"').replace("&#39;", "'")
        obj = json.loads(decoded)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        print("---")
    except Exception as e:
        print(f"  Parse error: {e}")
        print(f"  Raw: {td[:200]}")

print()
# Look for c-lot-row classes (stable BEM class names)
print("=== C-LOT-ROW CLASSES ===")
lot_classes = re.findall(r'class="(c-lot[^"]+)"', html)
unique_lot = sorted(set(lot_classes))
for c in unique_lot:
    print(" ", c)

print()
# Extract all JSON-like objects in data attributes
print("=== DATA-TRACK-CONTENTVIEW JSON ===")
content_views = re.findall(r'data-track-contentview="([^"]+)"', html)
print(f"Found {len(content_views)}")
for cv in content_views[:2]:
    try:
        decoded = cv.replace("&quot;", '"')
        obj = json.loads(decoded)
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        print("---")
    except Exception as e:
        print(f"  Raw: {cv[:300]}")

print()
# Look for bid amount after "Huidig bod" text pattern
print("=== ALL BID AMOUNT PATTERNS ===")
# Find all occurrences of "Huidig bod" and surrounding text
for m in re.finditer(r"Huidig bod", html):
    idx = m.start()
    snippet = html[idx:idx+400]
    # Extract any numbers in next 200 chars
    numbers = re.findall(r">\s*(\d+(?:[.,]\d+)?)\s*<", snippet[:200])
    if numbers:
        print(f"  Numbers near 'Huidig bod': {numbers}")
    break  # Just show first one with full context

# Broader search: show 300 chars after first "Huidig bod"
idx = html.find("Huidig bod")
print(html[idx:idx+500].replace("<", "\n<")[:600])
