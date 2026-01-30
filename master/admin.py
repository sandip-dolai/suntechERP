from django.contrib import admin
from .models import CompanyMaster


@admin.register(CompanyMaster)
class CompanyMasterAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "contact_person", "phone")
    search_fields = ("code", "name", "contact_person")
    ordering = ("code",)
