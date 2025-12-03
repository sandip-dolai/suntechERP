from django.urls import path
from . import views

app_name = 'indent'

urlpatterns = [
    path('', views.indent_list, name='indent_list'),
    path('create/', views.indent_create, name='indent_create'),
    path('edit/<int:pk>/', views.indent_edit, name='indent_edit'),
    path('delete/<int:pk>/', views.indent_delete, name='indent_delete'),
    path('report/', views.indent_report, name='indent_report'),
]