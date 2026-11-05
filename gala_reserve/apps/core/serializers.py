from rest_framework import serializers


class MessageOutputSerializer(serializers.Serializer):
    '''
    Сериализатор API ответа с сообщением.
    '''

    message = serializers.CharField()