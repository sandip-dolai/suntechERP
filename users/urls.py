from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import CustomLoginView
from . import views

app_name = "users"

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page="users:login"), name="logout"),
    path("manage/", views.user_list, name="user_list"),
    path("manage/create/", views.user_create, name="user_create"),
    path("manage/<int:user_id>/edit/", views.user_edit, name="user_edit"),
]
