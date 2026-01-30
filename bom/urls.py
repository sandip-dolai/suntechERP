from django.urls import path
from . import views

app_name = "bom"

urlpatterns = [
    # -----------------------------
    # BOM LIST
    # -----------------------------
    path("", views.bom_list, name="bom_list"),
    # -----------------------------
    # BOM CREATE
    # -----------------------------
    path("create/", views.bom_create, name="bom_create"),
    # -----------------------------
    # BOM DETAIL / VIEW
    # -----------------------------
    path("<int:pk>/", views.bom_detail, name="bom_detail"),
    # -----------------------------
    # AJAX: LOAD PO ITEMS
    # -----------------------------
    path("ajax/po-items/", views.ajax_load_po_items, name="ajax_load_po_items"),
]
