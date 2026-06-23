from io import BytesIO
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError


def _int_setting(name, default):
    try:
        return int(getattr(settings, name, default))
    except (TypeError, ValueError):
        return default


def validate_upload_image_size(uploaded_file):
    """Reject very large phone photos before Django spends time processing them."""
    max_mb = _int_setting('RENTWISE_MAX_IMAGE_UPLOAD_MB', 8)
    max_bytes = max_mb * 1024 * 1024
    if uploaded_file and getattr(uploaded_file, 'size', 0) > max_bytes:
        raise ValidationError(f'Image file too large. Maximum size is {max_mb} MB.')


def compress_uploaded_image(image_file):
    """
    Resize and compress uploaded listing photos before they are saved.

    This keeps caretaker uploads practical for phone photos while protecting storage and
    page speed. It returns a Django ContentFile ready for ImageField storage.
    """
    if not image_file:
        return image_file

    validate_upload_image_size(image_file)

    try:
        image_file.seek(0)
    except Exception:
        pass

    try:
        image = Image.open(image_file)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError('Upload a valid image file.') from exc

    image = ImageOps.exif_transpose(image)

    if image.mode not in ('RGB', 'L'):
        image = image.convert('RGB')
    elif image.mode == 'L':
        image = image.convert('RGB')

    max_width = _int_setting('RENTWISE_IMAGE_MAX_WIDTH', 1600)
    max_height = _int_setting('RENTWISE_IMAGE_MAX_HEIGHT', 1200)
    quality = _int_setting('RENTWISE_IMAGE_JPEG_QUALITY', 80)

    image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format='JPEG', quality=quality, optimize=True, progressive=True)
    output.seek(0)

    original_name = os.path.splitext(os.path.basename(getattr(image_file, 'name', 'upload')))[0]
    safe_name = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '-' for ch in original_name).strip('-') or 'listing-photo'
    new_name = f'{safe_name}-{uuid.uuid4().hex[:8]}.jpg'
    return ContentFile(output.read(), name=new_name)
