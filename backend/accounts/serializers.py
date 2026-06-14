# type: ignore
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from accounts.models import User


# strips sensitive fields from user output
class CustomUserSerializerOutput(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password", "is_staff", "is_superuser", "groups", "user_permissions"]


class CustomUserSerializerInput(serializers.ModelSerializer):
    """
    Serializes fields passed to register view
    """

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone_number"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {
            "password": {"write_only": True, "validators": [validate_password]},
        }

    # pop password, hash it, and save the user
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number"]


class LoginSerializer(serializers.Serializer):
    """
    Serializes fields passed to login view
    """

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    # authenticate credentials and raise error if invalid
    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        user = User.objects.filter(email=email).first()

        user = authenticate(
            request=self.context.get("request"), username=email, password=password
        )
        if not user:
            raise serializers.ValidationError({"details": "invalid email or password"})

        return user
