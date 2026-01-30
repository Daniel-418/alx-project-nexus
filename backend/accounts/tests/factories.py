# type: ignore
import factory

from accounts.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:  # pyright: ignore
        model = User

    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone_number = "306-850-9733"

    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted
        self.set_password(password)
