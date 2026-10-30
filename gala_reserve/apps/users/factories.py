import factory

from apps.users.models import User

USER_TEST_PASSWORD = 'P@ssw0rd'


class UserFactory(factory.django.DjangoModelFactory):
    '''
    Фабрика User.
    '''

    username = factory.Sequence(lambda n: f'user_{n}')
    password = factory.django.Password(password=USER_TEST_PASSWORD)
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    bio = factory.Faker('text')
    photo = factory.django.ImageField()
    is_email_verified = False
    is_active = True
    is_staff = False

    class Meta:
        model = User