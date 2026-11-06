from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import User, OneTimeCode


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


class EmailVerifyInputSerializer(serializers.Serializer):
    '''
    Сериализатор входных данных для верификации email.
    '''

    code = serializers.CharField(
        max_length=OneTimeCode.CODE_LENGTH, 
        min_length=OneTimeCode.CODE_LENGTH,
        validators=[
            RegexValidator(
                f'^[0-9]{{{OneTimeCode.CODE_LENGTH}}}$', 
                message='Код должен состоять из 6 цифр.'
            )
        ]
    )


class RequestEmailResetCodeInputSerializer(serializers.Serializer):
    '''
    Сериализатор входных данных для запроса кода сброса пароля.
    '''

    email = serializers.EmailField()