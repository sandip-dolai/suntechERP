from django.contrib import admin

from .models import Indent, IndentItem


class IndentItemInline(admin.TabularInline):
    model = IndentItem
    extra = 0


@admin.register(Indent)
class IndentAdmin(admin.ModelAdmin):
    list_display = (
        "indent_number",
        "indent_date",
        "purchase_order",
        "po_process",
        "status",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "indent_date",
        "po_process__department_process",
    )

    search_fields = (
        "indent_number",
        "purchase_order__po_number",
    )

    readonly_fields = ("created_at",)

    inlines = [IndentItemInline]


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
