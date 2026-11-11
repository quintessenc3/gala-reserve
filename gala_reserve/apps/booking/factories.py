import factory

from apps.booking.models import Registration, RegistrationStatus
from apps.events.factories import EventFactory
from apps.users.factories import UserFactory


class RegistrationFactory(factory.django.DjangoModelFactory):
    '''
    Фабрика Registration.
    '''

    user = factory.SubFactory(UserFactory)
    event = factory.SubFactory(EventFactory)
    status = RegistrationStatus.PENDING

    class Meta:
        model = Registration
