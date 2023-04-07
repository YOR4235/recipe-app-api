from rest_framework import generics, authentication, permissions
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from core.models import User

from user.serializers import (
    UserSerializer,
    AuthTokenSerializer,
    PasswordChangeSerializer,
)


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


class CreateTokenView(ObtainAuthToken):
    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeViewset(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer

    def get_object(self):
        email = str(self.kwargs['email'])
        user = User.objects.get(email=email)
        return user
