from types import SimpleNamespace

import pytest
from apps.core.serializer_validators import (
    BaseTwoFieldsValidator,
    FieldGreaterThanOtherValidator,
)
from rest_framework import serializers


@pytest.fixture
def serializer_class() -> serializers.Serializer:
    class Serializer(serializers.Serializer):
        first = serializers.IntegerField(required=False)
        second = serializers.IntegerField(required=False)

    return Serializer


class TestBaseTwoFieldsValidator:
    class Validator(BaseTwoFieldsValidator):
        def is_invalid(self, value, other_value):
            return value <= other_value

    validator = Validator(field='first', other_field='second')

    @pytest.fixture(autouse=True)
    def setup(self, serializer_class: serializers.Serializer):
        self.serializer_class = serializer_class
        self.serializer_class.validators = (self.validator,)

    def test_first_field_must_exist_in_serializer(self):
        serializer = self.serializer_class(data={'second': 2})
        serializer.fields.pop('first')

        with pytest.raises(AssertionError):
            serializer.is_valid()

    def test_second_field_must_exist_in_serializer(self):
        serializer = self.serializer_class(data={'first': 3})
        serializer.fields.pop('second')

        with pytest.raises(AssertionError):
            serializer.is_valid()

    def test_uses_default_message_when_validation_fails(self):
        serializer = self.serializer_class(data={'first': 3, 'second': 4})

        assert not serializer.is_valid()
        assert serializer.errors['first'] == [
            'Некорректное соотношение полей first и second.'
        ]

    def test_uses_custom_message_when_validation_fails(self):
        serializer = self.serializer_class()
        validator = self.Validator(
            field='first',
            other_field='second',
            message='Первое поле должно быть больше второго.',
        )

        with pytest.raises(serializers.ValidationError) as exc_info:
            validator({'first': 3, 'second': 4}, serializer)

        assert exc_info.value.detail == {
            'first': 'Первое поле должно быть больше второго.'
        }

    def test_uses_data_values_without_instance(self):
        serializer = self.serializer_class(data={'first': 5, 'second': 3})

        assert serializer.is_valid()
        assert serializer.validated_data == {'first': 5, 'second': 3}

    def test_uses_instance_values_when_data_is_empty(self):
        instance = SimpleNamespace(first=5, second=3)
        serializer = self.serializer_class(instance=instance, data={}, partial=True)

        assert serializer.is_valid()

    def test_data_values_override_instance_values(self):
        instance = SimpleNamespace(first=10, second=4)
        serializer = self.serializer_class(
            instance=instance,
            data={'first': 3},
            partial=True,
        )

        assert not serializer.is_valid()
        assert serializer.errors['first'] == [
            'Некорректное соотношение полей first и second.'
        ]

    def test_skips_comparison_when_either_value_is_missing(self):
        serializer = self.serializer_class(data={'first': 5})

        assert serializer.is_valid()


class TestFieldGreaterThanOtherValidator:
    @pytest.fixture(autouse=True)
    def setup(self, serializer_class: serializers.Serializer):
        self.serializer_class = serializer_class
        self.serializer_class.validators = (FieldGreaterThanOtherValidator('first', 'second'),)

    def test_field_gt_other_pass_validation(self):
        serializer = self.serializer_class(data={'first': 5, 'second': 3})

        assert serializer.is_valid()

    def test_field_eq_other_dont_pass_validation(self):
        serializer = self.serializer_class(data={'first': 3, 'second': 3})

        assert not serializer.is_valid()
        assert {'first'} == set(serializer.errors.keys())

    def test_field_lt_other_dont_pass_validation(self):
        serializer = self.serializer_class(data={'first': 2, 'second': 3})
        
        assert not serializer.is_valid()
        assert {'first'} == set(serializer.errors.keys())