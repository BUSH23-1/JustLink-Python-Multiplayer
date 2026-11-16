"""Telegram Bot API Integration.

Publishes messages to Telegram channels, supergroups, or chats using the
official Telegram Bot API sendMessage endpoint.
"""

import datetime
from typing import Optional
import httpx

from app.config import Settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class TelegramPlatform(BasePlatform):
    """Integration for Telegram Bot API."""

    name: str = "Telegram"

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self._client = client

    async def publish(self, message: str) -> PlatformResult:
        token = self.settings.telegram_bot_token
        chat_id = self.settings.telegram_chat_id

        # 1. Credential verification
        if not token or not chat_id:
            missing = []
            if not token:
                missing.append("TELEGRAM_BOT_TOKEN")
            if not chat_id:
                missing.append("TELEGRAM_CHAT_ID")
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Credentials not configured: {', '.join(missing)} are required.",
            )

        client = self._client or httpx.AsyncClient(timeout=self.settings.http_timeout_seconds)
        should_close = self._client is None

        try:
            endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
            }

            resp = await client.post(endpoint, json=payload)
            data = resp.json()

            if resp.status_code == 200 and data.get("ok"):
                result = data.get("result", {})
                message_id = result.get("message_id")
                chat = result.get("chat", {})
                username = chat.get("username")

                # Determine post URL and public accessibility
                if username:
                    posted_url = f"https://t.me/{username}/{message_id}"
                    public_access = True
                elif str(chat_id).startswith("@"):
                    clean_name = str(chat_id).lstrip("@")
                    posted_url = f"https://t.me/{clean_name}/{message_id}"
                    public_access = True
                else:
                    # Private group or channel (numeric id)
                    raw_id = str(chat.get("id") or chat_id)
                    if raw_id.startswith("-100"):
                        # Internal channel reference format for Telegram supergroups/channels
                        clean_id = raw_id[4:]
                        posted_url = f"https://t.me/c/{clean_id}/{message_id}"
                    else:
                        posted_url = f"https://t.me/c/{raw_id.lstrip('-')}/{message_id}"
                    public_access = False

                # Extract posting date and time from actual message Unix timestamp
                ts = result.get("date")
                if ts:
                    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M:%S")
                else:
                    date_str, time_str = self.get_current_utc_timestamp()

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
                desc = data.get("description") if isinstance(data, dict) else resp.text
                err_code = data.get("error_code") if isinstance(data, dict) else resp.status_code
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error=f"Telegram API error [HTTP {resp.status_code}] (code {err_code}): {desc}",
                )

        except httpx.TimeoutException:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Timeout after {self.settings.http_timeout_seconds}s connecting to Telegram Bot API.",
            )
        except httpx.RequestError as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Network error connecting to Telegram Bot API: {str(exc)}",
            )
        except Exception as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Unexpected error publishing to Telegram: {str(exc)}",
            )
        finally:
            if should_close:
                await client.aclose()

