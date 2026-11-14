from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view()),
    path("login/refresh/", TokenRefreshView.as_view()),
    path("logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
    path("users/", views.UserListView.as_view()),
    path("password-reset/", views.PasswordResetView.as_view()),
]
