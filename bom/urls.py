from django.urls import path
from . import views

app_name = "bom"

urlpatterns = [
    path("", views.bom_list, name="bom_list"),  # /bom/
    path("create/", views.bom_create, name="bom_create"),  # /bom/create/
    path("<int:pk>/edit/", views.bom_edit, name="bom_edit"),  # /bom/1/edit/
    path("<int:pk>/", views.bom_detail, name="bom_detail"),  # /bom/1/
    path("ajax/po-items/", views.ajax_load_po_items, name="ajax_load_po_items"),
    path("<int:pk>/delete/", views.bom_delete, name="bom_delete"),
    # BOM REPORT
    path("report/", views.bom_report, name="bom_report"),
    path("report/excel/", views.bom_report_excel, name="bom_report_excel"),
]
