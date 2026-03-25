from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.contrib import messages

from .models import BOM, BOMItem
from po.models import PurchaseOrder
from django.core.paginator import Paginator
from django.db.models import Q, Count
from datetime import datetime
from django.template.loader import render_to_string
from django.http import HttpResponse


# ======================================================
# BOM LIST
# ======================================================
@login_required
def bom_list(request):
    q = request.GET.get("q", "").strip()

    qs = BOM.objects.select_related("po", "created_by")

    if q:
        qs = qs.filter(
            Q(bom_no__icontains=q)
            | Q(po__po_number__icontains=q)
            | Q(po__oa_number__icontains=q)
            | Q(created_by__username__icontains=q)
        )

    qs = qs.order_by("-id")

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "bom/bom_list.html", {"page_obj": page_obj, "q": q})


# ======================================================
# BOM CREATE
# ======================================================
@login_required
@transaction.atomic
def bom_create(request):
    purchase_orders = PurchaseOrder.objects.order_by("-id")

    if request.method == "POST":
        po_id = request.POST.get("purchase_order")
        bom_date = request.POST.get("bom_date")

        if not po_id:
            messages.error(request, "Purchase Order is required.")
            return redirect("bom:bom_create")

        if not bom_date:
            messages.error(request, "BOM date is required.")
            return redirect("bom:bom_create")

        po = get_object_or_404(PurchaseOrder, id=po_id)

        # Create BOM header
        bom = BOM.objects.create(
            po=po,
            bom_no=BOM.generate_bom_no(po),
            bom_date=bom_date,
            created_by=request.user,
        )

        # Parse and save BOM items from POST
        _save_bom_items(request, bom)

        messages.success(request, f"BOM {bom.bom_no} created successfully.")
        return redirect("bom:bom_list")

    return render(
        request,
        "bom/bom_form.html",
        {
            "mode": "create",
            "bom": None,
            "items": [],
            "purchase_orders": purchase_orders,
        },
    )


# ======================================================
# BOM DETAIL
# ======================================================
@login_required
def bom_detail(request, pk):
    bom = get_object_or_404(
        BOM.objects.select_related("po", "created_by"), pk=pk
    )
    items = bom.items.all()

    return render(request, "bom/bom_detail.html", {"bom": bom, "items": items})


# ======================================================
# BOM EDIT
# ======================================================
@login_required
@transaction.atomic
def bom_edit(request, pk):
    bom = get_object_or_404(BOM, pk=pk)
    items = bom.items.all()

    if request.method == "POST":
        bom_date = request.POST.get("bom_date")
        if bom_date:
            bom.bom_date = bom_date
            bom.save()

        # Replace all items with freshly submitted ones
        bom.items.all().delete()
        _save_bom_items(request, bom)

        messages.success(request, "BOM updated successfully.")
        return redirect("bom:bom_detail", pk=bom.id)

    return render(
        request,
        "bom/bom_form.html",
        {
            "mode": "edit",
            "bom": bom,
            "items": items,
            "purchase_orders": PurchaseOrder.objects.filter(id=bom.po.id),
        },
    )


# ======================================================
# BOM DELETE
# ======================================================
@login_required
def bom_delete(request, pk):
    bom = get_object_or_404(BOM, pk=pk)

    if request.method == "POST":
        bom.delete()
        messages.success(request, "BOM deleted successfully.")
        return redirect("bom:bom_list")

    return render(request, "bom/bom_confirm_delete.html", {"bom": bom})


# ======================================================
# REPORT
# ======================================================
@login_required
def bom_report(request):
    today = datetime.today().date()

    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")
    po_id = request.GET.get("po", "")

    filters = {"bom_date__range": [date_from, date_to]}
    if po_id:
        filters["po_id"] = po_id

    qs = (
        BOM.objects.select_related("po", "created_by")
        .filter(**filters)
        .order_by("-id")
    )

    summary = qs.aggregate(total_boms=Count("id"))

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "bom/bom_report.html",
        {
            "page_obj": page_obj,
            "summary": summary,
            "filters": {"date_from": date_from, "date_to": date_to, "po": po_id},
            "purchase_orders": PurchaseOrder.objects.order_by("-id"),
            "q": "",
        },
    )


@login_required
def bom_report_excel(request):
    today = datetime.today().date()

    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")
    po_id = request.GET.get("po", "")

    filters = {"bom_date__range": [date_from, date_to]}
    if po_id:
        filters["po_id"] = po_id

    boms = (
        BOM.objects.select_related("po", "created_by")
        .filter(**filters)
        .order_by("-id")
    )

    html = render_to_string("bom/bom_report_excel.html", {"boms": boms})

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="BOM_Report_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ======================================================
# HELPER
# ======================================================
def _save_bom_items(request, bom):
    """
    Reads repeating POST arrays:
      item[], size[], quantity[], material[], remarks[]
    and bulk-creates BOMItem rows. Rows where item/quantity/material
    are all blank are silently skipped.
    """
    items_data = zip(
        request.POST.getlist("item[]"),
        request.POST.getlist("size[]"),
        request.POST.getlist("quantity[]"),
        request.POST.getlist("material[]"),
        request.POST.getlist("remarks[]"),
    )

    to_create = []
    for item, size, quantity, material, remarks in items_data:
        item = item.strip()
        quantity = quantity.strip()
        material = material.strip()

        # Skip entirely blank rows
        if not item and not quantity and not material:
            continue

        to_create.append(
            BOMItem(
                bom=bom,
                item=item,
                size=size.strip(),
                quantity=quantity or 0,
                material=material,
                remarks=remarks.strip(),
            )
        )

    if to_create:
        BOMItem.objects.bulk_create(to_create)