"""Extract and display the key REST API responses from api_calls.json."""
import json
from pathlib import Path

data = json.loads(Path("probe_output/api_calls.json").read_text(encoding="utf-8"))

KEY_URLS = [
    "veilingen?status=open",
    "/rest/nl/v2/veilingen/9062/kavels?page=1",
    "/rest/nl/v2/veilingen/9062/kavels/5",
    "/rest/nl/veilingen/9062?categorieen",
    "/rest/tijd",
    "/rest/nl/categorieen",
]

for call in data:
    url = call.get("url", "")
    if "response_json" not in call:
        continue
    for pattern in KEY_URLS:
        if pattern in url:
            print(f"\n{'='*70}")
            print(f"[{call.get('status')}] {call['method']} {url[:100]}")
            print(f"{'='*70}")
            resp = call["response_json"]
            s = json.dumps(resp, indent=2, ensure_ascii=False)
            if len(s) > 4000:
                print(s[:4000])
                print(f"... [truncated, {len(s)} chars total]")
                if isinstance(resp, list):
                    print(f"\nList length: {len(resp)}")
                    print("First item:")
                    print(json.dumps(resp[0], indent=2, ensure_ascii=False)[:2000])
                elif isinstance(resp, dict):
                    for k, v in resp.items():
                        if isinstance(v, list) and len(v) > 0:
                            print(f"\n  Key '{k}' is a list of {len(v)}. First item:")
                            print(json.dumps(v[0], indent=2, ensure_ascii=False)[:2000])
            else:
                print(s)
            break
