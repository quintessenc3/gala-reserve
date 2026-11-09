from apps.core.serializer_validators import BaseTwoFieldsValidator
from apps.events.models import EventStatus


class EventPublishedAtMatchesStatusValidator(BaseTwoFieldsValidator):
    '''
    Валидатор того, что дата публикации должна быть пустой у черновика 
    и заполненной при других статусах.
    '''
    
    message = 'Дата публикации должна быть пустой у черновика и заполненной при других статусах.'
    multi_field_error = True
    
    def is_invalid(self, status, published_at) -> bool:
        return bool(
            (status == EventStatus.DRAFT and published_at is not None) or
            (status != EventStatus.DRAFT and published_at is None)
        )