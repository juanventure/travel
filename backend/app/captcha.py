"""
Cloudflare Turnstile bot protection for the chat endpoint.

Gates the FIRST message of each chat session: the client must submit a valid
Turnstile token, which we verify server-side. Once a session passes, we remember
it in Redis (24h) so subsequent messages in that conversation aren't re-gated.

Disabled automatically when TURNSTILE_SECRET_KEY is unset (e.g. local dev),
so the app still works without keys. For local/integration testing, Cloudflare
publishes test keys:
  always-passes secret: 1x0000000000000000000000000000000AA
  always-fails  secret: 2x0000000000000000000000000000000AA
  always-passes sitekey (frontend): 1x00000000000000000000AA
"""
import os

import httpx
from fastapi import Request, HTTPException, status

from app.ratelimit import get_redis, _client_ip

TURNSTILE_SECRET = os.getenv("TURNSTILE_SECRET_KEY", "")
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
VERIFIED_TTL_SECONDS = 86400  # remember a verified session for 24h


async def _verify_token(token: str, remoteip: str) -> bool:
    data = {"secret": TURNSTILE_SECRET, "response": token}
    if remoteip and remoteip != "unknown":
        data["remoteip"] = remoteip
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(VERIFY_URL, data=data)
            return bool(resp.json().get("success"))
    except Exception as exc:  # noqa: BLE001
        print(f"[captcha] Turnstile verify call failed: {exc!r}")
        return False


async def enforce_chat_captcha(session_id: str, token: str | None, request: Request) -> None:
    """
    Raise 403 if the session's first message lacks a valid Turnstile token.
    No-op when bot protection is disabled or the session is already verified.
    """
    if not TURNSTILE_SECRET:
        return  # bot protection disabled (no secret configured)

    r = get_redis()
    verified_key = f"captcha_ok:{session_id}"
    try:
        if await r.get(verified_key):
            return  # this session already passed
    except Exception as exc:  # noqa: BLE001 - if Redis is down, fall through to verify
        print(f"[captcha] redis check failed ({exc!r}); verifying token directly.")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Captcha required.",
        )

    if not await _verify_token(token, _client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Captcha verification failed.",
        )

    try:
        await r.set(verified_key, "1", ex=VERIFIED_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001
        print(f"[captcha] failed to cache verified session ({exc!r}).")


async def enforce_form_captcha(token: str | None, request: Request) -> None:
    """
    Verify a Turnstile token for a stateless one-off form submit (no session
    memory, since each submit is independent). No-op when bot protection is
    disabled. Raises 403 on a missing or invalid token.
    """
    if not TURNSTILE_SECRET:
        return  # bot protection disabled (no secret configured)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Captcha required.",
        )

    if not await _verify_token(token, _client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Captcha verification failed.",
        )
