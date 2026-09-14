import os

import httpx

from dotenv import load_dotenv

load_dotenv()

TURNSTILE_ENABLED = (
    os.getenv("TURNSTILE_ENABLED", "false").lower()
    == "true"
)

TURNSTILE_SECRET_KEY = os.getenv(
    "TURNSTILE_SECRET_KEY",
    ""
)

TURNSTILE_VERIFY_URL = (
    "https://challenges.cloudflare.com/"
    "turnstile/v0/siteverify"
)


async def verify_turnstile(token: str) -> bool:

    if not TURNSTILE_ENABLED:
        return True

    if not token:
        return False

    if not TURNSTILE_SECRET_KEY:
        return False

    try:
        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:

            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data={
                    "secret": TURNSTILE_SECRET_KEY,
                    "response": token,
                },
            )

        if response.status_code != 200:
            return False

        data = response.json()

        return data.get("success") is True

    except Exception:
        return False