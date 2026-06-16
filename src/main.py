"""
OnlineVeilingMeester.nl Auction Monitor — Apify Actor entry point.
Reads INPUT, runs the scraper, writes results to Dataset and KV Store.
"""

import asyncio
import logging

from apify import Actor

from .scraper import VeilingMeesterScraper
from .config import ActorConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def main() -> None:
    async with Actor:
        raw_input = await Actor.get_input() or {}
        config = ActorConfig.from_dict(raw_input)

        log.info("Profile: %s | keywords: %s | max_bid: €%s",
                 config.profile_name, config.keywords, config.max_bid)

        scraper = VeilingMeesterScraper(config, Actor)
        await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
