from django.core.files import File
from rest_framework import exceptions

from apps.core.services.images import process_image
from apps.users.models import User


def user_set_photo(*, user_id: int, photo: File) -> User:
    '''
    Сервис для установки фотографии профиля пользователя.
    '''

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        raise exceptions.NotFound(detail='Пользователя не существует.')

    processed = process_image(
        file=photo,
        max_image_size_bytes=User.MAX_PHOTO_FILE_SIZE_BYTES,
        max_image_resolution_px=User.MAX_PHOTO_RESOLUTION,
        thumbnail_size_px=User.THUMBNAIL_SIZE_PX
    )

    user.photo.save(processed.name, processed, save=False)
    user.save(update_fields=['photo'])
    
    return user