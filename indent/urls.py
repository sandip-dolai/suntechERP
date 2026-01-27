from django.urls import path
from . import views

app_name = "indent"

urlpatterns = [
    path("", views.indent_list, name="list"),
    path("create/", views.indent_create, name="create"),
    path("<int:pk>/", views.indent_detail, name="detail"),
    path("<int:pk>/edit/", views.indent_update, name="update"),
    path("<int:pk>/close/", views.indent_close, name="close"),
    path("<int:pk>/delete/", views.indent_delete, name="delete"),
    
    path("ajax/load-po-processes/", views.ajax_load_po_processes, name="ajax_po_processes"),
    path("ajax/load-po-items/", views.ajax_load_po_items, name="ajax_po_items"),
]
