import pytest
from apps.events.models import EventStatus
from apps.events.serializer_validators import EventPublishedAtMatchesStatusValidator
from django.utils import timezone
from rest_framework import serializers
from rest_framework.settings import api_settings


@pytest.fixture
def serializer_class():
    class Serializer(serializers.Serializer):
        status = serializers.ChoiceField(choices=EventStatus.choices)
        published_at = serializers.DateTimeField(required=False, allow_null=True)

    return Serializer


class TestEventPublishedAtMatchesStatusValidator:
    @pytest.fixture(autouse=True)
    def setup(self, serializer_class):
        self.serializer_class = serializer_class
        self.validator = EventPublishedAtMatchesStatusValidator(
            field='status',
            other_field='published_at',
        )
        self.serializer_class.validators = (self.validator,)

    def test_draft_with_no_published_at_is_valid(self):
        serializer = self.serializer_class(data={
            'status': EventStatus.DRAFT,
            'published_at': None,
        })

        assert serializer.is_valid()

    def test_non_draft_with_published_at_is_valid(self):
        serializer = self.serializer_class(data={
            'status': EventStatus.PUBLISHED,
            'published_at': timezone.now(),
        })

        assert serializer.is_valid()

    def test_draft_with_published_at_is_invalid(self):
        serializer = self.serializer_class(data={
            'status': EventStatus.DRAFT,
            'published_at': timezone.now(),
        })

        assert not serializer.is_valid()
        assert api_settings.NON_FIELD_ERRORS_KEY in serializer.errors

    def test_non_draft_without_published_at_is_invalid(self):
        serializer = self.serializer_class(data={
            'status': EventStatus.PUBLISHED,
            'published_at': None,
        })

        assert not serializer.is_valid()
        assert api_settings.NON_FIELD_ERRORS_KEY in serializer.errors
