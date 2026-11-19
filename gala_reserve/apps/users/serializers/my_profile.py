from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, validators

from apps.users.models import User


class MyProfileOutputSerializer(serializers.ModelSerializer):
    '''
    Представление для вывода информации о себе.
    '''

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'bio', 'photo', 'date_joined', 'is_staff')


class MyProfileUpdateSerializer(serializers.ModelSerializer):
    '''
    Представление для обновления данных своего профиля.
    '''

    def get_fields(self):
        fields = super().get_fields()
        fields['username'].validators.append(
            validators.UniqueValidator(
                queryset=User.objects.all(),
                message='Пользователь с таким именем пользователя уже существует.',
                lookup='iexact'
            )
        )
        return fields

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'bio')


class PasswordResetByOldPasswordInputSerializer(serializers.Serializer):
    '''
    Сериализатор входных данных для сброса пароля по старому паролю.
    '''

    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])


class MyProfilePhotoUploadSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных данных для обновления фотографии пользователя.
    '''

    class Meta:
        model = User
        fields = ('photo',)
        extra_kwargs = {
            'photo': {'required': True}
        }