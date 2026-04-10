from django.urls import path
from . import views

app_name = "po"

urlpatterns = [
    # ------------------------------
    # PO CRUD
    # ------------------------------
    path("", views.po_list, name="po_list"),
    path("create/", views.po_create, name="po_create"),
    path("edit/<int:pk>/", views.po_edit, name="po_edit"),
    path("delete/<int:pk>/", views.po_delete, name="po_delete"),
    path("report/", views.po_report, name="po_report"),
    path(
        "report/summary/excel/",
        views.po_report_summary_excel,
        name="po_report_summary_excel",
    ),
    path(
        "report/items/excel/",
        views.po_report_item_excel,
        name="po_report_item_excel",
    ),
    path("<int:pk>/print/", views.po_print, name="po_print"),
    path("<int:pk>/ajax-items/", views.ajax_po_items_list, name="ajax_po_items_list"),
    # ------------------------------
    # PO PROCESS ROUTES
    # ------------------------------
    path(
        "<int:po_id>/processes/",
        views.po_process_list,
        name="po_process_list",
    ),
    path(
        "process/<int:process_id>/update/",
        views.po_process_update,
        name="po_process_update",
    ),
    path(
        "process/<int:process_id>/history/",
        views.po_process_history,
        name="po_process_history",
    ),
    path(
        "<int:po_id>/processes/excel/",
        views.po_process_excel,
        name="po_process_excel",
    ),
    path("process-report/", views.po_process_report, name="po_process_report"),
    path(
        "process-report/excel/",
        views.po_process_report_excel,
        name="po_process_report_excel",
    ),
    # ------------------------------
    # target
    # ------------------------------
    path("target/", views.po_target_list, name="po_target_list"),
    path("target/create/", views.po_target_create, name="po_target_create"),
    path("target/<int:pk>/edit/", views.po_target_edit, name="po_target_edit"),
    path("target/<int:pk>/delete/", views.po_target_delete, name="po_target_delete"),
    path(
        "target/ajax-items/<int:po_id>/",
        views.ajax_po_items_for_target,
        name="ajax_po_items_for_target",
    ),
    path("target-report/", views.po_target_report, name="po_target_report"),
    path(
        "target-report/excel/",
        views.po_target_report_excel,
        name="po_target_report_excel",
    ),
]
