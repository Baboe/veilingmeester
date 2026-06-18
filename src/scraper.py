"""
Main orchestration — ties together client, filters, store, and notifier.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from apify import Actor

from .client import VeilingMeesterClient
from .config import ActorConfig
from .filters import all_specs_pass, auction_title_skip, keyword_match, spec_check
from .notifier import (
    format_bid_reminder,
    format_discovery,
    format_over_budget,
    format_urgent,
    notify,
)
from .store import LotStore

log = logging.getLogger(__name__)


def _lot_url(base_url: str, auction_id: Any, volg_nummer: Any) -> str:
    return f"{base_url}/nl/kavels/{auction_id}/{volg_nummer}"


def _minutes_remaining(end_iso: str, now: datetime) -> int:
    try:
        end = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
        delta = end - now
        return max(0, int(delta.total_seconds() // 60))
    except Exception:
        return 9999


class VeilingMeesterScraper:
    def __init__(self, config: ActorConfig, actor: Any) -> None:
        self._config = config
        self._actor = actor
        self._store = LotStore()
        self._dataset_rows: list[dict] = []

    async def run(self) -> None:
        cfg = self._config
        async with VeilingMeesterClient(cfg.base_url, cfg.crawl_delay_seconds) as client:
            now = await client.get_server_time()
            log.info("Server UTC time: %s", now.isoformat())

            auctions = await client.get_open_auctions()
            log.info("Open auctions found: %d", len(auctions))

            if cfg.max_auctions_to_scan and len(auctions) > cfg.max_auctions_to_scan:
                auctions = auctions[: cfg.max_auctions_to_scan]

            skipped = 0
            for auction in auctions:
                naam = auction.get("naam", "")
                if auction_title_skip(naam, cfg.skip_auction_keywords):
                    log.info("Skipping auction %s — %s (matched skip keyword)", auction.get("id"), naam)
                    skipped += 1
                    continue
                await self._process_auction(client, auction, now)

            if skipped:
                log.info("Skipped %d/%d auctions by title filter", skipped, len(auctions))

        # Write all collected rows to Apify Dataset
        if self._dataset_rows:
            dataset = await Actor.open_dataset()
            for row in self._dataset_rows:
                await dataset.push_data(row)
            log.info("Wrote %d rows to dataset", len(self._dataset_rows))

        await self._store.cleanup_old_entries(days=30)

    async def _process_auction(
        self, client: VeilingMeesterClient, auction: dict, now: datetime
    ) -> None:
        auction_id = auction.get("id")
        naam = auction.get("naam", "")
        log.info("Processing auction %s — %s", auction_id, naam)

        page = 1
        while True:
            result = await client.get_lots(auction_id, page=page, size=100)
            lots = result.get("content", [])
            if not lots:
                break

            for lot in lots:
                await self._process_lot(client, auction_id, lot, now)

            total_pages = result.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1

    async def _process_lot(
        self,
        client: VeilingMeesterClient,
        auction_id: Any,
        lot: dict,
        now: datetime,
    ) -> None:
        cfg = self._config
        lot_naam = lot.get("naam", "")
        volg_nummer = lot.get("volgNummer")
        hoogste_bod = float(lot.get("hoogsteBod", 0) or 0)
        end_iso = lot.get("sluitingsDatumISO", "")
        lot_id = f"{auction_id}_{volg_nummer}"
        url = _lot_url(cfg.base_url, auction_id, volg_nummer)

        # Keyword filter on title
        if cfg.keywords and not keyword_match(lot_naam, cfg.keywords):
            return

        # Quick bid check before fetching detail
        over_budget = cfg.max_bid > 0 and hoogste_bod > cfg.max_bid
        if over_budget and cfg.suppress_above_max_bid:
            log.debug("Lot %s over budget (€%.0f > €%d), suppressed", lot_id, hoogste_bod, cfg.max_bid)
            return

        # Fetch full detail for spec parsing
        detail = await client.get_lot_detail(auction_id, volg_nummer)
        if detail is None:
            log.warning("Could not fetch detail for lot %s", lot_id)
            return

        # Extract spec HTML
        kavel_data = detail.get("kavelData", {})
        specs_html = kavel_data.get("specificaties", "") or ""
        bijzonderheden = kavel_data.get("bijzonderheden", "") or ""
        combined_html = specs_html + " " + bijzonderheden

        # Refresh bid from detail if available
        hoogste_bod = float(detail.get("hoogsteBod", hoogste_bod) or hoogste_bod)
        over_budget = cfg.max_bid > 0 and hoogste_bod > cfg.max_bid

        spec_result = spec_check(combined_html, cfg)
        spec_result["bid_ok"] = not over_budget

        minutes_left = _minutes_remaining(end_iso, now)

        self._dataset_rows.append({
            "lot_id": lot_id,
            "auction_id": auction_id,
            "volg_nummer": volg_nummer,
            "naam": lot_naam,
            "hoogste_bod": hoogste_bod,
            "end_iso": end_iso,
            "minutes_remaining": minutes_left,
            "url": url,
            **{f"spec_{k}": v for k, v in spec_result.items()},
        })

        if not all_specs_pass(spec_result):
            log.info(
                "Lot %s (%s) — spec filter failed: %s",
                lot_id, lot_naam, {k: v for k, v in spec_result.items() if k in ("cpu", "ram", "ssd", "power")}
            )
            return

        # All spec filters pass — check dedup state
        state = await self._store.get_lot_state(cfg.profile_name, lot_id)

        if state is None:
            if over_budget:
                log.info("Lot %s over budget (€%.0f > €%d), skipping", lot_id, hoogste_bod, cfg.max_bid)
                return
            if minutes_left < cfg.notify_minutes_before_end:
                msg = format_urgent(lot_naam, hoogste_bod, minutes_left, url, spec_result)
                log.info("URGENT new lot %s (%d min left)", lot_id, minutes_left)
            else:
                msg = format_discovery(lot_naam, hoogste_bod, end_iso, minutes_left, url, spec_result)
                log.info("Discovered lot %s (%d min left)", lot_id, minutes_left)
            await notify(cfg, msg)
            await self._store.set_lot_state(
                cfg.profile_name, lot_id, "discovered",
                {"naam": lot_naam, "bid": hoogste_bod, "end_iso": end_iso},
            )

        elif state == "discovered":
            if minutes_left <= cfg.notify_minutes_before_end:
                if over_budget:
                    msg = format_over_budget(lot_naam, hoogste_bod, cfg.max_bid, url)
                else:
                    msg = format_bid_reminder(lot_naam, hoogste_bod, url)
                log.info("Bid reminder for lot %s (%d min left)", lot_id, minutes_left)
                await notify(cfg, msg)
                await self._store.set_lot_state(
                    cfg.profile_name, lot_id, "reminded",
                    {"naam": lot_naam, "bid": hoogste_bod, "end_iso": end_iso},
                )

        else:
            log.debug("Lot %s already in state=%s, skipping", lot_id, state)
