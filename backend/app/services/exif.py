"""EXIF extraction through ExifTool with safe fallbacks."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile

from app.services.images import get_image_size


@dataclass(frozen=True)
class ExtractedMetadata:
    """Normalized metadata extracted from an image."""

    width: int | None
    height: int | None
    taken_at: datetime
    gps_lat: float | None
    gps_lng: float | None
    camera_make: str | None
    camera_model: str | None
    exif_json: dict | None


def _parse_exif_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.split("+", maxsplit=1)[0].split("-", maxsplit=1)[0]
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(normalized, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _run_exiftool(path: Path) -> dict | None:
    try:
        result = subprocess.run(
            ["exiftool", "-json", "-n", str(path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or not parsed or not isinstance(parsed[0], dict):
        return None
    return parsed[0]


def extract_metadata(
    image_bytes: bytes,
    filename_suffix: str,
    uploaded_at: datetime,
) -> ExtractedMetadata:
    """Extract normalized EXIF metadata and fall back to upload time."""

    width, height = get_image_size(image_bytes)
    suffix = filename_suffix if filename_suffix.startswith(".") else f".{filename_suffix}"
    with tempfile.NamedTemporaryFile(suffix=suffix) as temp_file:
        temp_file.write(image_bytes)
        temp_file.flush()
        exif = _run_exiftool(Path(temp_file.name))

    taken_at = uploaded_at
    gps_lat = None
    gps_lng = None
    camera_make = None
    camera_model = None

    if exif is not None:
        taken_at = (
            _parse_exif_datetime(exif.get("DateTimeOriginal"))
            or _parse_exif_datetime(exif.get("CreateDate"))
            or uploaded_at
        )
        gps_lat_value = exif.get("GPSLatitude")
        gps_lng_value = exif.get("GPSLongitude")
        gps_lat = gps_lat_value if isinstance(gps_lat_value, int | float) else None
        gps_lng = gps_lng_value if isinstance(gps_lng_value, int | float) else None
        camera_make = exif.get("Make") if isinstance(exif.get("Make"), str) else None
        camera_model = exif.get("Model") if isinstance(exif.get("Model"), str) else None

    return ExtractedMetadata(
        width=width,
        height=height,
        taken_at=taken_at,
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        camera_make=camera_make,
        camera_model=camera_model,
        exif_json=exif,
    )
