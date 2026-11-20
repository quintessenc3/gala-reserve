from types import SimpleNamespace

import pytest
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.permissions import IsTicketEventOwnerOrAdmin
from apps.events.factories import EventFactory
from rest_framework import status
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate

factory = APIRequestFactory()


@pytest.fixture
def mock_view():
    class MockView(RetrieveAPIView):
        ticket = None
        permission_classes = (IsTicketEventOwnerOrAdmin,)

        def get_object(self):
            self.check_object_permissions(self.request, self.ticket)
            return self.ticket

        def retrieve(self, request, *args, **kwargs):
            ticket = self.get_object()
            return Response({'ticket_id': ticket.pk})

    return MockView


def make_get_request(user_for_request):
    request = factory.get('/')
    force_authenticate(request, user=user_for_request)
    return request


class TestIsTicketEventOwnerOrAdmin:
    @pytest.mark.parametrize('is_event_owner, is_admin, expected', [
            (True, False, status.HTTP_200_OK),
            (False, True, status.HTTP_200_OK),
            (False, False, status.HTTP_403_FORBIDDEN),
    ])
    def test_has_object_permission(
        self,
        user,
        other_user,
        mock_view,
        is_event_owner,
        is_admin,
        expected,
    ):
        event = EventFactory.create(user=user)
        registration = RegistrationFactory.create(event=event, user=other_user)
        ticket = TicketFactory.create(registration=registration)
        request_user = user if is_event_owner else other_user
        request_user.is_staff = is_admin

        response = mock_view.as_view(ticket=ticket)(
            make_get_request(request_user)
        )

        assert response.status_code == expected

    def test_has_object_permission_returns_false_without_user(self, db):
        permission = IsTicketEventOwnerOrAdmin()
        ticket = TicketFactory.create()

        assert permission.has_object_permission(
            SimpleNamespace(user=None),
            None,
            ticket,
        ) == False

    def test_has_object_permission_returns_false_without_event(self, user):
        permission = IsTicketEventOwnerOrAdmin()

        assert permission.has_object_permission(
            SimpleNamespace(user=user),
            None,
            SimpleNamespace(),
        ) == False

    def test_has_object_permission_returns_false_without_event_user_id(self, user):
        permission = IsTicketEventOwnerOrAdmin()
        ticket = SimpleNamespace(event=SimpleNamespace())

        assert permission.has_object_permission(
            SimpleNamespace(user=user),
            None,
            ticket,
        ) == False
