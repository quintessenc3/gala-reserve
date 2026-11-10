import io
import uuid

from django.core.files import File
from django.core.files.base import ContentFile
from PIL import Image, ImageOps
from rest_framework import status

from apps.core import error_codes
from apps.core.exceptions import DomainError


class InvalidImageError(DomainError):
    code = error_codes.INVALID_IMAGE
    message = 'Файл не является корректным изображением.'
    http_status = status.HTTP_400_BAD_REQUEST


class ImageUnsupportedFormatError(InvalidImageError):
    code = error_codes.UNSUPPORTED_IMAGE_FORMAT
    message = 'Допустимы только JPEG, PNG и WEBP.'


class ImageTooLargeError(InvalidImageError):
    code = error_codes.IMAGE_TOO_LARGE
    message = 'Файл слишком большой.'


class ImageDimensionsTooLargeError(InvalidImageError):
    code = error_codes.IMAGE_DIMENSIONS_TOO_LARGE
    message = 'Изображение слишком большое по ширине или высоте.'


ALLOWED_FORMATS = ('JPEG', 'PNG', 'WEBP')
OUTPUT_QUALITY = 85


def generate_image_name() -> str:
    '''
    Сервис генерации имени изображения.
    '''

    return f'{uuid.uuid4()}.webp'


def process_image(
        *, 
        file: File, 
        max_image_size_bytes: int,
        max_image_resolution_px: tuple[int, int],
        thumbnail_size_px: tuple[int, int]
    ) -> ContentFile:

    '''
    Сервис обработки изображения. Возвращает обработанную
    копию изображения.
    '''

    if file.size > max_image_size_bytes:
        raise ImageTooLargeError

    file.seek(0)

    try:
        with Image.open(file) as source:
            if source.format not in ALLOWED_FORMATS:
                raise ImageUnsupportedFormatError

            width, height = source.size
            max_width, max_height = max_image_resolution_px
            if width > max_width or height > max_height:
                raise ImageDimensionsTooLargeError
            
            image = ImageOps.exif_transpose(source)
            image.thumbnail(thumbnail_size_px, Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            image.save(buffer, format='WEBP', quality=OUTPUT_QUALITY)
    except Image.DecompressionBombError:
        raise ImageDimensionsTooLargeError
    except (OSError, SyntaxError):
        raise InvalidImageError

    return ContentFile(buffer.getvalue(), name=generate_image_name())