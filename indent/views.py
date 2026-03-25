from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Indent, IndentItem, IndentSubItem
from .forms import IndentForm, IndentItemFormSet
from po.models import PurchaseOrder, POProcess, PurchaseOrderItem
from bom.models import BOM, BOMItem

from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.template.loader import render_to_string
from datetime import datetime

INDENT_PROCESS_IDS = [13, 18, 23]


# ======================================================
# INDENT LIST
# ======================================================
@login_required
def indent_list(request):
    q = request.GET.get("q", "").strip()

    qs = Indent.objects.select_related(
        "purchase_order",
        "po_process",
        "po_process__department_process",
        "created_by",
    )

    if q:
        qs = qs.filter(
            Q(indent_number__icontains=q)
            | Q(purchase_order__po_number__icontains=q)
            | Q(purchase_order__oa_number__icontains=q)
            | Q(po_process__department_process__name__icontains=q)
            | Q(created_by__username__icontains=q)
        )

    qs = qs.order_by("-id")

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "indent/indent_list.html", {"page_obj": page_obj, "q": q})


# ======================================================
# INDENT DETAIL
# ======================================================
@login_required
def indent_detail(request, pk):
    indent = get_object_or_404(
        Indent.objects.select_related(
            "purchase_order",
            "po_process",
            "po_process__department_process",
            "created_by",
        ).prefetch_related(
            "items__purchase_order_item",
            "items__sub_items__bom_item",
        ),
        pk=pk,
    )

    return render(request, "indent/indent_detail.html", {"indent": indent})


# ======================================================
# INDENT CREATE
# ======================================================
@login_required
@transaction.atomic
def indent_create(request):
    if request.method == "POST":
        form = IndentForm(request.POST)

        purchase_order = None
        po_id = request.POST.get("purchase_order")
        if po_id:
            purchase_order = PurchaseOrder.objects.filter(id=po_id).first()

        formset = IndentItemFormSet(
            request.POST,
            form_kwargs={"purchase_order": purchase_order},
        )

        if form.is_valid() and formset.is_valid():
            try:
                indent = form.save(commit=False)
                indent.created_by = request.user
                indent.save()

                formset.instance = indent
                saved_items = formset.save()

                # Save sub-items for each saved indent item
                _save_sub_items(request.POST, indent, saved_items, is_create=True)

                messages.success(
                    request, f"Indent {indent.indent_number} created successfully."
                )
                return redirect("indent:indent_list")

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = IndentForm()
        formset = IndentItemFormSet()

    return render(
        request,
        "indent/indent_form.html",
        {
            "form": form,
            "formset": formset,
            "mode": "create",
        },
    )


# ======================================================
# INDENT UPDATE
# ======================================================
@login_required
@transaction.atomic
def indent_update(request, pk):
    indent = get_object_or_404(Indent, pk=pk)

    if request.method == "POST":
        form = IndentForm(request.POST, instance=indent)

        formset = IndentItemFormSet(
            request.POST,
            instance=indent,
            form_kwargs={"purchase_order": indent.purchase_order},
        )

        if form.is_valid() and formset.is_valid():
            try:
                form.save()
                saved_items = formset.save()

                # Delete sub-items for any indent items that were deleted
                deleted_item_ids = [
                    item.pk
                    for item in formset.deleted_objects
                    if hasattr(item, "pk") and item.pk
                ]
                if deleted_item_ids:
                    IndentSubItem.objects.filter(
                        indent_item_id__in=deleted_item_ids
                    ).delete()

                # Replace sub-items for all remaining/updated items
                _save_sub_items(request.POST, indent, saved_items, is_create=False)

                messages.success(request, "Indent updated successfully.")
                return redirect("indent:indent_detail", pk=indent.id)

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = IndentForm(instance=indent)
        formset = IndentItemFormSet(
            instance=indent,
            form_kwargs={"purchase_order": indent.purchase_order},
        )

    # Pass existing sub-items to template keyed by indent_item id
    existing_sub_items = {}
    for item in indent.items.prefetch_related("sub_items__bom_item").all():
        existing_sub_items[item.id] = list(item.sub_items.all())

    return render(
        request,
        "indent/indent_form.html",
        {
            "form": form,
            "formset": formset,
            "mode": "edit",
            "indent": indent,
            "existing_sub_items": existing_sub_items,
        },
    )


# ======================================================
# INDENT DELETE
# ======================================================
@login_required
def indent_delete(request, pk):
    indent = get_object_or_404(Indent, pk=pk)

    if request.method == "POST":
        indent.delete()
        messages.success(request, "Indent deleted successfully.")
        return redirect("indent:indent_list")

    return render(request, "indent/indent_confirm_delete.html", {"indent": indent})


# ======================================================
# AJAX — Load Production Processes for a PO
# ======================================================
@login_required
def ajax_load_po_processes(request):
    po_id = request.GET.get("po_id")

    processes = POProcess.objects.filter(
        purchase_order_id=po_id,
        department_process_id__in=INDENT_PROCESS_IDS,
        department_process__department="Production",
    ).select_related("department_process")

    data = [{"id": p.id, "name": p.department_process.name} for p in processes]

    return JsonResponse(data, safe=False)


# ======================================================
# AJAX — Load PO Items for a PO
# ======================================================
@login_required
def ajax_load_po_items(request):
    po_id = request.GET.get("po_id")

    items = PurchaseOrderItem.objects.filter(purchase_order_id=po_id)

    data = [
        {
            "id": item.id,
            "name": item.material_description,
            "uom": item.uom,
        }
        for item in items
    ]

    return JsonResponse(data, safe=False)


# ======================================================
# AJAX — Load BOMs for a PO
# ======================================================
@login_required
def ajax_load_boms_for_po(request):
    po_id = request.GET.get("po_id")

    boms = BOM.objects.filter(po_id=po_id).order_by("bom_no")

    data = [{"id": bom.id, "bom_no": bom.bom_no} for bom in boms]

    return JsonResponse(data, safe=False)


# ======================================================
# AJAX — Load BOM Items for a BOM
# ======================================================
@login_required
def ajax_load_bom_items(request):
    bom_id = request.GET.get("bom_id")

    items = BOMItem.objects.filter(bom_id=bom_id)

    data = [
        {
            "id": item.id,
            "item": item.item,
            "size": item.size,
            "quantity": str(item.quantity),
            "material": item.material,
            "remarks": item.remarks,
        }
        for item in items
    ]

    return JsonResponse(data, safe=False)


# ======================================================
# INDENT REPORT
# ======================================================
@login_required
def indent_report(request):
    today = datetime.today().date()

    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to = request.GET.get("date_to") or today.strftime("%Y-%m-%d")
    po_id = request.GET.get("purchase_order", "")
    indent_no = request.GET.get("indent_no", "").strip()

    filters = {"indent_date__range": [date_from, date_to]}

    if po_id:
        filters["purchase_order_id"] = po_id
    if indent_no:
        filters["indent_number__icontains"] = indent_no

    qs = (
        Indent.objects.select_related(
            "purchase_order",
            "po_process",
            "po_process__department_process",
            "created_by",
        )
        .filter(**filters)
        .order_by("-id")
    )

    summary = qs.aggregate(
        total=Count("id"),
        unique_pos=Count("purchase_order", distinct=True),
    )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "indent/indent_report.html",
        {
            "page_obj": page_obj,
            "summary": summary,
            "filters": {
                "date_from": date_from,
                "date_to": date_to,
                "purchase_order": po_id,
                "indent_no": indent_no,
            },
            "purchase_orders": PurchaseOrder.objects.order_by("-id"),
            "q": "",
        },
    )


# ======================================================
# INDENT REPORT EXCEL  — replace the existing view
# ======================================================
@login_required
def indent_report_excel(request):
    today = datetime.today().date()

    date_from = request.GET.get("date_from") or today.strftime("%Y-%m-%d")
    date_to   = request.GET.get("date_to")   or today.strftime("%Y-%m-%d")
    po_id     = request.GET.get("purchase_order", "")
    indent_no = request.GET.get("indent_no", "").strip()

    filters = {"indent_date__range": [date_from, date_to]}
    if po_id:
        filters["purchase_order_id"] = po_id
    if indent_no:
        filters["indent_number__icontains"] = indent_no

    indents = (
        Indent.objects.select_related(
            "purchase_order",
            "po_process",
            "po_process__department_process",
            "created_by",
        )
        .prefetch_related(
            "items__purchase_order_item",
            "items__sub_items",
        )
        .filter(**filters)
        .order_by("-id")
    )

    html = render_to_string(
        "indent/indent_report_excel.html",
        {"indents": indents},
    )

    response = HttpResponse(html)
    response["Content-Type"] = "application/vnd.ms-excel"
    response["Content-Disposition"] = (
        f'attachment; filename="Indent_Report_{date_from}_to_{date_to}.xls"'
    )
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ======================================================
# HELPER — Save sub-items from POST arrays
# ======================================================
def _save_sub_items(post_data, indent, saved_items, is_create):
    """
    Sub-items are submitted as indexed POST arrays per indent item:

      sub_item_count-{item_form_index}   → number of sub-rows for that item
      sub_bom_item_id-{idx}-{sub_idx}    → BOMItem pk or "" (manual)
      sub_item-{idx}-{sub_idx}           → item name
      sub_size-{idx}-{sub_idx}           → size
      sub_quantity-{idx}-{sub_idx}       → quantity
      sub_material-{idx}-{sub_idx}       → material
      sub_remarks-{idx}-{sub_idx}        → remarks

    `saved_items` is the list returned by formset.save() — these are the
    IndentItem instances that were created/updated in this submission.

    On edit, existing sub-items for each saved IndentItem are deleted
    first, then re-created fresh from POST (clean replace strategy).
    """
    for form_index, indent_item in enumerate(saved_items):
        # On edit, wipe existing sub-items for this item before re-saving
        if not is_create:
            indent_item.sub_items.all().delete()

        count_key = f"sub_item_count-{form_index}"
        try:
            count = int(post_data.get(count_key, 0))
        except (ValueError, TypeError):
            count = 0

        to_create = []
        for sub_idx in range(count):
            item_val = post_data.get(f"sub_item-{form_index}-{sub_idx}", "").strip()
            size_val = post_data.get(f"sub_size-{form_index}-{sub_idx}", "").strip()
            qty_val = post_data.get(f"sub_quantity-{form_index}-{sub_idx}", "").strip()
            material_val = post_data.get(
                f"sub_material-{form_index}-{sub_idx}", ""
            ).strip()
            remarks_val = post_data.get(
                f"sub_remarks-{form_index}-{sub_idx}", ""
            ).strip()
            bom_item_id = post_data.get(
                f"sub_bom_item_id-{form_index}-{sub_idx}", ""
            ).strip()

            # Skip entirely blank rows
            if not item_val and not material_val and not qty_val:
                continue

            bom_item_obj = None
            if bom_item_id:
                try:
                    bom_item_obj = BOMItem.objects.get(pk=int(bom_item_id))
                except (BOMItem.DoesNotExist, ValueError):
                    bom_item_obj = None

            try:
                quantity = float(qty_val) if qty_val else 0
            except ValueError:
                quantity = 0

            to_create.append(
                IndentSubItem(
                    indent_item=indent_item,
                    bom_item=bom_item_obj,
                    item=item_val,
                    size=size_val,
                    quantity=quantity,
                    material=material_val,
                    remarks=remarks_val,
                )
            )

        if to_create:
            IndentSubItem.objects.bulk_create(to_create)


@login_required
def indent_print(request, pk):
    indent = get_object_or_404(
        Indent.objects.select_related(
            "purchase_order",
            "purchase_order__company",
            "po_process",
            "po_process__department_process",
            "created_by",
        ).prefetch_related(
            "items__purchase_order_item",
            "items__sub_items__bom_item",
        ),
        pk=pk,
    )
    return render(request, "indent/indent_print.html", {"indent": indent})
