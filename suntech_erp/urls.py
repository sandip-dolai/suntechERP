from django.contrib import admin
from django.urls import path, include
from users.views import dashboard_view

admin.site.site_header = "SUNTECH ADMINISTRATOR"
admin.site.site_title = "Suntech ERP"
admin.site.index_title = "Admin Dashboard"

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Dashboard (single view → no namespace)
    path("", dashboard_view, name="dashboard"),
    # Users (auth & management)
    path("users/", include(("users.urls", "users"), namespace="users")),
    # ERP Core Modules (NAMESPACED)
    path("po/", include(("po.urls", "po"), namespace="po")),
    path("bom/", include(("bom.urls", "bom"), namespace="bom")),
    path("indent/", include(("indent.urls", "indent"), namespace="indent")),
    path("master/", include(("master.urls", "master"), namespace="master")),
    path(
        "notifications/",
        include(("notifications.urls", "notifications"), namespace="notifications"),
    ),
]

# Custom error pages
handler404 = "users.views.custom_404"
