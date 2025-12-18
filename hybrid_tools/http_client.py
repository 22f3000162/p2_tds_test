"""
Shared HTTP client with connection pooling and retry logic.
Provides a single async HTTP client for all tools.
"""

import httpx
import asyncio
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()


# --------------------------------------------------
# CLIENT FACTORY
# --------------------------------------------------
async def get_http_client() -> httpx.AsyncClient:
    """
    Get or create the global async HTTP client with connection pooling.
    """
    global _client

    async with _client_lock:
        if _client is None:
            limits = httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            )

            _client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=limits,
                follow_redirects=True,
                http2=True,
            )

            print("[HTTP_CLIENT] ✓ Initialized (pool=100, keepalive=20)")

        return _client


# --------------------------------------------------
# CLEANUP
# --------------------------------------------------
async def close_http_client():
    """Close and cleanup the global HTTP client."""
    global _client

    async with _client_lock:
        if _client is not None:
            await _client.aclose()
            _client = None
            print("[HTTP_CLIENT] ✓ Closed connections")


# --------------------------------------------------
# RETRY CONFIG
# --------------------------------------------------
_retry_policy = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(
        (httpx.NetworkError, httpx.TimeoutException)
    ),
    reraise=True,
)


# --------------------------------------------------
# GET WITH RETRY
# --------------------------------------------------
@_retry_policy
async def get_with_retry(url: str, **kwargs) -> httpx.Response:
    """
    Perform GET request with retry on network/timeout errors.
    """
    client = await get_http_client()
    response = await client.get(url, **kwargs)
    response.raise_for_status()
    return response


# --------------------------------------------------
# POST WITH RETRY
# --------------------------------------------------
@_retry_policy
async def post_with_retry(url: str, **kwargs) -> httpx.Response:
    """
    Perform POST request with retry on network/timeout errors.
    """
    client = await get_http_client()
    response = await client.post(url, **kwargs)
    response.raise_for_status()
    return response


# --------------------------------------------------
# SAFE EXIT CLEANUP
# --------------------------------------------------
import atexit

def _cleanup():
    try:
        if asyncio.get_event_loop().is_running():
            return
        asyncio.run(close_http_client())
    except Exception:
        pass

atexit.register(_cleanup)
