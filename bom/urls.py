from django.urls import path
from . import views

app_name = "bom"

urlpatterns = [
    path("", views.bom_list, name="bom_list"),
    path("create/", views.bom_create, name="bom_create"),
    path("<int:pk>/edit/", views.bom_edit, name="bom_edit"),
    path("<int:pk>/", views.bom_detail, name="bom_detail"),
    path("<int:pk>/delete/", views.bom_delete, name="bom_delete"),
    # BOM REPORT
    path("report/", views.bom_report, name="bom_report"),
    path("report/excel/", views.bom_report_excel, name="bom_report_excel"),
    path("<int:pk>/print/", views.bom_print, name="bom_print"),
    # AJAX
    path("ajax-po-items/", views.bom_po_items, name="bom_po_items"),
]
