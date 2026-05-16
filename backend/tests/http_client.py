"""Synchronous ASGI test client for backend API tests."""

from __future__ import annotations

from typing import Any

import anyio
import httpx
from fastapi import FastAPI


class TestClient:
    """Small sync wrapper around ``httpx.AsyncClient`` for ASGI apps."""

    __test__ = False

    def __init__(self, app: FastAPI, *, base_url: str = "http://testserver") -> None:
        self._app = app
        self._base_url = base_url
        self._cookies = httpx.Cookies()

    def __enter__(self) -> TestClient:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def close(self) -> None:
        return None

    @property
    def app(self) -> FastAPI:
        return self._app

    @property
    def cookies(self) -> httpx.Cookies:
        return self._cookies

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return anyio.run(self._request_async, method, url, kwargs)

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    async def _request_async(self, method: str, url: str, kwargs: dict[str, Any]) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self._app),
            base_url=self._base_url,
            follow_redirects=True,
            cookies=self._cookies,
        ) as client:
            response = await client.request(method, url, **kwargs)
            self._cookies = client.cookies
            return response
