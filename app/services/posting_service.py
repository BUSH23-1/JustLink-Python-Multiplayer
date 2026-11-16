"""Orchestration service for multi-platform broadcasting."""

import asyncio
from typing import List, Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.platforms.linkedin import LinkedInPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.schemas import PostingResponse, PlatformResult


class PostingService:
    """Service that orchestrates concurrent publishing across all registered platforms."""

    def __init__(
        self,
        platforms: Optional[List[BasePlatform]] = None,
        settings: Optional[Settings] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        cfg = settings or default_settings
        if platforms is not None:
            self.platforms = platforms
        else:
            self.platforms = [
                LinkedInPlatform(settings=cfg, client=client),
                TelegramPlatform(settings=cfg, client=client),
                DiscordPlatform(settings=cfg, client=client),
            ]

    async def publish_all(self, message: str) -> PostingResponse:
        """Publishes the message to all configured platforms concurrently and independently."""
        tasks = [platform.publish(message) for platform in self.platforms]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results: List[PlatformResult] = []
        for platform, res in zip(self.platforms, raw_results):
            if isinstance(res, Exception):
                processed_results.append(
                    PlatformResult(
                        platform=platform.name,
                        status="failure",
                        posted_url=None,
                        public_access=False,
                        date=None,
                        time=None,
                        error=f"Internal unhandled exception: {type(res).__name__}: {str(res)}",
                    )
                )
            elif isinstance(res, PlatformResult):
                processed_results.append(res)
            else:
                processed_results.append(
                    PlatformResult(
                        platform=platform.name,
                        status="failure",
                        posted_url=None,
                        public_access=False,
                        date=None,
                        time=None,
                        error="Platform returned invalid response type.",
                    )
                )

        overall_success = (
            len(processed_results) > 0
            and all(r.status == "success" for r in processed_results)
        )

        return PostingResponse(
            success=overall_success,
            results=processed_results,
        )
