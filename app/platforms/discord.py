"""Discord Webhooks API Integration.

Publishes messages to Discord channels via incoming webhooks with ?wait=true
parameter to retrieve the confirmed message ID, channel ID, guild ID, and timestamp.
"""

import datetime
from typing import Optional
import httpx

from app.config import Settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class DiscordPlatform(BasePlatform):
    """Integration for Discord Webhook API."""

    name: str = "Discord"

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self._client = client

    async def publish(self, message: str) -> PlatformResult:
        webhook_url = self.settings.discord_webhook_url

        # 1. Credential verification
        if not webhook_url:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error="Credentials not configured: DISCORD_WEBHOOK_URL is required.",
            )

        client = self._client or httpx.AsyncClient(timeout=self.settings.http_timeout_seconds)
        should_close = self._client is None

        try:
            # Append ?wait=true so Discord waits for confirmation and returns the created message JSON
            sep = "&" if "?" in webhook_url else "?"
            endpoint = f"{webhook_url}{sep}wait=true"

            payload = {
                "content": message,
            }

            resp = await client.post(endpoint, json=payload)

            if resp.status_code in (200, 204):
                date_str, time_str = self.get_current_utc_timestamp()
                posted_url: Optional[str] = None

                if resp.status_code == 200 and resp.text:
                    try:
                        data = resp.json()
                        message_id = data.get("id")
                        channel_id = data.get("channel_id")
                        guild_id = data.get("guild_id") or self.settings.discord_guild_id

                        if guild_id and channel_id and message_id:
                            posted_url = f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                        elif channel_id and message_id:
                            posted_url = f"https://discord.com/channels/@me/{channel_id}/{message_id}"
                        elif message_id:
                            posted_url = f"https://discord.com/channels/@me/{message_id}"

                        # Parse Discord message timestamp if present
                        raw_ts = data.get("timestamp")
                        if raw_ts:
                            clean_ts = raw_ts.replace("Z", "+00:00")
                            dt = datetime.datetime.fromisoformat(clean_ts)
                            date_str = dt.strftime("%Y-%m-%d")
                            time_str = dt.strftime("%H:%M:%S")
                    except Exception:
                        pass

                if not posted_url:
                    posted_url = webhook_url

                # Discord channels require Discord user authentication and guild membership
                public_access = False

                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=posted_url,
                    public_access=public_access,
                    date=date_str,
                    time=time_str,
                    error=None,
                )
            else:
                err_detail = self._extract_discord_error(resp)
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error=f"Discord Webhook error [HTTP {resp.status_code}]: {err_detail}",
                )

        except httpx.TimeoutException:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Timeout after {self.settings.http_timeout_seconds}s connecting to Discord Webhook.",
            )
        except httpx.RequestError as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Network error connecting to Discord Webhook: {str(exc)}",
            )
        except Exception as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Unexpected error publishing to Discord: {str(exc)}",
            )
        finally:
            if should_close:
                await client.aclose()

    @staticmethod
    def _extract_discord_error(resp: httpx.Response) -> str:
        """Helper to extract Discord error description."""
        try:
            data = resp.json()
            if isinstance(data, dict):
                msg = data.get("message")
                code = data.get("code")
                return f"{msg} (code {code})" if msg and code else (msg or resp.text)
        except Exception:
            pass
        return resp.text

