# po/admin.py
from django.contrib import admin
from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    fields = ['material_description', 'quantity', 'status']
    readonly_fields = []
    show_change_link = True


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'po_number',
        'oa_number',
        'get_company',
        'item_count',
        'po_date',
        'created_by',
    ]

    list_filter = [
        'company',
        'po_date',
    ]

    search_fields = [
        'po_number',
        'oa_number',
        'company__name',
        'company__code',
        'items__material_description',
    ]

    autocomplete_fields = ['company']
    date_hierarchy = 'po_date'
    ordering = ['-po_date']

    inlines = [PurchaseOrderItemInline]

    # Custom column for company
    def get_company(self, obj):
        return obj.company
    get_company.short_description = 'Company'
    get_company.admin_order_field = 'company__name'
