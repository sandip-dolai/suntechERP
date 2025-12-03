from django.urls import path
from . import views

app_name = 'po'

urlpatterns = [
    path('', views.po_list, name='po_list'),
    path('create/', views.po_create, name='po_create'),
    path('edit/<int:pk>/', views.po_edit, name='po_edit'),
    path('delete/<int:pk>/', views.po_delete, name='po_delete'),
    path('report/', views.po_report, name='po_report'),
]