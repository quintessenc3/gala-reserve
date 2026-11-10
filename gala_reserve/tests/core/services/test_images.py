from io import BytesIO

import pytest
from apps.core import error_codes
from apps.core.services import images
from apps.core.services.images import (
    ImageDimensionsTooLargeError,
    ImageTooLargeError,
    ImageUnsupportedFormatError,
    InvalidImageError,
    process_image,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

LIMITS = {
    'max_image_size_bytes': 10_000_000,
    'max_image_resolution_px': (4096, 4096),
    'thumbnail_size_px': (512, 512),
}


def make_image(image_format='PNG', size=(200, 100), exif=None):
    image = Image.new('RGB', size, color='red')
    buffer = BytesIO()
    save_options = {'exif': exif} if exif is not None else {}
    image.save(buffer, format=image_format, **save_options)

    extension = {'BMP': 'bmp', 'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[image_format]
    return SimpleUploadedFile(
        f'image.{extension}',
        buffer.getvalue(),
        content_type=f'image/{extension}',
    )


class TestProcessImage:
    def test_returns_resized_webp_and_leaves_original_untouched(self):
        upload = make_image('JPEG', size=(2000, 1000))
        original = upload.read()
        upload.seek(0)

        result = process_image(file=upload, **LIMITS)

        assert result.name.endswith('.webp')
        with Image.open(result) as output:
            assert output.format == 'WEBP'
            assert output.size == (512, 256)
        upload.seek(0)
        assert upload.read() == original

    def test_applies_exif_orientation(self):
        exif = Image.Exif()
        exif[0x0112] = 6

        result = process_image(
            file=make_image('JPEG', size=(200, 100), exif=exif),
            **LIMITS,
        )

        with Image.open(result) as output:
            assert output.size == (100, 200)
            assert len(output.getexif()) == 0

    def test_rejects_file_larger_than_limit(self):
        with pytest.raises(ImageTooLargeError) as exc_info:
            process_image(file=make_image(), **{**LIMITS, 'max_image_size_bytes': 1})

        assert exc_info.value.code == error_codes.IMAGE_TOO_LARGE

    def test_rejects_unsupported_format(self):
        with pytest.raises(ImageUnsupportedFormatError) as exc_info:
            process_image(file=make_image('BMP'), **LIMITS)

        assert exc_info.value.code == error_codes.UNSUPPORTED_IMAGE_FORMAT

    @pytest.mark.parametrize('size', ((4097, 100), (100, 4097)))
    def test_rejects_image_exceeding_width_or_height_limit(self, size):
        with pytest.raises(ImageDimensionsTooLargeError) as exc_info:
            process_image(file=make_image(size=size), **LIMITS)

        assert exc_info.value.code == error_codes.IMAGE_DIMENSIONS_TOO_LARGE

    def test_converts_decompression_bomb_error_to_dimensions_error(self, monkeypatch):
        def raise_decompression_bomb(_file):
            raise Image.DecompressionBombError

        monkeypatch.setattr(images.Image, 'open', raise_decompression_bomb)

        with pytest.raises(ImageDimensionsTooLargeError) as exc_info:
            process_image(file=make_image(), **LIMITS)

        assert exc_info.value.code == error_codes.IMAGE_DIMENSIONS_TOO_LARGE

    def test_rejects_invalid_image(self):
        invalid_image = SimpleUploadedFile(
            'image.jpg',
            b'not an image',
            content_type='image/jpeg',
        )

        with pytest.raises(InvalidImageError) as exc_info:
            process_image(file=invalid_image, **LIMITS)

        assert exc_info.value.code == error_codes.INVALID_IMAGE

    def test_converts_syntax_error_to_invalid_image(self, monkeypatch):
        def raise_syntax_error(_file):
            raise SyntaxError

        monkeypatch.setattr(images.Image, 'open', raise_syntax_error)

        with pytest.raises(InvalidImageError) as exc_info:
            process_image(file=make_image(), **LIMITS)

        assert exc_info.value.code == error_codes.INVALID_IMAGE
