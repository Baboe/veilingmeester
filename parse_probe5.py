"""Extract JSON-LD structured data from the lots page — the gold mine."""
import re
import json
from pathlib import Path

html = Path("probe_output/lots.html").read_text(encoding="utf-8")

# Find all JSON-LD script blocks
ld_blocks = re.findall(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    html, re.DOTALL
)
print(f"JSON-LD blocks found: {len(ld_blocks)}")

for i, block in enumerate(ld_blocks):
    try:
        obj = json.loads(block)
        print(f"\n--- Block {i+1} (@type: {obj.get('@type', '?')}) ---")
        # Pretty-print but truncate if huge
        s = json.dumps(obj, indent=2, ensure_ascii=False)
        if len(s) > 3000:
            print(s[:3000])
            print(f"... [truncated, total {len(s)} chars]")
            # Show first item of any list
            if "itemListElement" in obj:
                items = obj["itemListElement"]
                print(f"\nFirst item of itemListElement ({len(items)} items):")
                print(json.dumps(items[0], indent=2, ensure_ascii=False))
                print(f"\nSecond item:")
                print(json.dumps(items[1], indent=2, ensure_ascii=False))
        else:
            print(s)
    except json.JSONDecodeError as e:
        print(f"  Parse error: {e}")
        print(f"  Raw (first 500): {block[:500]}")

print()
# Also check auctions.html for JSON-LD
html2 = Path("probe_output/auctions.html").read_text(encoding="utf-8")
ld_blocks2 = re.findall(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
    html2, re.DOTALL
)
print(f"\nAuctions.html JSON-LD blocks: {len(ld_blocks2)}")
for i, block in enumerate(ld_blocks2):
    try:
        obj = json.loads(block)
        s = json.dumps(obj, indent=2, ensure_ascii=False)
        print(f"\n--- Auctions Block {i+1} ---")
        print(s[:1500])
    except Exception as e:
        print(f"  Error: {e}")
