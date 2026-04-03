from rest_framework import serializers
from categories.models import Category


class CategoryInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["parent", "name", "description"]


class CategoryOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "parent", "name", "description", "products"]
        read_only_fields = fields
