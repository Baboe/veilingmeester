"""
Deduplication via Apify Key-Value Store.
States: discovered → reminded → closed
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from apify import Actor

log = logging.getLogger(__name__)

_STORE_NAME = "veilingmeester-state"


def _key(profile_name: str, lot_id: str | int) -> str:
    return f"{profile_name}:{lot_id}"


class LotStore:
    def __init__(self) -> None:
        self._store: Any = None

    async def _get_store(self) -> Any:
        if self._store is None:
            self._store = await Actor.open_key_value_store(name=_STORE_NAME)
        return self._store

    async def get_lot_state(
        self, profile_name: str, lot_id: str | int
    ) -> str | None:
        store = await self._get_store()
        key = _key(profile_name, lot_id)
        try:
            record = await store.get_value(key)
            if record is None:
                return None
            if isinstance(record, dict):
                return record.get("state")
            return str(record)
        except Exception as exc:
            log.warning("KV get failed for %s: %s", key, exc)
            return None

    async def set_lot_state(
        self,
        profile_name: str,
        lot_id: str | int,
        state: str,
        metadata: dict | None = None,
    ) -> None:
        store = await self._get_store()
        key = _key(profile_name, lot_id)
        record = {
            "state": state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }
        try:
            await store.set_value(key, record)
        except Exception as exc:
            log.warning("KV set failed for %s: %s", key, exc)

    async def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries whose updated_at is older than `days` days. Returns count removed."""
        store = await self._get_store()
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        removed = 0
        try:
            async for item in store.iterate_keys():
                key = item["key"] if isinstance(item, dict) else item
                try:
                    record = await store.get_value(key)
                    if not isinstance(record, dict):
                        continue
                    updated = record.get("updated_at", "")
                    if not updated:
                        continue
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if dt.timestamp() < cutoff:
                        await store.set_value(key, None)
                        removed += 1
                except Exception as exc:
                    log.debug("Cleanup skip %s: %s", key, exc)
        except Exception as exc:
            log.warning("Cleanup iteration failed: %s", exc)
        if removed:
            log.info("Cleaned up %d stale KV entries (older than %d days)", removed, days)
        return removed
