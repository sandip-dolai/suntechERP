from django.contrib import admin
from .models import Indent

@admin.register(Indent)
class IndentAdmin(admin.ModelAdmin):
    list_display = ['indent_number', 'bom', 'status', 'created_by']
    list_filter = ['status', 'bom__po__po_number']
    search_fields = ['indent_number', 'bom__item_name']