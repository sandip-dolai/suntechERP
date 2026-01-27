from django.contrib import admin
from .models import (
    PurchaseOrder,
    PurchaseOrderItem,
    POProcess,
    POProcessHistory,
)

# ======================================================
# PURCHASE ORDER ITEM INLINE
# ======================================================
class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    fields = [
        "material_code",
        "material_description",
        "quantity_value",
        "uom",
        "material_value",
        "status",
    ]
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return request.user.has_perm("po.add_purchaseorderitem")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("po.change_purchaseorderitem")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("po.delete_purchaseorderitem")


# ======================================================
# PO PROCESS INLINE (READ ONLY, UNDER PO)
# ======================================================
class POProcessInline(admin.TabularInline):
    model = POProcess
    extra = 0
    fields = [
        "department_process",
        "current_status",
        "last_updated_by",
        "last_updated_at",
    ]
    readonly_fields = fields
    can_delete = False
    show_change_link = True  # Opens POProcess admin


# ======================================================
# PURCHASE ORDER ADMIN
# ======================================================
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        "po_number",
        "oa_number",
        "company",
        "item_count",
        "po_status",
        "po_date",
        "created_by",
        "created_at",
    ]

    list_filter = [
        "po_status",
        "company",
        "po_date",
    ]

    search_fields = [
        "po_number",
        "oa_number",
        "company__name",
        "items__material_description",
    ]

    autocomplete_fields = ["company"]
    date_hierarchy = "po_date"
    ordering = ["-created_at"]

    readonly_fields = [
        "created_by",
        "created_at",
        "updated_at",
        "item_count",
    ]

    fieldsets = (
        ("PO Details", {
            "fields": (
                "po_number",
                "oa_number",
                "company",
                "po_date",
                "delivery_date",
            )
        }),
        ("Status", {
            "fields": ("po_status",)
        }),
        ("Audit Info", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )

    inlines = [
        PurchaseOrderItemInline,
        POProcessInline,
    ]

    # -----------------------------
    # AUTO SET CREATED BY
    # -----------------------------
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # -----------------------------
    # PERMISSION CONTROL
    # -----------------------------
    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("po.view_purchaseorder")

    def has_add_permission(self, request):
        return request.user.has_perm("po.add_purchaseorder")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("po.change_purchaseorder")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("po.delete_purchaseorder")


# ======================================================
# PO PROCESS HISTORY INLINE (UNDER PO PROCESS)
# ======================================================
class POProcessHistoryInline(admin.TabularInline):
    model = POProcessHistory
    extra = 0
    readonly_fields = [
        "status",
        "remark",
        "changed_by",
        "changed_at",
    ]
    can_delete = False


# ======================================================
# PO PROCESS ADMIN
# ======================================================
@admin.register(POProcess)
class POProcessAdmin(admin.ModelAdmin):
    list_display = [
        "purchase_order",
        "department_process",
        "current_status",
        "last_updated_by",
        "last_updated_at",
    ]

    list_filter = [
        "department_process",
        "current_status",
    ]

    search_fields = [
        "purchase_order__po_number",
    ]

    readonly_fields = [
        "purchase_order",
        "department_process",
        "last_updated_by",
        "last_updated_at",
    ]

    inlines = [POProcessHistoryInline]

    def has_add_permission(self, request):
        return False  # created automatically

    def has_delete_permission(self, request, obj=None):
        return False


# ======================================================
# PO PROCESS HISTORY ADMIN (OPTIONAL VIEW)
# ======================================================
@admin.register(POProcessHistory)
class POProcessHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "po_process",
        "status",
        "changed_by",
        "changed_at",
    ]

    list_filter = [
        "status",
        "changed_at",
    ]

    search_fields = [
        "po_process__purchase_order__po_number",
    ]

    readonly_fields = [
        "po_process",
        "status",
        "remark",
        "changed_by",
        "changed_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
