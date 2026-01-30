from django.urls import path
from . import views

app_name = "master"

urlpatterns = [
    # ----- Company Master -----
    path("companies/", views.company_list, name="company_list"),
    path("companies/create/", views.company_create, name="company_create"),
    path("companies/<int:pk>/edit/", views.company_edit, name="company_edit"),
    path("companies/<int:pk>/delete/", views.company_delete, name="company_delete"),
    # ----- Process Status Master -----
    path("process-statuses/", views.process_status_list, name="process_status_list"),
    path(
        "process-statuses/create/",
        views.process_status_create,
        name="process_status_create",
    ),
    path(
        "process-statuses/<int:pk>/edit/",
        views.process_status_edit,
        name="process_status_edit",
    ),
    path(
        "department-processes/",
        views.department_process_list,
        name="department_process_list",
    ),
    path(
        "department-processes/create/",
        views.department_process_create,
        name="department_process_create",
    ),
    path(
        "department-processes/<int:pk>/edit/",
        views.department_process_edit,
        name="department_process_edit",
    ),
]
