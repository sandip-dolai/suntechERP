from django.contrib import admin
from .models import ItemMaster, CompanyMaster


@admin.register(ItemMaster)
class ItemMasterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'uom')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(CompanyMaster)
class CompanyMasterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'contact_person', 'phone')
    search_fields = ('code', 'name', 'contact_person')
    ordering = ('code',)