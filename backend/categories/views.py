# Create your views here.
from categories.models import Category
from categories.serializers import CategoryInputSerializer, CategoryOutputSerializer
from core.views import BaseCatalogViewset


class CategoryViewset(BaseCatalogViewset):
    queryset = Category.objects.all()
    input_serializer_class = CategoryInputSerializer
    output_serializer_class = CategoryOutputSerializer
