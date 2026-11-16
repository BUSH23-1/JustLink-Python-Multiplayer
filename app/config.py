"""Configuration settings for Automated Multi-Platform Posting System.

All credentials and configurable parameters are loaded from environment
variables or a local `.env` file using pydantic-settings.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and API credentials."""

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 4000
    debug: bool = False
    environment: str = "production"
    http_timeout_seconds: float = 15.0

    # Instagram Graph API Credentials
    # Requires an Instagram Professional/Business account linked to a Facebook Page
    # Scopes: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement
    instagram_access_token: Optional[str] = None
    instagram_account_id: Optional[str] = None
    instagram_image_url: str = (
        "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80"
    )
    instagram_api_version: str = "v19.0"

    # LinkedIn Posts API Credentials
    # Requires OAuth 2.0 Bearer token with 'w_member_social' or 'w_organization_social' scope
    linkedin_access_token: Optional[str] = None
    linkedin_author_urn: Optional[str] = None  # e.g., urn:li:person:XXXX or urn:li:organization:XXXX
    linkedin_api_version: str = "202401"

    # Telegram Bot API Credentials
    # Requires Bot Token from @BotFather and Target Chat/Channel ID (e.g., @my_channel or -100xxxxxxxxxx)
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Discord Webhooks API Credentials
    # Requires a valid Discord incoming webhook URL generated from Channel Settings -> Integrations -> Webhooks
    discord_webhook_url: Optional[str] = None
    discord_guild_id: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

