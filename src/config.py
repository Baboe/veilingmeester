"""
Typed wrapper around the raw Actor input dict.
All defaults must match INPUT_SCHEMA.json defaults exactly.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotificationConfig:
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    whatsapp_enabled: bool = False
    whatsapp_phone: str = ""
    whatsapp_api_key: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "NotificationConfig":
        tg = d.get("telegram", {})
        wa = d.get("whatsapp_callmebot", {})
        return cls(
            telegram_enabled=bool(tg.get("enabled", False)),
            telegram_bot_token=str(tg.get("bot_token", "")),
            telegram_chat_id=str(tg.get("chat_id", "")),
            whatsapp_enabled=bool(wa.get("enabled", False)),
            whatsapp_phone=str(wa.get("phone", "")),
            whatsapp_api_key=str(wa.get("api_key", "")),
        )


@dataclass
class ActorConfig:
    profile_name: str = "default"
    keywords: list[str] = field(default_factory=list)
    processor_keywords: list[str] = field(default_factory=lambda: [
        "i5", "i7", "i8", "i9", "core i5", "core i7", "core i9"
    ])
    ram_min_gb: int = 8
    require_ssd: bool = True
    require_power_adapter: bool = True
    exclude_if_spec_unconfirmed: bool = True
    max_bid: int = 60
    suppress_above_max_bid: bool = True
    notify_minutes_before_end: int = 60
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    base_url: str = "https://www.onlineveilingmeester.nl"
    language: str = "nl"
    crawl_delay_seconds: int = 10
    max_auctions_to_scan: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "ActorConfig":
        return cls(
            profile_name=str(d.get("profile_name", "default")),
            keywords=[str(k) for k in d.get("keywords", [])],
            processor_keywords=[str(k) for k in d.get("processor_keywords", [
                "i5", "i7", "i8", "i9", "core i5", "core i7", "core i9"
            ])],
            ram_min_gb=int(d.get("ram_min_gb", 8)),
            require_ssd=bool(d.get("require_ssd", True)),
            require_power_adapter=bool(d.get("require_power_adapter", True)),
            exclude_if_spec_unconfirmed=bool(d.get("exclude_if_spec_unconfirmed", True)),
            max_bid=int(d.get("max_bid", 60)),
            suppress_above_max_bid=bool(d.get("suppress_above_max_bid", True)),
            notify_minutes_before_end=int(d.get("notify_minutes_before_end", 60)),
            notifications=NotificationConfig.from_dict(d.get("notifications", {})),
            base_url=str(d.get("base_url", "https://www.onlineveilingmeester.nl")).rstrip("/"),
            language=str(d.get("language", "nl")),
            crawl_delay_seconds=max(10, int(d.get("crawl_delay_seconds", 10))),
            max_auctions_to_scan=int(d.get("max_auctions_to_scan", 0)),
        )

    @property
    def url_prefix(self) -> str:
        return f"{self.base_url}/{self.language}"
