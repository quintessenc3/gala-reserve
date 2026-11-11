from django import forms
from django_filters import FilterSet, filters
from django_filters.fields import IsoDateTimeField
from rest_framework.exceptions import ValidationError

from apps.events.models import Event, EventStatus


class EventFilter(FilterSet):
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    start_from = filters.IsoDateTimeFilter(
        'start_at',
        'gte',
        input_formats=[
            IsoDateTimeField.ISO_8601,
            *forms.DateTimeField.input_formats
        ]
    )
    start_to = filters.IsoDateTimeFilter(
        'start_at',
        'lte',
        input_formats=[
            IsoDateTimeField.ISO_8601,
            *forms.DateTimeField.input_formats
        ]
    )
    status = filters.ChoiceFilter(
        'status', 
        choices=[
            choice for choice in EventStatus.choices if choice[0] != EventStatus.DRAFT
        ]
    )
    ordering = filters.OrderingFilter(fields={
        'start_at': 'start_at',
        'price': 'price',
        'created_at': 'created_at',
        'seats_taken': 'popularity'
    })

    def filter_queryset(self, queryset):
        data = self.form.cleaned_data

        price_min, price_max = data.get('price_min', None), data.get('price_max', None)
        if price_min is not None and price_max is not None and price_min > price_max:
            raise ValidationError({'price_min': 'Минимальная цена не может быть больше максимальной цены.'})

        start_from, start_to = data.get('start_from', None), data.get('start_to', None)
        if start_from is not None and start_to is not None and start_from > start_to:
            raise ValidationError({'start_from': 'Минимальный порог начала мероприятия не может быть больше '
                                   'максимального порога начала мероприятия.'})

        return super().filter_queryset(queryset)

    class Meta:
        model = Event
        fields = ('category', 'user')