"""Extract detailed structure from lots.html."""
import re
from pathlib import Path

html = Path("probe_output/lots.html").read_text(encoding="utf-8")

# h3 titles
h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", html)
print(f"h3 ({len(h3)}):")
for t in h3[:20]:
    print(" ", t.strip())

print()
h2 = re.findall(r"<h2[^>]*>([^<]+)</h2>", html)
print(f"h2 ({len(h2)}):")
for t in h2[:10]:
    print(" ", t.strip())

print()
# aria-label
aria = re.findall(r'aria-label="([^"]{5,100})"', html)
print(f"aria-label ({len(aria)}):")
for a in aria[:20]:
    print(" ", a)

print()
# datetime attrs
dt = re.findall(r'datetime="([^"]+)"', html)
print(f"datetime ({len(dt)}): {dt[:10]}")

print()
# Look for "Huidig bod" or "Startbod" patterns
for kw in ["Huidig bod", "Startbod", "Huidige bieder", "Sluitingstijd", "Sluit", "bod:", "bieden"]:
    count = html.count(kw)
    if count:
        idx = html.index(kw)
        snippet = html[idx:idx+200].replace("\n", " ")
        print(f"'{kw}' x{count}: ...{snippet[:150]}...")

print()
# Find lot card container - look for repeated patterns around lot links
# Get context around first lot link
m = re.search(r'href="/nl/veilingen/9062/kavels/5"', html)
if m:
    ctx = html[m.start()-500:m.start()+500]
    print("Context around kavels/5 link:")
    print(ctx[:800])

print()
# Look for span or p tags with numbers that look like bids
spans_with_numbers = re.findall(r"<span[^>]*>(\s*\d{1,4}\s*)</span>", html)
print(f"Spans with short numbers ({len(spans_with_numbers)}): {spans_with_numbers[:30]}")
