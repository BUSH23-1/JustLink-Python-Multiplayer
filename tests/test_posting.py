"""Unit and integration tests for Automated Multi-Platform Posting System.

Tests cover:
1. Message and CTA URL Pydantic validations (length, single CTA, HTTP/HTTPS scheme, invalid inputs).
2. Unconfigured credentials handling across all platforms.
3. Successful publishing to Instagram, LinkedIn, Telegram, and Discord using mocked API responses.
4. Independent platform error isolation (failure on one platform does not affect others).
5. HTTP timeout and network error resiliency.
6. Health and root service discovery endpoints.
"""

import pytest
import respx
import httpx
from starlette.testclient import TestClient

from app.main import app, get_posting_service
from app.config import Settings
from app.services.posting_service import PostingService
from app.platforms.instagram import InstagramPlatform
from app.platforms.linkedin import LinkedInPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing complete, valid dummy credentials for testing."""
    return Settings(
        instagram_access_token="test_ig_access_token_xyz",
        instagram_account_id="17841400000000000",
        instagram_image_url="https://images.example.com/promo.jpg",
        instagram_api_version="v19.0",
        linkedin_access_token="test_linkedin_oauth_token_abc",
        linkedin_author_urn="urn:li:person:12345678",
        linkedin_api_version="202401",
        telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        telegram_chat_id="@official_channel",
        discord_webhook_url="https://discord.com/api/webhooks/123456789/abcdef_token",
        discord_guild_id="guild_777",
        http_timeout_seconds=5.0,
    )


@pytest.fixture
def empty_settings() -> Settings:
    """Fixture providing empty credentials to simulate unconfigured environment."""
    return Settings(
        instagram_access_token=None,
        instagram_account_id=None,
        linkedin_access_token=None,
        linkedin_author_urn=None,
        telegram_bot_token=None,
        telegram_chat_id=None,
        discord_webhook_url=None,
        discord_guild_id=None,
        http_timeout_seconds=5.0,
    )


@pytest.fixture
def client(test_settings: Settings) -> TestClient:
    """TestClient configured with full test credentials."""
    service = PostingService(settings=test_settings)
    app.dependency_overrides[get_posting_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# 1. MESSAGE & CTA URL VALIDATION TESTS
# ============================================================================


def test_valid_message_accepted(client: TestClient):
    """A valid message <= 200 characters with exactly one CTA URL is accepted."""
    payload = {
        "message": "Check out our latest business platform! https://example.com"
    }
    response = client.post("/posting", json=payload)
    # The payload is valid, so status should not be 422
    assert response.status_code != 422


def test_message_exceeds_max_length(client: TestClient):
    """A message exceeding 200 characters must return 422 Unprocessable Entity."""
    long_text = "A" * 180 + " https://example.com"  # 180 + 20 = 200 chars
    # Exceed by adding more characters
    too_long = "A" * 190 + " https://example.com"
    response = client.post("/posting", json={"message": too_long})
    assert response.status_code == 422
    data = response.json()
    assert "200 characters" in str(data["detail"])


def test_message_missing_cta_url(client: TestClient):
    """A message without any CTA URL must return 422 Unprocessable Entity."""
    payload = {"message": "Check out our latest business platform without any link!"}
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "none was found" in str(data["detail"])


def test_message_multiple_cta_urls(client: TestClient):
    """A message containing more than one CTA URL must return 422 Unprocessable Entity."""
    payload = {
        "message": "Visit https://platform.com and also see https://docs.platform.com"
    }
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "found" in str(data["detail"])


def test_message_invalid_scheme_ftp(client: TestClient):
    """A message containing a non-HTTP/HTTPS URL (e.g. ftp://) must return 422."""
    payload = {"message": "Download our presentation here: ftp://files.example.com"}
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "Only 'http' and 'https' are permitted" in str(data["detail"])


def test_message_url_missing_scheme(client: TestClient):
    """A message containing 'www.example.com' without http:// or https:// must return 422."""
    payload = {"message": "Visit our official site at www.example.com"}
    response = client.post("/posting", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "missing scheme" in str(data["detail"])


def test_empty_message(client: TestClient):
    """An empty or purely whitespace message must return 422 Unprocessable Entity."""
    response = client.post("/posting", json={"message": "   "})
    assert response.status_code == 422
    data = response.json()
    assert "empty" in str(data["detail"])


def test_invalid_url_format(client: TestClient):
    """A message with an incomplete URL (missing domain) must return 422."""
    response = client.post("/posting", json={"message": "Check out https://"})
    assert response.status_code == 422


# ============================================================================
# 2. CREDENTIALS VERIFICATION TESTS (UNCONFIGURED CREDENTIALS)
# ============================================================================


def test_all_credentials_unconfigured(empty_settings: Settings):
    """When credentials are not configured, each platform reports failure with clear error details."""
    service = PostingService(settings=empty_settings)
    app.dependency_overrides[get_posting_service] = lambda: service
    test_client = TestClient(app)

    payload = {"message": "Check out our latest business platform! https://example.com"}
    response = test_client.post("/posting", json=payload)

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert len(data["results"]) == 4

    for result in data["results"]:
        assert result["status"] == "failure"
        assert result["posted_url"] is None
        assert result["public_access"] is False
        assert result["date"] is None
        assert result["time"] is None
        assert "Credentials not configured" in result["error"]


def test_partial_credentials_configured(test_settings: Settings):
    """When some platforms have credentials and others do not, unconfigured platforms fail gracefully."""
    # Only configure Telegram and Discord
    partial_settings = Settings(
        instagram_access_token=None,
        instagram_account_id=None,
        linkedin_access_token=None,
        linkedin_author_urn=None,
        telegram_bot_token=test_settings.telegram_bot_token,
        telegram_chat_id=test_settings.telegram_chat_id,
        discord_webhook_url=test_settings.discord_webhook_url,
        discord_guild_id=test_settings.discord_guild_id,
    )

    with respx.mock(assert_all_called=False) as respx_mock:
        # Mock Telegram
        respx_mock.post(f"https://api.telegram.org/bot{partial_settings.telegram_bot_token}/sendMessage").mock(
            return_value=httpx.Response(
                200,
                json={
                    "ok": True,
                    "result": {
                        "message_id": 101,
                        "date": 1731666600,
                        "chat": {"username": "official_channel"},
                    },
                },
            )
        )
        # Mock Discord
        respx_mock.post(f"{partial_settings.discord_webhook_url}?wait=true").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "discord_101",
                    "channel_id": "chan_202",
                    "guild_id": "guild_777",
                    "timestamp": "2026-11-15T10:30:00+00:00",
                },
            )
        )

        service = PostingService(settings=partial_settings)
        app.dependency_overrides[get_posting_service] = lambda: service
        test_client = TestClient(app)

        response = test_client.post(
            "/posting",
            json={"message": "Check out our latest business platform! https://example.com"},
        )
        app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False  # Because Instagram and LinkedIn failed

        results_by_platform = {r["platform"]: r for r in data["results"]}
        assert results_by_platform["Instagram"]["status"] == "failure"
        assert "Credentials not configured" in results_by_platform["Instagram"]["error"]
        assert results_by_platform["LinkedIn"]["status"] == "failure"
        assert "Credentials not configured" in results_by_platform["LinkedIn"]["error"]

        assert results_by_platform["Telegram"]["status"] == "success"
        assert results_by_platform["Telegram"]["posted_url"] == "https://t.me/official_channel/101"

        assert results_by_platform["Discord"]["status"] == "success"
        assert (
            results_by_platform["Discord"]["posted_url"]
            == "https://discord.com/channels/guild_777/chan_202/discord_101"
        )


# ============================================================================
# 3. SUCCESSFUL PUBLISHING ACROSS ALL PLATFORMS (MOCKED API RESPONSES)
# ============================================================================


@respx.mock
def test_all_platforms_successful(client: TestClient, test_settings: Settings):
    """When all external APIs respond successfully, all platforms return success with actual URLs and timestamps."""
    # 1. Mock Instagram endpoints
    ig_version = test_settings.instagram_api_version
    ig_account = test_settings.instagram_account_id

    # Container creation
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media").mock(
        return_value=httpx.Response(200, json={"id": "container_ig_999"})
    )
    # Media publish
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media_publish").mock(
        return_value=httpx.Response(200, json={"id": "media_ig_888"})
    )
    # Permalink fetch
    respx.get(f"https://graph.facebook.com/{ig_version}/media_ig_888").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "media_ig_888",
                "permalink": "https://www.instagram.com/p/DB12345xyz/",
                "shortcode": "DB12345xyz",
                "timestamp": "2026-11-15T10:30:00+0000",
            },
        )
    )

    # 2. Mock LinkedIn REST posts endpoint
    respx.post("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(
            201,
            headers={"x-restli-id": "urn:li:share:7123456789012345678"},
            json={},
        )
    )

    # 3. Mock Telegram Bot API sendMessage endpoint
    respx.post(f"https://api.telegram.org/bot{test_settings.telegram_bot_token}/sendMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "result": {
                    "message_id": 4200,
                    "date": 1794738600,
                    "chat": {
                        "id": -1001234567890,
                        "title": "Official Updates",
                        "username": "official_channel",
                    },
                },
            },
        )
    )

    # 4. Mock Discord Webhook endpoint
    respx.post(f"{test_settings.discord_webhook_url}?wait=true").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "1198765432109876543",
                "channel_id": "887766554433221100",
                "guild_id": "guild_777",
                "timestamp": "2026-11-15T10:30:00.000000+00:00",
            },
        )
    )

    payload = {
        "message": "Check out our latest business platform! https://example.com"
    }
    response = client.post("/posting", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["results"]) == 4

    results_by_platform = {r["platform"]: r for r in data["results"]}

    # Verify Instagram
    ig = results_by_platform["Instagram"]
    assert ig["status"] == "success"
    assert ig["posted_url"] == "https://www.instagram.com/p/DB12345xyz/"
    assert ig["public_access"] is True
    assert ig["date"] == "2026-11-15"
    assert ig["time"] == "10:30:00"
    assert ig["error"] is None

    # Verify LinkedIn
    li = results_by_platform["LinkedIn"]
    assert li["status"] == "success"
    assert li["posted_url"] == "https://www.linkedin.com/feed/update/urn:li:share:7123456789012345678"
    assert li["public_access"] is True
    assert li["date"] is not None
    assert li["time"] is not None
    assert li["error"] is None

    # Verify Telegram
    tg = results_by_platform["Telegram"]
    assert tg["status"] == "success"
    assert tg["posted_url"] == "https://t.me/official_channel/4200"
    assert tg["public_access"] is True
    assert tg["date"] is not None
    assert tg["time"] is not None
    assert tg["error"] is None

    # Verify Discord
    dc = results_by_platform["Discord"]
    assert dc["status"] == "success"
    assert (
        dc["posted_url"]
        == "https://discord.com/channels/guild_777/887766554433221100/1198765432109876543"
    )
    assert dc["public_access"] is False
    assert dc["date"] == "2026-11-15"
    assert dc["time"] == "10:30:00"
    assert dc["error"] is None


# ============================================================================
# 4. INDEPENDENT ERROR HANDLING & PLATFORM API FAILURES
# ============================================================================


@respx.mock
def test_instagram_api_failure_does_not_halt_other_platforms(
    client: TestClient, test_settings: Settings
):
    """When Instagram API fails, other platforms continue publishing successfully."""
    ig_version = test_settings.instagram_api_version
    ig_account = test_settings.instagram_account_id

    # Instagram returns 400 Bad Request
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "message": "Invalid OAuth access token.",
                    "type": "OAuthException",
                    "code": 190,
                }
            },
        )
    )

    # LinkedIn succeeds
    respx.post("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(201, headers={"x-restli-id": "urn:li:share:999"}, json={})
    )

    # Telegram succeeds
    respx.post(f"https://api.telegram.org/bot{test_settings.telegram_bot_token}/sendMessage").mock(
        return_value=httpx.Response(
            200,
            json={
                "ok": True,
                "result": {"message_id": 77, "chat": {"username": "official_channel"}},
            },
        )
    )

    # Discord succeeds
    respx.post(f"{test_settings.discord_webhook_url}?wait=true").mock(
        return_value=httpx.Response(
            200,
            json={"id": "msg_88", "channel_id": "c1", "guild_id": "g1"},
        )
    )

    response = client.post(
        "/posting",
        json={"message": "Check out our latest business platform! https://example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

    results = {r["platform"]: r for r in data["results"]}

    # Instagram failed
    assert results["Instagram"]["status"] == "failure"
    assert results["Instagram"]["posted_url"] is None
    assert "Invalid OAuth access token" in results["Instagram"]["error"]

    # The other 3 succeeded
    assert results["LinkedIn"]["status"] == "success"
    assert results["Telegram"]["status"] == "success"
    assert results["Discord"]["status"] == "success"


@respx.mock
def test_linkedin_unauthorized_error(client: TestClient, test_settings: Settings):
    """When LinkedIn returns 401 Unauthorized, it reports failure while others succeed."""
    ig_version = test_settings.instagram_api_version
    ig_account = test_settings.instagram_account_id

    # Instagram succeeds
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media").mock(
        return_value=httpx.Response(200, json={"id": "c1"})
    )
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media_publish").mock(
        return_value=httpx.Response(200, json={"id": "m1"})
    )
    respx.get(f"https://graph.facebook.com/{ig_version}/m1").mock(
        return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/p/m1/"})
    )

    # LinkedIn fails with 401
    respx.post("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(
            401,
            json={"message": "Expired access token", "serviceErrorCode": 65600},
        )
    )

    # Telegram succeeds
    respx.post(f"https://api.telegram.org/bot{test_settings.telegram_bot_token}/sendMessage").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 99, "chat": {"username": "official_channel"}}},
        )
    )

    # Discord succeeds
    respx.post(f"{test_settings.discord_webhook_url}?wait=true").mock(
        return_value=httpx.Response(200, json={"id": "msg_99", "channel_id": "c1", "guild_id": "g1"})
    )

    response = client.post(
        "/posting",
        json={"message": "Check out our latest business platform! https://example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    results = {r["platform"]: r for r in data["results"]}

    assert results["LinkedIn"]["status"] == "failure"
    assert "Expired access token" in results["LinkedIn"]["error"]
    assert results["Instagram"]["status"] == "success"
    assert results["Telegram"]["status"] == "success"
    assert results["Discord"]["status"] == "success"


@respx.mock
def test_telegram_rate_limited_error(client: TestClient, test_settings: Settings):
    """When Telegram returns 429 Too Many Requests, it reports failure gracefully."""
    ig_version = test_settings.instagram_api_version
    ig_account = test_settings.instagram_account_id

    # Instagram succeeds
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media").mock(
        return_value=httpx.Response(200, json={"id": "c1"})
    )
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media_publish").mock(
        return_value=httpx.Response(200, json={"id": "m1"})
    )
    respx.get(f"https://graph.facebook.com/{ig_version}/m1").mock(
        return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/p/m1/"})
    )

    # LinkedIn succeeds
    respx.post("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(201, headers={"x-restli-id": "urn:li:share:111"}, json={})
    )

    # Telegram fails with 429
    respx.post(f"https://api.telegram.org/bot{test_settings.telegram_bot_token}/sendMessage").mock(
        return_value=httpx.Response(
            429,
            json={"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 15"},
        )
    )

    # Discord succeeds
    respx.post(f"{test_settings.discord_webhook_url}?wait=true").mock(
        return_value=httpx.Response(200, json={"id": "msg_1", "channel_id": "c1", "guild_id": "g1"})
    )

    response = client.post(
        "/posting",
        json={"message": "Check out our latest business platform! https://example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    results = {r["platform"]: r for r in data["results"]}

    assert results["Telegram"]["status"] == "failure"
    assert "Too Many Requests" in results["Telegram"]["error"]
    assert results["Instagram"]["status"] == "success"
    assert results["LinkedIn"]["status"] == "success"
    assert results["Discord"]["status"] == "success"


@respx.mock
def test_discord_webhook_not_found(client: TestClient, test_settings: Settings):
    """When Discord webhook returns 404 Not Found, it reports failure while others succeed."""
    ig_version = test_settings.instagram_api_version
    ig_account = test_settings.instagram_account_id

    # Instagram succeeds
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media").mock(
        return_value=httpx.Response(200, json={"id": "c1"})
    )
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media_publish").mock(
        return_value=httpx.Response(200, json={"id": "m1"})
    )
    respx.get(f"https://graph.facebook.com/{ig_version}/m1").mock(
        return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/p/m1/"})
    )

    # LinkedIn succeeds
    respx.post("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(201, headers={"x-restli-id": "urn:li:share:111"}, json={})
    )

    # Telegram succeeds
    respx.post(f"https://api.telegram.org/bot{test_settings.telegram_bot_token}/sendMessage").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 99, "chat": {"username": "official_channel"}}},
        )
    )

    # Discord fails with 404
    respx.post(f"{test_settings.discord_webhook_url}?wait=true").mock(
        return_value=httpx.Response(
            404,
            json={"message": "Unknown Webhook", "code": 10015},
        )
    )

    response = client.post(
        "/posting",
        json={"message": "Check out our latest business platform! https://example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    results = {r["platform"]: r for r in data["results"]}

    assert results["Discord"]["status"] == "failure"
    assert "Unknown Webhook" in results["Discord"]["error"]
    assert results["Instagram"]["status"] == "success"
    assert results["LinkedIn"]["status"] == "success"
    assert results["Telegram"]["status"] == "success"


# ============================================================================
# 5. NETWORK TIMEOUT & RESILIENCE TESTS
# ============================================================================


@respx.mock
def test_network_timeout_handling(client: TestClient, test_settings: Settings):
    """When a network timeout occurs for one platform, it fails safely without crashing."""
    ig_version = test_settings.instagram_api_version
    ig_account = test_settings.instagram_account_id

    # Instagram times out
    respx.post(f"https://graph.facebook.com/{ig_version}/{ig_account}/media").mock(
        side_effect=httpx.TimeoutException("Connection timed out")
    )

    # LinkedIn succeeds
    respx.post("https://api.linkedin.com/rest/posts").mock(
        return_value=httpx.Response(201, headers={"x-restli-id": "urn:li:share:111"}, json={})
    )

    # Telegram succeeds
    respx.post(f"https://api.telegram.org/bot{test_settings.telegram_bot_token}/sendMessage").mock(
        return_value=httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 1, "chat": {"username": "official_channel"}}},
        )
    )

    # Discord succeeds
    respx.post(f"{test_settings.discord_webhook_url}?wait=true").mock(
        return_value=httpx.Response(200, json={"id": "msg_1", "channel_id": "c1", "guild_id": "g1"})
    )

    response = client.post(
        "/posting",
        json={"message": "Check out our latest business platform! https://example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    results = {r["platform"]: r for r in data["results"]}

    assert results["Instagram"]["status"] == "failure"
    assert "Timeout after" in results["Instagram"]["error"]
    assert results["LinkedIn"]["status"] == "success"
    assert results["Telegram"]["status"] == "success"
    assert results["Discord"]["status"] == "success"


# ============================================================================
# 6. ROOT & HEALTH ENDPOINTS TESTS
# ============================================================================


def test_root_endpoint(client: TestClient):
    """GET / should return system information and status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "supported_platforms" in data
    assert len(data["supported_platforms"]) == 4


def test_health_endpoint(client: TestClient):
    """GET /health should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

