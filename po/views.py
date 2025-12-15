from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from suntech_erp.permissions import login_required_view, admin_required
from django.db import transaction, IntegrityError
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat, Coalesce
from .models import PurchaseOrder, PurchaseOrderItem, POProcess, POProcessHistory
from .forms import PurchaseOrderForm, PurchaseOrderItemFormSet, POProcessUpdateForm
from master.models import CompanyMaster
from datetime import datetime
from django.http import HttpResponseForbidden


# ------------------------------
# PO CREATE (header + items)
# ------------------------------
@login_required_view
@admin_required
def po_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            # require at least one non-deleted item
            # note: formset.cleaned_data may contain deleted flags
            non_deleted_forms = [
                f for f in formset.cleaned_data if f and not f.get("DELETE", False)
            ]
            if not non_deleted_forms:
                formset.add_error(None, "At least one item is required.")
                return render(
                    request, "po/po_form.html", {"form": form, "formset": formset}
                )
            else:
                try:
                    with transaction.atomic():
                        po = form.save(commit=False)
                        po.created_by = request.user
                        po.save()
                        # save formset linked to po
                        formset.instance = po
                        formset.save()
                    messages.success(request, "Purchase Order created successfully.")
                    return redirect("po:po_list")
                except IntegrityError as e:
                    # likely unique constraint on po_number or oa_number
                    # parse and attach to form error (simple approach)
                    form.add_error(
                        None, "Database error: possible duplicate PO/OA number."
                    )
        else:
            # fall through to render with errors
            pass
    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet()

    context = {
        "form": form,
        "formset": formset,
        "title": "Create Purchase Order",
        "companies": CompanyMaster.objects.order_by("name"),
    }
    return render(request, "po/po_form.html", context)


# ------------------------------
# PO EDIT (header + items)
# ------------------------------
@login_required_view
def po_edit(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po)

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()  # <-- THIS PROCESSES DELETE CHECKBOXES
                messages.success(request, "Purchase Order updated successfully.")
                return redirect("po:po_list")
            except IntegrityError:
                form.add_error(None, "Database error: possible duplicate PO/OA number.")

        # If invalid, fall through to re-render with errors

    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po)

    context = {
        "form": form,
        "formset": formset,
        "title": f"Edit PO {po.po_number}",
        "po": po,
        "companies": CompanyMaster.objects.order_by("name"),
    }

    return render(request, "po/po_form.html", context)


# ------------------------------
# PO DELETE
# ------------------------------
@login_required_view
def po_delete(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == "POST":
        po.delete()
        messages.success(request, "Purchase Order deleted.")
        return redirect("po:po_list")
    return render(request, "po/po_delete.html", {"po": po})


# ------------------------------
# PO LIST (example with creator)
# ------------------------------
@login_required_view
def po_list(request):
    pos = (
        PurchaseOrder.objects.select_related("created_by", "company")
        .annotate(
            creator_name=Coalesce(
                Concat(
                    F("created_by__first_name"), Value(" "), F("created_by__last_name")
                ),
                F("created_by__username"),
                Value("—"),
                output_field=CharField(),
            )
        )
        .order_by("-id")
    )
    return render(request, "po/po_list.html", {"pos": pos})


@login_required_view
def po_report(request):
    view_mode = request.GET.get("view", "summary").lower()

    # required date defaults
    today = datetime.today().date()
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    # ✔ Auto-fill if missing
    if not date_from:
        date_from = today.strftime("%Y-%m-%d")
    if not date_to:
        date_to = today.strftime("%Y-%m-%d")

    # Detect if filters were applied
    filter_used = (
        "po_number" in request.GET
        or "company" in request.GET
        or "date_from" in request.GET
    )

    # Base queryset (empty initially)
    po_qs = PurchaseOrder.objects.none()

    if filter_used:
        po_qs = PurchaseOrder.objects.select_related("created_by", "company")

        # Apply filters only after button click
        if request.GET.get("po_number"):
            po_qs = po_qs.filter(po_number__icontains=request.GET["po_number"])

        if request.GET.get("company"):
            po_qs = po_qs.filter(company_id=request.GET["company"])

        # required date range
        po_qs = po_qs.filter(po_date__range=[date_from, date_to])

        # Creator name annotation
        po_qs = po_qs.annotate(
            creator_name=Coalesce(
                Concat(
                    F("created_by__first_name"), Value(" "), F("created_by__last_name")
                ),
                F("created_by__username"),
                Value("—"),
                output_field=CharField(),
            )
        )

    # ITEM VIEW (only if filter used)
    items = None
    if view_mode == "items" and filter_used:
        items = (
            PurchaseOrderItem.objects.select_related(
                "purchase_order", "purchase_order__company"
            )
            .filter(purchase_order__in=po_qs)
            .order_by("purchase_order__po_number", "id")
        )

    context = {
        "view": view_mode,
        "filters": {
            "po_number": request.GET.get("po_number", ""),
            "company": request.GET.get("company", ""),
            "date_from": date_from,
            "date_to": date_to,
        },
        "pos": po_qs.order_by("-po_date") if filter_used else [],
        "items": items,
        "filter_used": filter_used,
        "companies": CompanyMaster.objects.order_by("name"),
    }

    return render(request, "po/po_report.html", context)


# ------------------------------
# PO PROCESS LIST
# ------------------------------
@login_required_view
def po_process_list(request, po_id):
    po = get_object_or_404(PurchaseOrder, pk=po_id)

    processes = po.processes.select_related(
        "department_process",
        "current_status",
        "last_updated_by",
    ).order_by(
        "department_process__department",
        "department_process__name",
    )

    context = {
        "po": po,
        "processes": processes,
    }

    return render(request, "po/po_process_list.html", context)


# ------------------------------
# PO PROCESS UPDATE
# ------------------------------
def can_edit_po_process(user, po_process):
    """
    Admin can edit all.
    Department users can edit only their department processes.
    """
    if user.is_superuser or user.is_staff:
        return True

    return getattr(user, "department", None) == po_process.department_process.department


@login_required_view
def po_process_update(request, process_id):
    po_process = get_object_or_404(POProcess, pk=process_id)
    po = po_process.purchase_order

    # 🔐 Permission check
    if not can_edit_po_process(request.user, po_process):
        return HttpResponseForbidden(
            "You do not have permission to update this process."
        )

    if request.method == "POST":
        form = POProcessUpdateForm(
            request.POST,
            instance=po_process,
            user=request.user,
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Process status updated successfully.")
            return redirect(
                "po:po_process_list",
                po_id=po.id,
            )
    else:
        form = POProcessUpdateForm(
            instance=po_process,
            user=request.user,
        )

    context = {
        "form": form,
        "po": po,
        "po_process": po_process,
    }

    return render(
        request,
        "po/po_process_update.html",
        context,
    )


# ------------------------------
# PO PROCESS HISTORY VIEW
# ------------------------------
@login_required_view
def po_process_history(request, process_id):
    po_process = get_object_or_404(POProcess, pk=process_id)
    po = po_process.purchase_order

    history = po_process.history.select_related("status", "changed_by").order_by(
        "-changed_at"
    )

    context = {
        "po": po,
        "po_process": po_process,
        "history": history,
    }

    return render(
        request,
        "po/po_process_history.html",
        context,
    )
