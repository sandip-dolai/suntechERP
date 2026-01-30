from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

from .models import Indent, PurchaseOrder
from .forms import IndentForm, IndentItemFormSet
from django.http import JsonResponse
from po.models import POProcess, PurchaseOrderItem

INDENT_PROCESS_IDS = [13, 18, 23]


# INDENT LIST VIEW
@login_required
def indent_list(request):
    indents = Indent.objects.select_related(
        "purchase_order",
        "po_process",
        "created_by",
    ).order_by("-id")

    return render(
        request,
        "indent/indent_list.html",
        {"indents": indents},
    )


# INDENT DETAIL VIEW
@login_required
def indent_detail(request, pk):
    indent = get_object_or_404(
        Indent.objects.select_related(
            "purchase_order",
            "po_process",
            "created_by",
        ).prefetch_related("items"),
        pk=pk,
    )

    return render(
        request,
        "indent/indent_detail.html",
        {"indent": indent},
    )


# INDENT CREATE VIEW
@login_required
def indent_create(request):
    if request.method == "POST":
        form = IndentForm(request.POST)

        # 🔑 Extract PO safely from POST
        purchase_order = None
        po_id = request.POST.get("purchase_order")
        if po_id:
            purchase_order = PurchaseOrder.objects.filter(id=po_id).first()

        formset = IndentItemFormSet(
            request.POST,
            form_kwargs={"purchase_order": purchase_order},
        )
        print("FORM ERRORS:", form.errors)
        print("FORMSET ERRORS:", formset.errors)
        print("FORMSET NON FORM ERRORS:", formset.non_form_errors())

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    indent = form.save(commit=False)
                    indent.created_by = request.user
                    indent.save()

                    formset.instance = indent
                    formset.save()

                messages.success(request, "Indent created successfully.")
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


# INDENT UPDATE (OPEN ONLY) VIEW
@login_required
def indent_update(request, pk):
    indent = get_object_or_404(Indent, pk=pk)

    if indent.status != "OPEN":
        messages.error(request, "Closed indent cannot be edited.")
        return redirect("indent:detail", pk=pk)

    if request.method == "POST":
        form = IndentForm(request.POST, instance=indent)

        formset = IndentItemFormSet(
            request.POST,
            instance=indent,
            form_kwargs={"purchase_order": indent.purchase_order},
        )

        print(form.errors)
        print(formset.errors)
        print(formset.non_form_errors())

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()

                messages.success(request, "Indent updated successfully.")
                return redirect("indent:detail", pk=pk)

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = IndentForm(instance=indent)
        formset = IndentItemFormSet(
            instance=indent,
            form_kwargs={"purchase_order": indent.purchase_order},
        )

    return render(
        request,
        "indent/indent_form.html",
        {
            "form": form,
            "formset": formset,
            "mode": "edit",
            "indent": indent,
        },
    )


# INDENT CLOSE VIEW
@login_required
def indent_close(request, pk):
    indent = get_object_or_404(Indent, pk=pk)

    if indent.status != "OPEN":
        messages.warning(request, "Indent already closed.")
        return redirect("indent:detail", pk=pk)

    indent.status = "CLOSED"
    indent.save(update_fields=["status"])

    messages.success(request, "Indent closed successfully.")
    return redirect("indent:detail", pk=pk)


# INDENT DELETE (OPEN ONLY) VIEW
@login_required
def indent_delete(request, pk):
    indent = get_object_or_404(Indent, pk=pk)

    if indent.status != "OPEN":
        messages.error(
            request,
            "Closed indent cannot be deleted.",
        )
        return redirect("indent:detail", pk=pk)

    if request.method == "POST":
        indent.delete()
        messages.success(request, "Indent deleted successfully.")
        return redirect("indent:indent_list")

    return render(
        request,
        "indent/indent_confirm_delete.html",
        {"indent": indent},
    )


def ajax_load_po_processes(request):
    po_id = request.GET.get("po_id")

    processes = POProcess.objects.filter(
        purchase_order_id=po_id,
        department_process_id__in=INDENT_PROCESS_IDS,
        department_process__department="Production",
    ).select_related("department_process")

    data = [
        {
            "id": p.id,
            "name": p.department_process.name,
        }
        for p in processes
    ]

    return JsonResponse(data, safe=False)


def ajax_load_po_items(request):
    po_id = request.GET.get("po_id")

    items = PurchaseOrderItem.objects.filter(purchase_order_id=po_id)

    data = [
        {
            "id": item.id,
            "name": item.material_description,
        }
        for item in items
    ]

    return JsonResponse(data, safe=False)

