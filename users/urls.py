from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import CustomLoginView
from . import views
app_name = 'users'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='users:login'), name='logout'),
    # path('send/', views.send_mail_page)

]