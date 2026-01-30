from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages

from .models import BOM, BOMItem
from po.models import PurchaseOrder, PurchaseOrderItem


# BOM LIST VIEW
@login_required
def bom_list(request):
    boms = BOM.objects.select_related("po", "created_by").all()

    return render(
        request,
        "bom/bom_list.html",
        {
            "boms": boms,
        },
    )


# BOM CREATE VIEW
@login_required
@transaction.atomic
def bom_create(request):
    pos = PurchaseOrder.objects.all()

    if request.method == "POST":
        po_id = request.POST.get("purchase_order")
        bom_date = request.POST.get("bom_date")

        if not po_id:
            messages.error(request, "Purchase Order is required.")
            return redirect("bom:bom_create")

        po = get_object_or_404(PurchaseOrder, id=po_id)

        # ❌ Prevent duplicate BOM for same PO
        if BOM.objects.filter(po=po).exists():
            messages.error(request, "BOM already exists for this PO.")
            return redirect("bom:bom_create")

        # ✅ Create BOM
        bom = BOM.objects.create(
            po=po,
            bom_no=BOM.generate_bom_no(po),
            bom_date=bom_date,
            created_by=request.user,
        )

        # ✅ Create BOM items from PO items
        po_items = PurchaseOrderItem.objects.filter(purchase_order=po)

        for item in po_items:
            qty = request.POST.get(f"quantity_{item.id}")
            if qty:
                BOMItem.objects.create(
                    bom=bom,
                    po_item=item,
                    quantity=qty,
                )

        messages.success(request, "BOM created successfully.")
        return redirect("bom:bom_list")

    return render(
        request,
        "bom/bom_create.html",
        {
            "purchase_orders": pos,
        },
    )


# BOM DETAIL VIEW
@login_required
def bom_detail(request, pk):
    bom = get_object_or_404(BOM.objects.select_related("po", "created_by"), pk=pk)

    items = BOMItem.objects.select_related("po_item").filter(bom=bom)

    return render(
        request,
        "bom/bom_detail.html",
        {
            "bom": bom,
            "items": items,
        },
    )


# AJAX: LOAD PO ITEMS
@login_required
def ajax_load_po_items(request):
    po_id = request.GET.get("po_id")

    items = PurchaseOrderItem.objects.filter(purchase_order_id=po_id)

    data = [
        {
            "id": item.id,
            "name": item.material_description,
            "quantity": item.quantity_value,
            "uom": item.uom,
        }
        for item in items
    ]

    return JsonResponse(data, safe=False)
