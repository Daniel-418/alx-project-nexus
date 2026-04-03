# type: ignore
import factory
from categories.models import Category


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    parent = None
    name = factory.Faker("word")
    description = factory.Faker("text")
