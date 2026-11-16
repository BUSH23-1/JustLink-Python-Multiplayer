"""Instagram Graph API Integration.

Publishes posts to Instagram Professional/Business accounts via Facebook Graph API.
Handles the required media container creation with a configurable promotional
image URL and uses the submitted message as the caption.
"""

import datetime
from typing import Optional
import httpx

from app.config import Settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class InstagramPlatform(BasePlatform):
    """Integration for Instagram Graph API."""

    name: str = "Instagram"

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self._client = client

    async def publish(self, message: str) -> PlatformResult:
        token = self.settings.instagram_access_token
        account_id = self.settings.instagram_account_id
        image_url = self.settings.instagram_image_url
        version = self.settings.instagram_api_version

        # 1. Credential verification
        if not token or not account_id:
            missing = []
            if not token:
                missing.append("INSTAGRAM_ACCESS_TOKEN")
            if not account_id:
                missing.append("INSTAGRAM_ACCOUNT_ID")
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
            # Step 1: Create Instagram media container
            container_endpoint = f"https://graph.facebook.com/{version}/{account_id}/media"
            container_payload = {
                "image_url": image_url,
                "caption": message,
                "access_token": token,
            }

            container_resp = await client.post(container_endpoint, data=container_payload)
            if container_resp.status_code != 200:
                err_detail = self._extract_fb_error(container_resp)
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error=f"Container creation failed [HTTP {container_resp.status_code}]: {err_detail}",
                )

            container_json = container_resp.json()
            creation_id = container_json.get("id")
            if not creation_id:
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error="Instagram API returned success but omitted container 'id'.",
                )

            # Step 2: Publish media container
            publish_endpoint = f"https://graph.facebook.com/{version}/{account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": token,
            }

            publish_resp = await client.post(publish_endpoint, data=publish_payload)
            if publish_resp.status_code != 200:
                err_detail = self._extract_fb_error(publish_resp)
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error=f"Media publishing failed [HTTP {publish_resp.status_code}]: {err_detail}",
                )

            publish_json = publish_resp.json()
            media_id = publish_json.get("id")
            if not media_id:
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error="Instagram API published container but omitted media 'id'.",
                )

            # Step 3: Fetch post permalink to obtain the actual live post URL
            permalink_endpoint = f"https://graph.facebook.com/{version}/{media_id}"
            permalink_resp = await client.get(
                permalink_endpoint,
                params={"fields": "permalink,shortcode,timestamp", "access_token": token},
            )

            date_str, time_str = self.get_current_utc_timestamp()
            posted_url: Optional[str] = None

            if permalink_resp.status_code == 200:
                media_data = permalink_resp.json()
                posted_url = media_data.get("permalink")
                if not posted_url and media_data.get("shortcode"):
                    posted_url = f"https://www.instagram.com/p/{media_data['shortcode']}/"

                # Parse official timestamp if provided
                if media_data.get("timestamp"):
                    try:
                        raw_ts = media_data["timestamp"].replace("Z", "+00:00")
                        dt = datetime.datetime.fromisoformat(raw_ts)
                        date_str = dt.strftime("%Y-%m-%d")
                        time_str = dt.strftime("%H:%M:%S")
                    except Exception:
                        pass

            if not posted_url:
                posted_url = f"https://www.instagram.com/p/{media_id}/"

            return PlatformResult(
                platform=self.name,
                status="success",
                posted_url=posted_url,
                public_access=True,
                date=date_str,
                time=time_str,
                error=None,
            )

        except httpx.TimeoutException:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Timeout after {self.settings.http_timeout_seconds}s connecting to Instagram Graph API.",
            )
        except httpx.RequestError as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Network error connecting to Instagram Graph API: {str(exc)}",
            )
        except Exception as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Unexpected error publishing to Instagram: {str(exc)}",
            )
        finally:
            if should_close:
                await client.aclose()

    @staticmethod
    def _extract_fb_error(resp: httpx.Response) -> str:
        """Helper to extract Facebook Graph API error message from response."""
        try:
            data = resp.json()
            if "error" in data:
                err = data["error"]
                msg = err.get("message", "")
                err_type = err.get("type", "")
                code = err.get("code", "")
                return f"{err_type} (code {code}): {msg}" if msg else resp.text
        except Exception:
            pass
        return resp.text

