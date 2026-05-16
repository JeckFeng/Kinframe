"""Shared pytest fixtures and environment patches for backend tests."""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
import fastapi.concurrency
import fastapi.dependencies.utils
import fastapi.routing
import starlette.datastructures
import starlette.concurrency


@pytest.fixture(autouse=True)
def inline_threadpool(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run sync FastAPI handlers inline inside tests.

    The sandbox used for automated verification blocks thread creation, which
    causes FastAPI/Starlette sync route execution to hang. Backend tests use
    in-memory SQLite and fake storage, so running these call sites inline is
    sufficient and keeps the HTTP tests deterministic.
    """

    async def run_inline(func, *args, **kwargs):
        return func(*args, **kwargs)

    @asynccontextmanager
    async def inline_contextmanager(cm):
        try:
            yield cm.__enter__()
        except Exception as exc:
            suppress = cm.__exit__(type(exc), exc, exc.__traceback__)
            if not suppress:
                raise
        else:
            cm.__exit__(None, None, None)

    monkeypatch.setattr(starlette.concurrency, "run_in_threadpool", run_inline)
    monkeypatch.setattr(starlette.datastructures, "run_in_threadpool", run_inline)
    monkeypatch.setattr(fastapi.routing, "run_in_threadpool", run_inline)
    monkeypatch.setattr(fastapi.dependencies.utils, "run_in_threadpool", run_inline)
    monkeypatch.setattr(fastapi.concurrency, "contextmanager_in_threadpool", inline_contextmanager)
    monkeypatch.setattr(fastapi.dependencies.utils, "contextmanager_in_threadpool", inline_contextmanager)
