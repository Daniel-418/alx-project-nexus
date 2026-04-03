import pytest

from categories.tests.factories import CategoryFactory
from categories.models import Category

pytestmark = pytest.mark.django_db


@pytest.fixture
def category():
    yield CategoryFactory()


class TestCategoryCreation:
    # test that a category is successfully created and persisted with its products
    def test_that_a_category_can_be_created(self, category):
        assert Category.objects.filter(id=category.id).exists()

    def test_category_with_parent(self):
        parent = CategoryFactory()
        child = CategoryFactory(parent=parent)

        child_from_db = Category.objects.get(id=child.id)
        assert child_from_db.parent == parent

    def test_root_category_has_no_parent(self, category):
        assert category.parent is None
