from rest_framework import exceptions, serializers


class BaseTwoFieldsValidator:
    """
    Базовый класс для валидаторов, основанных на двух полях.
    """

    requires_context = True
    message = "Некорректное соотношение полей {} и {}."

    def __init__(
        self,
        field: str,
        other_field: str,
        message: str | None = None
    ):
        self.field = field
        self.other_field = other_field

        if message is not None:
            self.message = message

    def __call__(
        self,
        attrs: dict,
        serializer: serializers.Serializer
    ):
        for field_name in (self.field, self.other_field):
            if field_name not in serializer.fields:
                raise AssertionError(
                    f'Поле "{field_name}" должно быть объявлено в сериализаторе.'
                )

        instance = serializer.instance

        value = attrs.get(
            self.field,
            getattr(instance, self.field, None) if instance else None
        )

        other_value = attrs.get(
            self.other_field,
            getattr(instance, self.other_field, None) if instance else None
        )

        if value is None or other_value is None:
            return

        if self.is_invalid(value, other_value):
            raise exceptions.ValidationError({
                self.field: self.message.format(
                    self.field,
                    self.other_field
                )
            })

    def is_invalid(self, value, other_value) -> bool:
        raise NotImplementedError