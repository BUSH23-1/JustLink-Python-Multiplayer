"""Platform integration modules for social networks."""

from app.platforms.base import BasePlatform
from app.platforms.linkedin import LinkedInPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform

__all__ = [
    "BasePlatform",
    "LinkedInPlatform",
    "TelegramPlatform",
    "DiscordPlatform",
]

