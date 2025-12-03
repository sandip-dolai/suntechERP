from django.contrib import admin
from django.urls import path, include
from users.views import dashboard_view  # Import the new view

admin.site.site_header = "SUNTECH ADMINISTRATOR"
admin.site.site_title="Suntech ERP"
admin.site.index_title="Admin Dashboard"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    path('users/', include('users.urls')),
    path('po/', include('po.urls')),
    path('bom/', include('bom.urls')),
    path('indent/', include('indent.urls')),
    path('', include('master.urls')),
]
