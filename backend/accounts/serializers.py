from rest_framework import serializers
from accounts.models import User


class CustomUserSerializerOutput(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password"]


class CustomUserSerializerInput(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone_number"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
