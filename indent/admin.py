from django.contrib import admin

from .models import Indent, IndentItem, IndentSubItem


# ======================================================
# INLINES
# ======================================================
class IndentSubItemInline(admin.TabularInline):
    model = IndentSubItem
    extra = 0
    fields = ["item", "size", "quantity", "material", "remarks", "bom_item"]
    readonly_fields = ["bom_item"]
    show_change_link = False


class IndentItemInline(admin.TabularInline):
    model = IndentItem
    extra = 0
    fields = ["purchase_order_item", "required_quantity", "uom", "remarks"]
    show_change_link = True  # open IndentItem to see its sub-items


# ======================================================
# INDENT ADMIN
# ======================================================
@admin.register(Indent)
class IndentAdmin(admin.ModelAdmin):
    list_display = (
        "indent_number",
        "indent_date",
        "purchase_order",
        "po_process",
        "created_by",
        "created_at",
    )

    list_filter = (
        "indent_date",
        "po_process__department_process",
    )

    search_fields = (
        "indent_number",
        "purchase_order__po_number",
        "purchase_order__oa_number",
    )

    readonly_fields = ("indent_number", "created_at", "created_by")

    inlines = [IndentItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ======================================================
# INDENT ITEM ADMIN (standalone — shows sub-items inline)
# ======================================================
@admin.register(IndentItem)
class IndentItemAdmin(admin.ModelAdmin):
    list_display = (
        "indent",
        "purchase_order_item",
        "required_quantity",
        "uom",
    )

    search_fields = (
        "indent__indent_number",
        "purchase_order_item__material_description",
    )

    list_select_related = ("indent", "purchase_order_item")

    inlines = [IndentSubItemInline]


# ======================================================
# INDENT SUB-ITEM ADMIN (standalone — for direct lookup)
# ======================================================
@admin.register(IndentSubItem)
class IndentSubItemAdmin(admin.ModelAdmin):
    list_display = (
        "indent_item",
        "item",
        "size",
        "quantity",
        "material",
        "is_bom_linked",
    )

    list_filter = ("material",)

    search_fields = (
        "item",
        "material",
        "indent_item__indent__indent_number",
    )

    readonly_fields = ("bom_item",)

    list_select_related = ("indent_item__indent", "bom_item")

    @admin.display(boolean=True, description="BOM Linked")
    def is_bom_linked(self, obj):
        return obj.bom_item_id is not None
