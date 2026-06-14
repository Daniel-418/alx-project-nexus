import uuid
from django.db import models


class Category(models.Model):
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField()

    class Meta:
        ordering = ["name"]
