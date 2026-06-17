# OnlineVeilingMeester.nl Auction Monitor

Apify Actor that monitors [OnlineVeilingMeester.nl](https://www.onlineveilingmeester.nl) for matching lots and sends notifications via Telegram and/or WhatsApp (CallMeBot).

## How it works

1. Fetches all open auctions via the unauthenticated REST API (no browser needed).
2. Filters lots by title keywords, then fetches full specs for candidates.
3. Applies five spec filters: CPU model, RAM, SSD, power adapter, and bid ceiling.
4. Sends a **discovery notification** when a new match is found, and a **bid reminder** when the lot is within `notify_minutes_before_end` of closing.
5. Deduplicates via Apify Key-Value Store so you only receive each notification once per run.

---

## Running manually in the Apify Console

1. Go to **Actors → Your Actor → Input**.
2. Paste one of the JSON profiles below (or the test profile).
3. Click **Start**.
4. Results appear in **Storage → Datasets** (all scanned lots) and notifications fire to your configured channels.

---

## Schedule setup (Tue/Fri 09:00 Europe/Paris)

1. Open your Actor → **Schedules** tab → **Create schedule**.
2. Set cron expression: `0 9 * * 2,5`
3. Set timezone: `Europe/Paris`.
4. Save and enable.

---

## Notification channel setup

### Telegram

1. Open [@BotFather](https://t.me/BotFather) in Telegram, send `/newbot`, follow instructions → get `bot_token`.
2. Start a chat with your new bot or add it to a group.
3. Get your `chat_id`: send a message, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`.
4. In Apify: go to **Settings → Environment variables** and add:
   - `TELEGRAM_BOT_TOKEN` = your token
   - `TELEGRAM_CHAT_ID` = your chat id
5. In your Actor input JSON set:
   ```json
   "notifications": {
     "telegram": {
       "enabled": true,
       "bot_token": "YOUR_TOKEN",
       "chat_id": "YOUR_CHAT_ID"
     }
   }
   ```

### WhatsApp via CallMeBot

1. Add **+34 644 59 78 54** to your WhatsApp contacts.
2. Send this exact message to that number on WhatsApp:
   ```
   I allow callmebot to send me messages
   ```
3. You will receive your API key back within a few seconds.
4. In your Actor input JSON set:
   ```json
   "notifications": {
     "whatsapp_callmebot": {
       "enabled": true,
       "phone": "32XXXXXXXXX",
       "api_key": "YOUR_API_KEY"
     }
   }
   ```
   Use your phone number in international format without the `+` (e.g. `32476123456` for Belgium).

---

## Search profiles

Each Actor run uses one profile (one input JSON). To search for different categories simultaneously, create **multiple Actor schedules** with different input JSONs, or run the Actor multiple times with different inputs.

### Test profile (mini-PC / server)

```json
{
  "profile_name": "mini-pc-server",
  "keywords": ["Dell OptiPlex", "HP EliteDesk", "ThinkCentre", "Mac mini"],
  "processor_keywords": ["i5", "i7", "i9", "core i5", "core i7"],
  "ram_min_gb": 8,
  "require_ssd": true,
  "require_power_adapter": true,
  "exclude_if_spec_unconfirmed": true,
  "max_bid": 60,
  "suppress_above_max_bid": true,
  "notify_minutes_before_end": 60,
  "notifications": {
    "telegram": {"enabled": false, "bot_token": "", "chat_id": ""},
    "whatsapp_callmebot": {"enabled": false, "phone": "", "api_key": ""}
  }
}
```

---

## Adjusting filters without touching code

All filter thresholds are Actor **input parameters** — change them in the Input tab or in your JSON:

| Parameter | What it does |
|---|---|
| `keywords` | Title must contain at least one of these strings (case-insensitive). Empty list = match all. |
| `processor_keywords` | At least one must appear in the specs. Add `"i5"` and `"i7"` both if you want either. |
| `ram_min_gb` | Minimum RAM in GB parsed from specs (`8gb`, `16 GB`, `8192mb`, etc.). |
| `require_ssd` | If true, specs must mention `ssd`, `nvme`, or `m.2`. |
| `require_power_adapter` | If true, specs must confirm a power adapter is included. |
| `exclude_if_spec_unconfirmed` | If true and power adapter is not mentioned at all, lot is excluded. |
| `max_bid` | Lots with `hoogsteBod > max_bid` are suppressed (set to `0` to disable). |
| `suppress_above_max_bid` | If false, over-budget lots are still logged to the dataset (no notification). |
| `notify_minutes_before_end` | Send bid reminder this many minutes before lot closes (default 60). |
| `max_auctions_to_scan` | Limit number of auctions per run (0 = no limit). |
| `crawl_delay_seconds` | Minimum delay between API requests. Do not set below 10 (robots.txt). |

---

## Dataset output

Every lot that passes the keyword filter (regardless of spec result) is written to the Apify Dataset with these fields:

| Field | Description |
|---|---|
| `lot_id` | `{auction_id}_{volg_nummer}` |
| `naam` | Lot title |
| `hoogste_bod` | Current highest bid in EUR |
| `end_iso` | Lot closing time (UTC ISO string) |
| `minutes_remaining` | Minutes until closing at scan time |
| `url` | Direct lot URL |
| `spec_cpu` / `spec_ram` / `spec_ssd` / `spec_power` | Per-filter pass/fail |
| `spec_ram_found_gb` | Parsed RAM value in GB (or null) |
| `spec_bid_ok` | Whether bid is within budget |
