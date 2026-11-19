from io import BytesIO

import pytest
from apps.users.models import User
from apps.users.services.profile import user_set_photo
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework import exceptions


def make_photo(size=(2000, 1000)):
    photo = Image.new('RGB', size, color='red')
    buffer = BytesIO()
    photo.save(buffer, format='PNG')

    return SimpleUploadedFile(
        'image.png',
        buffer.getvalue(),
        content_type='image/png',
    )


class TestUserSetPhoto:
    def test_replaces_user_photo_with_resized_webp(self, user):
        user.photo.save('old.png', ContentFile(b'old image'), save=True)
        old_photo_name = user.photo.name

        updated_user = user_set_photo(
            user_id=user.pk,
            photo=make_photo(size=(3000, 1500)),
        )
        user.refresh_from_db()

        assert updated_user.pk == user.pk
        assert user.photo.name != old_photo_name
        assert user.photo.name.endswith('.webp')
        with Image.open(user.photo) as image:
            assert image.format == 'WEBP'
            assert image.size[0] <= User.THUMBNAIL_SIZE_PX[0]
            assert image.size[1] <= User.THUMBNAIL_SIZE_PX[1]

    def test_user_does_not_exist(self, db):
        with pytest.raises(exceptions.NotFound):
            user_set_photo(user_id=0, photo=make_photo())
