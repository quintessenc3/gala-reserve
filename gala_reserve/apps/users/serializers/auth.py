from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.users.models import OneTimeCode, User


class RegisterInputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных регистрационных данных пользователя.
    '''

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'validators': [UniqueValidator(queryset=User.objects.all(), lookup='iexact')]},
            'username': {'validators': [UniqueValidator(queryset=User.objects.all(), lookup='iexact')]},
            'password': {'validators': [validate_password]},
        }


class RegisterOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных пользователя после регистрации.
    '''

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')
        read_only_fields = fields


class EmailVerifyInputSerializer(serializers.Serializer):
    '''
    Сериализатор входных данных для верификации email.
    '''

    code = serializers.CharField(validators=[RegexValidator(OneTimeCode.CODE_REGEX)])


class RequestEmailResetCodeInputSerializer(serializers.Serializer):
    '''
    Сериализатор входных данных для запроса кода сброса пароля.
    '''

    email = serializers.EmailField()


class PasswordResetByCodeInputSerializer(serializers.Serializer):
    '''
    Сериализатор входных данных для сброса пароля по коду.
    '''

    email = serializers.EmailField()
    code = serializers.CharField(validators=[RegexValidator(OneTimeCode.CODE_REGEX)])
    password = serializers.CharField(validators=[validate_password])