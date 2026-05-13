"""Reverse-geocoding service: provider abstraction, caching, and rate limiting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Protocol

from app.core.config import Settings


@dataclass(frozen=True)
class GeocodingResult:
    """Normalized location result across providers."""

    name: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    district: str | None = None
    road: str | None = None


class GeocodingProvider(Protocol):
    """Interface for reverse-geocoding implementations."""

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        ...


class NoopProvider:
    """Returns None; used when geocoding is disabled or in test mode."""

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        return None


class NominatimProvider:
    """Calls the Nominatim reverse-geocoding API (OpenStreetMap)."""

    def __init__(self, settings: Settings) -> None:
        self._endpoint = settings.nominatim_endpoint.rstrip("/")
        self._timeout = settings.geocoding_timeout_seconds
        self._client: object = None

    def _get_client(self):
        import httpx

        if self._client is None:
            self._client = httpx.Client(
                headers={"User-Agent": "KinFrame/0.2"},
                timeout=self._timeout,
            )
        return self._client

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        import httpx

        url = f"{self._endpoint}/reverse"
        params = {"lat": lat, "lon": lng, "format": "jsonv2", "addressdetails": 1}
        try:
            response = self._get_client().get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        if not data or "address" not in data:
            return None

        addr = data["address"]
        return GeocodingResult(
            name=data.get("display_name"),
            country=addr.get("country"),
            region=addr.get("state"),
            city=addr.get("city") or addr.get("town") or addr.get("village"),
            district=addr.get("county") or addr.get("suburb"),
            road=addr.get("road") or addr.get("pedestrian"),
        )


class AmapProvider:
    """Calls the AMap (Gaode) reverse-geocoding Web API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.amap_api_key:
            raise ValueError("AMap API key is required when geocoding_provider='amap'")
        self._api_key = settings.amap_api_key
        self._timeout = settings.geocoding_timeout_seconds
        self._client: object = None

    def _get_client(self):
        import httpx

        if self._client is None:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        import httpx

        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "key": self._api_key,
            "location": f"{lng},{lat}",
            "extensions": "base",
            "output": "JSON",
        }
        try:
            response = self._get_client().get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError:
            return None

        data = response.json()
        if data.get("status") != "1":
            return None

        regeo = data.get("regeocode", {})
        addr = regeo.get("addressComponent", {})
        if not addr:
            return None

        street_number = addr.get("streetNumber") or {}

        def _road_from_amap() -> str | None:
            if isinstance(street_number, dict):
                street = street_number.get("street") or ""
                number = street_number.get("number") or ""
                combined = f"{street}{number}".strip()
                if combined:
                    return combined
            return str(street_number) if street_number and not isinstance(street_number, dict) else None

        return GeocodingResult(
            name=regeo.get("formatted_address"),
            country=addr.get("country"),
            region=addr.get("province"),
            city=addr.get("city") or addr.get("district"),
            district=addr.get("township") or addr.get("district"),
            road=_road_from_amap(),
        )


@dataclass
class GeocodingService:
    """Coordinates geocoding: provider selection, caching, and rate limiting."""

    _provider: GeocodingProvider
    _enabled: bool
    _provider_name: str
    _rate_limit_interval: float
    _cache: dict[tuple[float, float], GeocodingResult | None] = field(default_factory=dict)
    _last_call: float = 0.0

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def enabled(self) -> bool:
        return self._enabled

    def reverse_geocode(self, lat: float, lng: float) -> GeocodingResult | None:
        if not self._enabled:
            return None
        key = (round(lat, 4), round(lng, 4))
        if key in self._cache:
            return self._cache[key]
        now = time.monotonic()
        wait = self._rate_limit_interval - (now - self._last_call)
        if wait > 0:
            time.sleep(wait)
        result = self._provider.reverse_geocode(lat, lng)
        self._last_call = time.monotonic()
        self._cache[key] = result
        return result


def create_geocoding_service(settings: Settings) -> GeocodingService:
    provider: GeocodingProvider
    provider_name = settings.geocoding_provider
    enabled = settings.geocoding_enabled and provider_name != "noop"
    if not enabled:
        provider = NoopProvider()
        provider_name = "noop"
    elif provider_name == "amap":
        provider = AmapProvider(settings)
    else:
        provider = NominatimProvider(settings)
    rate_limit_interval = 1.0 / settings.geocoding_rate_limit_per_second
    return GeocodingService(
        _provider=provider,
        _enabled=enabled,
        _provider_name=provider_name,
        _rate_limit_interval=rate_limit_interval,
    )
