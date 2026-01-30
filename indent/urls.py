from django.urls import path
from . import views

app_name = "indent"

urlpatterns = [
    path("", views.indent_list, name="indent_list"),
    path("create/", views.indent_create, name="indent_create"),
    path("<int:pk>/", views.indent_detail, name="indent_detail"),
    path("<int:pk>/edit/", views.indent_update, name="indent_update"),
    path("<int:pk>/close/", views.indent_close, name="indent_close"),
    path("<int:pk>/delete/", views.indent_delete, name="indent_delete"),
    
    path("ajax/load-po-processes/", views.ajax_load_po_processes, name="ajax_po_processes"),
    path("ajax/ajax_load_po_items/", views.ajax_load_po_items, name="ajax_po_items"),
]
