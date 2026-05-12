"""Image validation and thumbnail generation."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


class InvalidImageError(ValueError):
    """Raised when uploaded image bytes cannot be processed."""


def register_heic_opener() -> None:
    """Register HEIC/HEIF support when the optional plugin is installed."""

    try:
        import pillow_heif  # type: ignore[import-not-found]

        pillow_heif.register_heif_opener()
    except ImportError:
        pass


def heic_conversion_available() -> bool:
    """Return whether Pillow has a registered HEIC/HEIF decoder."""

    register_heic_opener()
    extensions = Image.registered_extensions()
    return extensions.get(".heic") is not None or extensions.get(".heif") is not None


def get_image_size(image_bytes: bytes) -> tuple[int, int]:
    """Return image dimensions after applying EXIF orientation."""

    try:
        register_heic_opener()
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            return image.size
    except (OSError, UnidentifiedImageError) as exc:
        raise InvalidImageError("Unsupported or invalid image file") from exc


def generate_webp_derivative(image_bytes: bytes, max_size: int, quality: int) -> bytes:
    """Generate a WebP derivative preserving aspect ratio and orientation."""

    try:
        register_heic_opener()
        with Image.open(BytesIO(image_bytes)) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((max_size, max_size))
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="WEBP", quality=quality)
            return output.getvalue()
    except (OSError, UnidentifiedImageError) as exc:
        raise InvalidImageError("Unsupported or invalid image file") from exc


def generate_thumbnail(image_bytes: bytes, max_size: int = 512) -> bytes:
    """Generate a WebP thumbnail preserving aspect ratio."""

    return generate_webp_derivative(image_bytes, max_size=max_size, quality=82)


def generate_preview(image_bytes: bytes, max_size: int = 2048) -> bytes:
    """Generate a WebP preview preserving aspect ratio."""

    return generate_webp_derivative(image_bytes, max_size=max_size, quality=88)
