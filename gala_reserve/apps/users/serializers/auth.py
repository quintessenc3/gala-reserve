from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import User


class RegisterInputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных регистрационных данных пользователя.
    '''

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'validators': [validate_password]}
        }


class RegisterOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных пользователя после регистрации.
    '''

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')
        read_only_fields = fields