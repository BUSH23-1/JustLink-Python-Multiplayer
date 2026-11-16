# Automated Multi-Platform Posting System

A high-performance, modular FastAPI microservice that accepts a promotional message and automatically publishes it concurrently across **Instagram**, **LinkedIn**, **Telegram**, and **Discord** using their official APIs.

---

## Table of Contents

- [Overview](#overview)
- [Architecture & Design](#architecture--design)
- [Project Directory Structure](#project-directory-structure)
- [Features & Validation Rules](#features--validation-rules)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Platform API Credentials Configuration](#platform-api-credentials-configuration)
  - [1. Instagram Graph API](#1-instagram-graph-api)
  - [2. LinkedIn Posts API](#2-linkedin-posts-api)
  - [3. Telegram Bot API](#3-telegram-bot-api)
  - [4. Discord Webhooks API](#4-discord-webhooks-api)
- [Running the Application](#running-the-application)
- [Interactive API Documentation (Swagger & ReDoc)](#interactive-api-documentation-swagger--redoc)
- [API Reference](#api-reference)
  - [`POST /posting`](#post-posting)
  - [`GET /`](#get-)
  - [`GET /health`](#get-health)
- [Sample Requests & Responses](#sample-requests--responses)
  - [Sample 1: Successful Publish Across All Platforms](#sample-1-successful-publish-across-all-platforms)
  - [Sample 2: Unconfigured Credentials Handling](#sample-2-unconfigured-credentials-handling)
  - [Sample 3: Validation Error (Message > 200 Characters)](#sample-3-validation-error-message--200-characters)
  - [Sample 4: Validation Error (Missing or Multiple CTA URLs)](#sample-4-validation-error-missing-or-multiple-cta-urls)
- [Running Unit Tests](#running-unit-tests)
- [Security & Best Practices](#security--best-practices)

---

## Overview

Modern marketing and content distribution workflows require publishing promotional updates to multiple social channels simultaneously. Manually posting to each network is slow and prone to errors.

The **Automated Multi-Platform Posting System** provides a single REST endpoint (`POST /posting`) that:
1. Validates promotional copy and call-to-action (CTA) links using strict Pydantic models.
2. Broadcasts content simultaneously to four major social networks in parallel using non-blocking asynchronous I/O.
3. Isolates external API errors so that a failure or unconfigured state in one platform never blocks the remaining platforms.
4. Returns granular, un-fabricated status objects for each network, including authentic post URLs, public accessibility flags, UTC timestamps, and exact platform error messages.

---

## Architecture & Design

```text
                                   +-----------------------+
                                   |     Client Request    |
                                   |     POST /posting     |
                                   +-----------+-----------+
                                               |
                                               v
                                   +-----------------------+
                                   |   Pydantic Validator  |
                                   |  (Max 200 chars,      |
                                   |   Single HTTP/S CTA)  |
                                   +-----------+-----------+
                                               |
                                               v
                                   +-----------------------+
                                   |    PostingService     |
                                   | (asyncio.gather /     |
                                   |  independent tasks)   |
                                   +-----------+-----------+
                     +-----------------+-------+-------+-----------------+
                     |                 |               |                 |
                     v                 v               v                 v
           +-----------------+ +---------------+ +---------------+ +---------------+
           |    Instagram    | |   LinkedIn    | |   Telegram    | |    Discord    |
           |    Graph API    | |   Posts API   | |    Bot API    | |  Webhooks API |
           | (Container/Pub) | |  (REST v2024) | | (sendMessage) | | (?wait=true)  |
           +-----------------+ +---------------+ +---------------+ +---------------+
```

### Core Architectural Decisions:
- **Resilient & Isolated Execution**: Platforms execute concurrently via `asyncio.gather(..., return_exceptions=True)`. If Instagram fails due to an expired token, LinkedIn, Telegram, and Discord still complete successfully.
- **Authentic Verification**: Never fabricates post URLs or success flags. If credentials are unconfigured or an API responds with an error, the system reports `"failure"` with accurate diagnostics and leaves `posted_url` as `null`.
- **Media Requirement for Instagram**: Since the Instagram Graph API requires media containers for feed posts, the system pairs a configurable high-resolution promotional image URL with the submitted text caption.
- **Asynchronous HTTP with HTTPX**: Built on `httpx.AsyncClient` with configurable timeout safety against hanging network sockets.

---

## Project Directory Structure

```text
automated-posting/
│
├── app/
│   ├── __init__.py               # Package marker and version identifier
│   ├── main.py                   # FastAPI app declaration, routes, and lifespan handlers
│   ├── schemas.py                # Pydantic models for request validation and response formatting
│   ├── config.py                 # Central settings powered by pydantic-settings (.env support)
│   │
│   ├── platforms/
│   │   ├── __init__.py           # Platform module exports
│   │   ├── base.py               # Abstract base class BasePlatform and timestamp helpers
│   │   ├── instagram.py          # Instagram Graph API integration (2-step container + publish)
│   │   ├── linkedin.py           # LinkedIn Posts REST API integration (OAuth 2.0 / w_member_social)
│   │   ├── telegram.py           # Telegram Bot API integration (sendMessage endpoint)
│   │   └── discord.py            # Discord Webhook integration (?wait=true confirmation)
│   │
│   └── services/
│       ├── __init__.py           # Service module exports
│       └── posting_service.py    # Orchestration service managing concurrent platform dispatch
│
├── tests/
│   ├── __init__.py               # Test package marker
│   └── test_posting.py           # Comprehensive pytest suite using mocked API responses (respx)
│
├── requirements.txt              # Production and test dependencies
├── .env.example                  # Documented environment variable template
├── .gitignore                    # Git ignore file preventing credential and cache leaks
└── README.md                     # Comprehensive technical documentation
```

### Purpose of Every File:
- **`app/main.py`**: Initializes the FastAPI application, mounts Swagger/ReDoc docs, and defines the `POST /posting`, `GET /`, and `GET /health` endpoints.
- **`app/schemas.py`**: Enforces strict request constraints (character limits, single CTA URL extraction and URL scheme/host verification) and defines the `PlatformResult` and `PostingResponse` schemas.
- **`app/config.py`**: Centralizes application configuration and loads sensitive credentials from environment variables or `.env`.
- **`app/platforms/base.py`**: Defines the abstract `BasePlatform` interface, ensuring a uniform `publish(message)` contract across all integrations.
- **`app/platforms/instagram.py`**: Manages the Meta Graph API container workflow: creates an image media container with caption, publishes the container, and queries for the permalink.
- **`app/platforms/linkedin.py`**: Dispatches posts to LinkedIn's official REST Posts API (`POST /rest/posts`) using bearer token authorization.
- **`app/platforms/telegram.py`**: Dispatches text messages to channels or groups via the Telegram Bot API (`POST /bot{token}/sendMessage`).
- **`app/platforms/discord.py`**: Delivers messages to Discord channels via webhooks with `?wait=true`, extracting confirmation message IDs and timestamps.
- **`app/services/posting_service.py`**: Dispatches concurrent publication tasks using `asyncio.gather`, handles exceptions per platform, and aggregates results.
- **`tests/test_posting.py`**: Complete unit test suite verifying validation logic, unconfigured credentials, successful publishing, API errors, and timeouts without live network calls.

---

## Features & Validation Rules

### Input Message Constraints:
1. **Length**: Maximum 200 characters (`len(message) <= 200`). Empty or whitespace-only messages are rejected.
2. **Exactly One CTA URL**: Must contain exactly 1 URL. Messages with 0 URLs or 2+ URLs are rejected.
3. **URL Scheme**: Must explicitly use `http://` or `https://`. Protocols such as `ftp://` or plain `www.example.com` without a scheme are rejected.
4. **URL Host**: Must have a valid network host or domain name (e.g. `example.com` or `localhost`).
5. **Punctuation Stripping**: Automatically strips sentence-ending punctuation (e.g., `https://example.com!` -> `https://example.com`) when validating.

---

## Prerequisites

- **Python 3.10+** (Python 3.12 recommended)
- **pip** (Python package installer)
- Operating System: Windows, Linux, or macOS

---

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/automated-posting.git
cd automated-posting
```

### 2. Create and Activate a Virtual Environment
**On Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (Command Prompt / PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Local Environment Configuration
```bash
cp .env.example .env
```
Open `.env` in your text editor and fill in your credentials (or test with mock/empty credentials).

---

## Platform API Credentials Configuration

### 1. Instagram Graph API
- **Official Documentation**: [Meta Instagram Graph API Content Publishing](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/content-publishing)
- **Prerequisites**:
  - An Instagram Professional (Business or Creator) Account.
  - A Facebook Page connected to your Instagram Professional Account.
  - A Meta Developer App at [developers.facebook.com](https://developers.facebook.com/).
- **Required Permissions (Scopes)**:
  - `instagram_basic`
  - `instagram_content_publish`
  - `pages_show_list`
  - `pages_read_engagement`
- **Environment Variables**:
  ```env
  INSTAGRAM_ACCESS_TOKEN=EAAG...your_long_lived_token...
  INSTAGRAM_ACCOUNT_ID=17841400000000000
  INSTAGRAM_IMAGE_URL=https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe
  INSTAGRAM_API_VERSION=v19.0
  ```
- **How to Obtain the `INSTAGRAM_ACCOUNT_ID`**:
  Query the Graph API Explorer:
  ```http
  GET https://graph.facebook.com/v19.0/me/accounts?access_token={PAGE_ACCESS_TOKEN}
  ```
  Look for `instagram_business_account.id`.

### 2. LinkedIn Posts API
- **Official Documentation**: [LinkedIn Consumer Solutions / Posts API](https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin)
- **Prerequisites**:
  - A LinkedIn Developer App registered at [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
  - "Share on LinkedIn" and "Sign In with LinkedIn using OpenID Connect" products added to the app.
- **Required Permissions (Scopes)**:
  - `w_member_social` (to post on personal profile)
  - `w_organization_social` (to post on company/organization pages)
- **Environment Variables**:
  ```env
  LINKEDIN_ACCESS_TOKEN=AQV...your_oauth2_token...
  LINKEDIN_AUTHOR_URN=urn:li:person:123456789
  LINKEDIN_API_VERSION=202401
  ```
- **How to Obtain the `LINKEDIN_AUTHOR_URN`**:
  Make an authenticated call with your token:
  ```http
  GET https://api.linkedin.com/v2/userinfo
  Authorization: Bearer {LINKEDIN_ACCESS_TOKEN}
  ```
  The returned `sub` value is your person ID (URN: `urn:li:person:{sub}`).

### 3. Telegram Bot API
- **Official Documentation**: [Telegram Bot API - sendMessage](https://core.telegram.org/bots/api#sendmessage)
- **Prerequisites**:
  - Create a bot via [@BotFather](https://t.me/BotFather) on Telegram to get your bot token.
  - Create a public or private Telegram Channel/Supergroup and add your bot as an **Administrator** with "Post Messages" rights.
- **Environment Variables**:
  ```env
  TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
  TELEGRAM_CHAT_ID=@your_public_channel_username
  ```
  *(For private channels, use numeric ID format: `-100xxxxxxxxxx`)*

### 4. Discord Webhooks API
- **Official Documentation**: [Discord Webhook Resource](https://discord.com/developers/docs/resources/webhook)
- **Prerequisites**:
  - In Discord, go to **Server Settings** or **Channel Settings** -> **Integrations** -> **Webhooks**.
  - Click **New Webhook**, select the target channel, and copy the Webhook URL.
- **Environment Variables**:
  ```env
  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789012345678/abcdefg_token
  DISCORD_GUILD_ID=123456789012345678
  ```

---

## Running the Application

Execute the application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

To enable auto-reload during development:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

---

## Interactive API Documentation (Swagger & ReDoc)

Once the application is running, access the interactive documentation:
- **Interactive Swagger UI**: [http://localhost:4000/docs](http://localhost:4000/docs)
- **ReDoc Alternative**: [http://localhost:4000/redoc](http://localhost:4000/redoc)
- **OpenAPI JSON Specification**: [http://localhost:4000/openapi.json](http://localhost:4000/openapi.json)

---

## API Reference

### `POST /posting`
Publishes the validated promotional message across all four platforms simultaneously.

**Request Headers**:
- `Content-Type: application/json`

**Request Body**:
```json
{
  "message": "Check out our latest business platform! https://example.com"
}
```

**Status Codes**:
- `200 OK`: Request processed. Results array contains individual platform outcomes.
- `422 Unprocessable Entity`: Message validation failed (exceeds 200 characters, missing/multiple CTA URLs, or invalid URL format).

---

### `GET /`
Returns service status and supported platform capabilities.

**Response**:
```json
{
  "service": "Automated Multi-Platform Posting System",
  "version": "1.0.0",
  "status": "online",
  "supported_platforms": ["Instagram", "LinkedIn", "Telegram", "Discord"],
  "docs_url": "/docs",
  "posting_endpoint": "POST /posting"
}
```

---

### `GET /health`
Probe endpoint for health checks and container readiness checks.

**Response**:
```json
{
  "status": "healthy"
}
```

---

## Sample Requests & Responses

### Sample 1: Successful Publish Across All Platforms

**cURL Request**:
```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform! https://example.com"}'
```

**Response (HTTP 200)**:
```json
{
  "success": true,
  "results": [
    {
      "platform": "Instagram",
      "status": "success",
      "posted_url": "https://www.instagram.com/p/DB12345xyz/",
      "public_access": true,
      "date": "2026-11-15",
      "time": "10:30:00",
      "error": null
    },
    {
      "platform": "LinkedIn",
      "status": "success",
      "posted_url": "https://www.linkedin.com/feed/update/urn:li:share:7123456789012345678",
      "public_access": true,
      "date": "2026-11-15",
      "time": "10:30:00",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/official_channel/4200",
      "public_access": true,
      "date": "2026-11-15",
      "time": "10:30:00",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/1234567890/8877665544/1198765432109876543",
      "public_access": false,
      "date": "2026-11-15",
      "time": "10:30:00",
      "error": null
    }
  ]
}
```

---

### Sample 2: Unconfigured Credentials Handling

When running without environment credentials configured:

**Response (HTTP 200)**:
```json
{
  "success": false,
  "results": [
    {
      "platform": "Instagram",
      "status": "failure",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Credentials not configured: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_ACCOUNT_ID are required."
    },
    {
      "platform": "LinkedIn",
      "status": "failure",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Credentials not configured: LINKEDIN_ACCESS_TOKEN, LINKEDIN_AUTHOR_URN are required."
    },
    {
      "platform": "Telegram",
      "status": "failure",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Credentials not configured: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID are required."
    },
    {
      "platform": "Discord",
      "status": "failure",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Credentials not configured: DISCORD_WEBHOOK_URL is required."
    }
  ]
}
```

---

### Sample 3: Validation Error (Message > 200 Characters)

**Request**:
```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "This promotional message is intentionally written to be extremely verbose and unnecessarily detailed, repeating words and phrases again and again to ensure that it exceeds the strict limit of two hundred characters allowed by the system https://example.com"}'
```

**Response (HTTP 422 Unprocessable Entity)**:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, Message exceeds maximum limit of 200 characters (received 273 characters).",
      "input": "..."
    }
  ]
}
```

---

### Sample 4: Validation Error (Missing or Multiple CTA URLs)

**Missing URL Request**:
```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform without any link!"}'
```

**Response (HTTP 422 Unprocessable Entity)**:
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, Message must contain exactly one Call-To-Action (CTA) URL, but none was found.",
      "input": "Check out our latest business platform without any link!"
    }
  ]
}
```

---

## Running Unit Tests

The test suite uses `pytest` and `respx` to mock all external API calls, executing in seconds without requiring live API keys or active internet access.

Run all tests:
```bash
pytest -v
```

Run tests with coverage report:
```bash
pytest --cov=app -v
```

### Tested Scenarios:
1. Valid message formatting and acceptance.
2. Character length validation (> 200 characters).
3. CTA URL presence validation (0 URLs rejected).
4. Multiple CTA URLs validation (2+ URLs rejected).
5. Unsupported scheme validation (e.g. `ftp://` rejected).
6. Missing scheme validation (e.g. `www.example.com` rejected).
7. Empty / whitespace message rejection.
8. Unconfigured credentials handling (returns structured failure details, no fabrication).
9. Partial credentials handling (configured platforms succeed while missing platforms fail).
10. Full 4-platform successful publishing with real URL extraction and timestamps.
11. Independent failure isolation (Instagram 400 error does not stop LinkedIn, Telegram, Discord).
12. LinkedIn 401 Unauthorized handling.
13. Telegram 429 Rate Limit handling.
14. Discord 404 Webhook Not Found handling.
15. HTTP socket timeout resiliency.
16. Root and health check service endpoints.

---

## Security & Best Practices

- **Zero Hardcoded Secrets**: All tokens, webhook URLs, and IDs are read exclusively from environment variables or `.env`.
- **Git Protection**: `.gitignore` is pre-configured to ignore `.env`, virtual environments, and test caches.
- **Input Sanitization**: Request bodies are validated using Pydantic before any downstream processing.
- **Fail-Safe Asynchrony**: `asyncio.gather` with `return_exceptions=True` protects against unhandled thread or task crashes.
- **Configurable Timeouts**: All HTTP requests use bounded timeouts (default: 15s) to prevent thread/coroutine exhaustion.

