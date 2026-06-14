# type: ignore
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.views import APIView, Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.serializers import (
    CustomUserSerializerInput,
    CustomUserSerializerOutput,
    LoginSerializer,
    UserUpdateSerializer,
)


class Register(APIView):
    """Register a user"""

    permission_classes = [AllowAny]

    @extend_schema(
        request=CustomUserSerializerInput, responses={201, CustomUserSerializerOutput}
    )
    # validate input, create user, and return JWT tokens
    def post(self, request):
        serializer = CustomUserSerializerInput(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user": CustomUserSerializerOutput(user).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Login(APIView):
    """
    Get a token for a user
    """

    @extend_schema(request=LoginSerializer, responses={200, "Token response"})
    # validate credentials and return JWT tokens
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})

        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "login successful",
            },
            status=status.HTTP_200_OK,
        )


# returns and updates the authenticated user's own profile
class UserProfile(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CustomUserSerializerOutput(instance=request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CustomUserSerializerOutput(instance=request.user).data)
