"""
Notification delivery — Telegram (Bot API) and CallMeBot WhatsApp.
"""

from __future__ import annotations

import logging
import urllib.parse
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from .config import ActorConfig

log = logging.getLogger(__name__)


async def send_telegram(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
        log.info("Telegram notification sent")
        return True
    except Exception as exc:
        log.warning("Telegram send failed: %s", exc)
        return False


async def send_callmebot_whatsapp(phone: str, api_key: str, text: str) -> bool:
    encoded = urllib.parse.quote(text)
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={phone}&apikey={api_key}&text={encoded}"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            r.raise_for_status()
        log.info("WhatsApp notification sent")
        return True
    except Exception as exc:
        log.warning("WhatsApp send failed: %s", exc)
        return False


async def notify(config: "ActorConfig", message_text: str) -> None:
    sent = False
    nc = config.notifications

    if nc.telegram_enabled and nc.telegram_bot_token and nc.telegram_chat_id:
        await send_telegram(nc.telegram_bot_token, nc.telegram_chat_id, message_text)
        sent = True

    if nc.whatsapp_enabled and nc.whatsapp_phone and nc.whatsapp_api_key:
        await send_callmebot_whatsapp(nc.whatsapp_phone, nc.whatsapp_api_key, message_text)
        sent = True

    if not sent:
        log.info("No notification channels enabled — message: %s", message_text[:120])


def format_discovery(
    title: str,
    bid: float,
    end_iso: str,
    minutes_remaining: int,
    lot_url: str,
    spec_result: dict,
) -> str:
    cpu_tick = "✅" if spec_result.get("cpu") else "❌"
    ram_gb = spec_result.get("ram_found_gb")
    ram_label = f"{ram_gb}GB" if ram_gb else "?"
    ram_tick = "✅" if spec_result.get("ram") else "❌"
    ssd_tick = "✅" if spec_result.get("ssd") else "❌"
    power_tick = "✅" if spec_result.get("power") else "❌"

    return (
        f"🔍 <b>GEVONDEN</b>\n"
        f"{title}\n\n"
        f"💶 Huidig bod: €{bid:.0f}\n"
        f"⏱ Sluit over ~{minutes_remaining} min ({end_iso})\n\n"
        f"CPU {cpu_tick}  RAM {ram_label} {ram_tick}  SSD {ssd_tick}  Voeding {power_tick}\n\n"
        f"🔗 {lot_url}"
    )


def format_bid_reminder(
    title: str,
    bid: float,
    lot_url: str,
) -> str:
    return (
        f"⏰ <b>BIEDEN NU</b>\n"
        f"{title}\n\n"
        f"💶 Huidig bod: €{bid:.0f}\n"
        f"⌛ Sluit over ~60 minuten\n\n"
        f"🔗 {lot_url}"
    )


def format_over_budget(title: str, bid: float, max_bid: float, lot_url: str) -> str:
    return (
        f"🚫 <b>BUDGET OVERSCHREDEN</b>\n"
        f"{title}\n\n"
        f"💶 Staat nu op €{bid:.0f} (jouw max: €{max_bid:.0f})\n\n"
        f"🔗 {lot_url}"
    )


def format_urgent(
    title: str,
    bid: float,
    minutes_remaining: int,
    lot_url: str,
    spec_result: dict,
) -> str:
    cpu_tick = "✅" if spec_result.get("cpu") else "❌"
    ram_gb = spec_result.get("ram_found_gb")
    ram_label = f"{ram_gb}GB" if ram_gb else "?"
    ram_tick = "✅" if spec_result.get("ram") else "❌"
    ssd_tick = "✅" if spec_result.get("ssd") else "❌"
    power_tick = "✅" if spec_result.get("power") else "❌"

    return (
        f"⚠️ <b>URGENT</b>\n"
        f"{title}\n\n"
        f"💶 Huidig bod: €{bid:.0f}\n"
        f"🔥 Sluit over ~{minutes_remaining} min!\n\n"
        f"CPU {cpu_tick}  RAM {ram_label} {ram_tick}  SSD {ssd_tick}  Voeding {power_tick}\n\n"
        f"🔗 {lot_url}"
    )
