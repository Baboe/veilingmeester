"""
Thin async REST client for OnlineVeilingMeester.nl.
All public methods return plain dicts/lists — no parsing beyond JSON.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

log = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
_DOMAIN = "ONLINEVEILINGMEESTER"


class VeilingMeesterClient:
    def __init__(self, base_url: str, crawl_delay_seconds: int = 10) -> None:
        self._base = base_url.rstrip("/")
        self._delay = crawl_delay_seconds
        self._client = httpx.AsyncClient(
            headers={"User-Agent": _USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )
        self._first_request = True

    async def _get(self, url: str, **params: Any) -> Any:
        if not self._first_request:
            await asyncio.sleep(self._delay)
        self._first_request = False
        try:
            r = await self._client.get(url, params=params or None)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            log.warning("HTTP %s for %s — skipping", exc.response.status_code, url)
            return None
        except Exception as exc:
            log.warning("Request failed for %s: %s — skipping", url, exc)
            return None

    async def get_open_auctions(self) -> list[dict]:
        url = f"{self._base}/rest/nl/veilingen"
        data = await self._get(url, status="open", domein=_DOMAIN)
        if data is None:
            return []
        # Response may be a list or {"veilingen": [...]}
        if isinstance(data, list):
            return data
        return data.get("veilingen", data.get("content", []))

    async def get_lots(
        self, auction_id: int | str, page: int = 1, size: int = 100
    ) -> dict:
        """Returns {"content": [...], "totalElements": N, "totalPages": N, ...}"""
        url = f"{self._base}/rest/nl/v2/veilingen/{auction_id}/kavels"
        data = await self._get(
            url,
            page=page,
            size=size,
            status="OPEN",
            sortBy="volgNummer",
            veiling=auction_id,
        )
        if data is None:
            return {"content": [], "totalPages": 0, "totalElements": 0}
        return data

    async def get_lot_detail(
        self, auction_id: int | str, volg_nummer: int | str
    ) -> dict | None:
        url = f"{self._base}/rest/nl/v2/veilingen/{auction_id}/kavels/{volg_nummer}"
        return await self._get(url)

    async def get_server_time(self) -> datetime:
        url = f"{self._base}/rest/tijd"
        data = await self._get(url)
        if data is None:
            return datetime.now(timezone.utc)
        # Response is an ISO string or {"tijd": "..."}
        raw = data if isinstance(data, str) else data.get("tijd", data.get("time", ""))
        try:
            dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except Exception:
            log.warning("Could not parse server time %r, using local UTC", raw)
            return datetime.now(timezone.utc)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "VeilingMeesterClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()
