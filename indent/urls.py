from django.urls import path
from . import views

app_name = "indent"

urlpatterns = [
    # ── CRUD ──────────────────────────────────────────────────────────────
    path("", views.indent_list, name="indent_list"),
    path("create/", views.indent_create, name="indent_create"),
    path("<int:pk>/", views.indent_detail, name="indent_detail"),
    path("<int:pk>/edit/", views.indent_update, name="indent_update"),
    path("<int:pk>/delete/", views.indent_delete, name="indent_delete"),
    # ── REPORT ────────────────────────────────────────────────────────────
    path("report/", views.indent_report, name="indent_report"),
    path("<int:pk>/print/", views.indent_print, name="indent_print"),
    path("report/excel/", views.indent_report_excel, name="indent_report_excel"),
    # ── AJAX ──────────────────────────────────────────────────────────────
    path("ajax/po-processes/", views.ajax_load_po_processes, name="ajax_po_processes"),
    path("ajax/po-items/", views.ajax_load_po_items, name="ajax_po_items"),
    path("ajax/boms/", views.ajax_load_boms_for_po, name="ajax_boms_for_po"),
    path("ajax/bom-items/", views.ajax_load_bom_items, name="ajax_bom_items"),
]
