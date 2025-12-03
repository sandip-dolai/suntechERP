from django.urls import path
from . import views

app_name = 'bom'

urlpatterns = [
    path('', views.bom_list, name='bom_list'),
    path('create/', views.bom_create, name='bom_create'),
    path('edit/<int:pk>/', views.bom_edit, name='bom_edit'),
    path('delete/<int:pk>/', views.bom_delete, name='bom_delete'),
    path('report/', views.bom_report, name='bom_report'),
]