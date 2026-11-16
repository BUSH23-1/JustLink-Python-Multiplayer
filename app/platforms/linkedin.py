"""LinkedIn Posts API Integration.

Publishes posts via the official LinkedIn Posts REST API using OAuth 2.0 Bearer
authentication and member/organization permissions (w_member_social or w_organization_social).
"""

from typing import Optional
import httpx

from app.config import Settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class LinkedInPlatform(BasePlatform):
    """Integration for LinkedIn Posts API."""

    name: str = "LinkedIn"

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self.settings = settings
        self._client = client

    async def publish(self, message: str) -> PlatformResult:
        token = self.settings.linkedin_access_token
        author_urn = self.settings.linkedin_author_urn
        version = self.settings.linkedin_api_version

        if author_urn and "your_linkedin_person_id_here" in author_urn:
            author_urn = None

        if not token:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error="Credentials not configured: LINKEDIN_ACCESS_TOKEN is required.",
            )

        client = self._client or httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds
        )
        should_close = self._client is None

        try:
            # Auto-discover author URN via userinfo if not manually specified
            if not author_urn:
                try:
                    userinfo_resp = await client.get(
                        "https://api.linkedin.com/v2/userinfo",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if userinfo_resp.status_code == 200:
                        user_data = userinfo_resp.json()
                        sub = user_data.get("sub")
                        if sub:
                            author_urn = f"urn:li:person:{sub}"
                except Exception:
                    pass

            if not author_urn:
                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error="Credentials not configured: LINKEDIN_AUTHOR_URN is required.",
                )

            endpoint = "https://api.linkedin.com/rest/posts"

            headers = {
                "Authorization": f"Bearer {token}",
                "LinkedIn-Version": version,
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json",
            }

            payload = {
                "author": author_urn,
                "commentary": message,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": [],
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False,
            }

            resp = await client.post(
                endpoint,
                headers=headers,
                json=payload,
            )

            if resp.status_code == 201:
                post_urn = (
                    resp.headers.get("x-restli-id")
                    or resp.headers.get("x-linkedin-id")
                )

                if not post_urn and resp.text:
                    try:
                        data = resp.json()
                        post_urn = data.get("id")
                    except Exception:
                        pass

                if not post_urn:
                    post_urn = f"{author_urn}-post"

                posted_url = (
                    f"https://www.linkedin.com/feed/update/{post_urn}"
                )
                date_str, time_str = self.get_current_utc_timestamp()

                return PlatformResult(
                    platform=self.name,
                    status="success",
                    posted_url=posted_url,
                    public_access=True,
                    date=date_str,
                    time=time_str,
                    error=None,
                )

            else:
                err_detail = self._extract_linkedin_error(resp)

                # DEBUGGING: LinkedIn API error details
                print("\n========== LINKEDIN DEBUG ==========")
                print("LINKEDIN STATUS:", resp.status_code)
                print("LINKEDIN RESPONSE:", resp.text)
                print("LINKEDIN AUTHOR URN:", author_urn)
                print("LINKEDIN API VERSION:", version)
                print("====================================\n")

                return PlatformResult(
                    platform=self.name,
                    status="failure",
                    posted_url=None,
                    public_access=False,
                    date=None,
                    time=None,
                    error=f"LinkedIn Posts API error [HTTP {resp.status_code}]: {err_detail}",
                )

        except httpx.TimeoutException:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Timeout after {self.settings.http_timeout_seconds}s connecting to LinkedIn Posts API.",
            )

        except httpx.RequestError as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Network error connecting to LinkedIn Posts API: {str(exc)}",
            )

        except Exception as exc:
            return PlatformResult(
                platform=self.name,
                status="failure",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Unexpected error publishing to LinkedIn: {str(exc)}",
            )

        finally:
            if should_close:
                await client.aclose()

    @staticmethod
    def _extract_linkedin_error(resp: httpx.Response) -> str:
        """Helper to extract LinkedIn API error description."""
        try:
            data = resp.json()
            if isinstance(data, dict):
                msg = data.get("message")
                code = data.get("status") or data.get("serviceErrorCode")
                if msg:
                    return f"{msg} (code: {code})" if code else msg
        except Exception:
            pass

        return resp.text
