from django.contrib import admin
from .models import BOM, BOMItem


class BOMItemInline(admin.TabularInline):
    model = BOMItem
    extra = 0
    autocomplete_fields = ["po_item"]


@admin.register(BOM)
class BOMAdmin(admin.ModelAdmin):
    list_display = (
        "bom_no",
        "po",
        "bom_date",
        "created_by",
    )
    list_filter = ("bom_date", "po")
    search_fields = ("bom_no", "po__po_number")
    readonly_fields = ("bom_no",)

    inlines = [BOMItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.bom_no = BOM.generate_bom_no(obj.po)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
