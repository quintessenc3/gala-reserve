import factory

from apps.booking.models import Registration, RegistrationStatus, Ticket, TicketStatus
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


class TicketFactory(factory.django.DjangoModelFactory):
    '''
    Фабрика Ticket.
    '''

    registration = factory.SubFactory(RegistrationFactory)
    user = factory.SelfAttribute('registration.user')
    event = factory.SelfAttribute('registration.event')
    status = TicketStatus.VALID

    class Meta:
        model = Ticket
