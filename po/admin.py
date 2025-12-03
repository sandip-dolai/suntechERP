# po/admin.py
from django.contrib import admin
from .models import PurchaseOrder


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'po_number',
        'get_company',      # Displays company name/code
        'status',
        'created_by',
    ]
    list_filter = [
        'status',
        'company',          # Filters by CompanyMaster (shows name)
        'po_date',
    ]
    search_fields = [
        'po_number',
        'material_description',
        'company__name',    # Search by company name
        'company__code',    # Also search by company code
    ]
    autocomplete_fields = ['company']  # Modern Django admin lookup
    date_hierarchy = 'po_date'
    ordering = ['-po_date']

    # Custom method to display company in list
    def get_company(self, obj):
        return obj.company  # Uses CompanyMaster.__str__() → "SUP-001 - Acme Corp"
    get_company.short_description = 'Company'
    get_company.admin_order_field = 'company__name'  # Enables sorting by name