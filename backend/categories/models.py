import uuid
from django.db import models
from products.models import Product


# Create your models here.
class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField()
    products = models.ManyToManyField(Product, related_name="categories")
