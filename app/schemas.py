"""Pydantic schemas and request/response validation models."""

import re
import urllib.parse
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# Regular expression to identify candidate URLs (protocols or www prefix)
CANDIDATE_URL_PATTERN = re.compile(
    r'(?:[a-zA-Z][a-zA-Z0-9+.-]*://|www\.)[^\s<>"\'{}|\\^`]+',
    re.IGNORECASE,
)

# Trailing punctuation to strip from matched URLs at sentence boundaries
TRAILING_PUNCTUATION = ".,!?:;)\"'>]}"


class PostingRequest(BaseModel):
    """Request payload for posting messages to platforms."""

    message: str = Field(
        ...,
        description="Short message to publish across platforms. Must be <= 200 chars and contain exactly one HTTP/HTTPS CTA URL.",
        examples=["Check out our latest business platform! https://example.com"],
    )

    @field_validator("message")
    @classmethod
    def validate_message_and_cta_url(cls, v: str) -> str:
        # 1. Non-empty validation
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or contain only whitespace.")

        # 2. Maximum 200 characters validation
        if len(v) > 200:
            raise ValueError(
                f"Message exceeds maximum limit of 200 characters (received {len(v)} characters)."
            )

        # 3. Find candidate URLs in the message text
        raw_matches = CANDIDATE_URL_PATTERN.findall(v)
        cleaned_urls = [match.rstrip(TRAILING_PUNCTUATION) for match in raw_matches if match.rstrip(TRAILING_PUNCTUATION)]

        # 4. Exactly one CTA URL validation
        url_count = len(cleaned_urls)
        if url_count == 0:
            raise ValueError(
                "Message must contain exactly one Call-To-Action (CTA) URL, but none was found."
            )
        if url_count > 1:
            raise ValueError(
                f"Message must contain exactly one Call-To-Action (CTA) URL, but {url_count} were found: {cleaned_urls}."
            )

        # 5. Format and HTTP/HTTPS scheme validation
        cta_url = cleaned_urls[0]
        if cta_url.lower().startswith("www."):
            raise ValueError(
                f"CTA URL '{cta_url}' is missing scheme. It must explicitly include 'http://' or 'https://'."
            )

        try:
            parsed = urllib.parse.urlsplit(cta_url)
        except Exception as exc:
            raise ValueError(f"Malformed CTA URL '{cta_url}': {str(exc)}") from exc

        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme '{parsed.scheme}' in CTA URL '{cta_url}'. Only 'http' and 'https' are permitted."
            )

        host = parsed.netloc.split(":")[0]
        if not host:
            raise ValueError(
                f"Invalid CTA URL format in '{cta_url}': missing domain/host."
            )

        if host.lower() != "localhost" and ("." not in host or host.startswith(".") or host.endswith(".")):
            raise ValueError(
                f"Invalid host '{host}' in CTA URL '{cta_url}'. Must be a valid domain name or localhost."
            )

        return v


class PlatformResult(BaseModel):
    """Result for an individual social platform publishing attempt."""

    platform: str = Field(..., description="Name of the platform (Instagram, LinkedIn, Telegram, Discord)")
    status: str = Field(..., description="Status of the post: 'success' or 'failure'")
    posted_url: Optional[str] = Field(
        None,
        description="Actual published post URL if successfully published; null otherwise",
    )
    public_access: bool = Field(
        ...,
        description="Whether the published post is publicly accessible without platform authentication",
    )
    date: Optional[str] = Field(
        None,
        description="Posting date in YYYY-MM-DD format (UTC) if published; null otherwise",
    )
    time: Optional[str] = Field(
        None,
        description="Posting time in HH:MM:SS format (UTC) if published; null otherwise",
    )
    error: Optional[str] = Field(
        None,
        description="Detailed error message if the platform failed or credentials are unconfigured; null on success",
    )


class PostingResponse(BaseModel):
    """Overall response containing individual results for all four platforms."""

    success: bool = Field(
        ...,
        description="True if all platforms published successfully; False if any platform encountered an error or unconfigured credentials",
    )
    results: List[PlatformResult] = Field(
        ...,
        description="Array of results for each platform",
    )

