from django.shortcuts import render, redirect, get_object_or_404
from suntech_erp.permissions import admin_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db import transaction
from .models import (
    CompanyMaster,
    ProcessStatusMaster,
    DepartmentProcessMaster,
)

from .forms import (
    CompanyMasterForm,
    ProcessStatusMasterForm,
    DepartmentProcessMasterForm,
)
from .utils import apply_master_search_pagination

# ======================  COMPANY MASTER  ======================
@admin_required
def company_list(request):
    queryset = CompanyMaster.objects.all().order_by("code")

    context = apply_master_search_pagination(
        request,
        queryset,
        search_fields=["code", "code2", "name"],
        page_size=20,
    )

    return render(
        request,
        "master/company_master/company_list.html",
        context,
    )

@admin_required
def company_create(request):
    if request.method == "POST":
        form = CompanyMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("master:company_list")
    else:
        form = CompanyMasterForm()
    return render(
        request,
        "master/company_master/company_form.html",
        {"form": form, "title": "Create Company"},
    )


@admin_required
def company_edit(request, pk):
    obj = get_object_or_404(CompanyMaster, pk=pk)
    if request.method == "POST":
        form = CompanyMasterForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("master:company_list")
    else:
        form = CompanyMasterForm(instance=obj)
    return render(
        request,
        "master/company_master/company_form.html",
        {"form": form, "title": "Edit Company"},
    )


@admin_required
def company_delete(request, pk):
    obj = get_object_or_404(CompanyMaster, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("master:company_list")
    return render(
        request,
        "master/company_master/company_delete.html",
        {"obj": obj, "type": "Company"},
    )


# ======================  PROCESS STATUS MASTER  ======================
@admin_required
def process_status_list(request):
    queryset = ProcessStatusMaster.objects.all()
    paginator = Paginator(queryset, 25)
    page = request.GET.get("page")
    statuses = paginator.get_page(page)
    return render(
        request, "master/process_status_master/status_list.html", {"statuses": statuses}
    )


@admin_required
def process_status_create(request):
    if request.method == "POST":
        form = ProcessStatusMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("master:process_status_list")
    else:
        form = ProcessStatusMasterForm()
    return render(
        request,
        "master/process_status_master/status_form.html",
        {"form": form, "title": "Create Process Status"},
    )


@admin_required
def process_status_edit(request, pk):
    obj = get_object_or_404(ProcessStatusMaster, pk=pk)
    if request.method == "POST":
        form = ProcessStatusMasterForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("master:process_status_list")
    else:
        form = ProcessStatusMasterForm(instance=obj)
    return render(
        request,
        "master/process_status_master/status_form.html",
        {"form": form, "title": "Edit Process Status"},
    )


# ======================  DEPARTMENT PROCESS MASTER  ======================


@admin_required
def department_process_list(request):
    queryset = DepartmentProcessMaster.objects.all().order_by("sequence")
    paginator = Paginator(queryset, 50)
    page = request.GET.get("page")
    processes = paginator.get_page(page)

    return render(
        request,
        "master/department_process_master/process_list.html",
        {"processes": processes},
    )


@admin_required
def department_process_create(request):
    if request.method == "POST":
        form = DepartmentProcessMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("master:department_process_list")
    else:
        form = DepartmentProcessMasterForm()

    return render(
        request,
        "master/department_process_master/process_form.html",
        {
            "form": form,
            "title": "Create Department Process",
        },
    )


@admin_required
def department_process_edit(request, pk):
    obj = get_object_or_404(DepartmentProcessMaster, pk=pk)

    if request.method == "POST":
        form = DepartmentProcessMasterForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect("master:department_process_list")
    else:
        form = DepartmentProcessMasterForm(instance=obj)

    return render(
        request,
        "master/department_process_master/process_form.html",
        {
            "form": form,
            "title": "Edit Department Process",
        },
    )


@admin_required
def department_process_reorder(request):
    """
    Show all active department processes in execution order
    for drag & drop reordering.
    """
    processes = DepartmentProcessMaster.objects.filter(is_active=True).order_by(
        "sequence"
    )

    return render(
        request,
        "master/department_process_master/process_reorder.html",
        {"processes": processes},
    )


@admin_required
@require_POST
@transaction.atomic
def department_process_reorder_save(request):
    """
    Save reordered process sequence.
    Expects POST data: order[] = [id1, id2, id3, ...]
    """
    order = request.POST.getlist("order[]")

    if not order:
        return HttpResponseBadRequest("Invalid order data")

    processes = {
        str(p.id): p for p in DepartmentProcessMaster.objects.filter(id__in=order)
    }

    if len(processes) != len(order):
        return HttpResponseBadRequest("Process mismatch detected")

    # Reassign sequence starting from 1
    for index, process_id in enumerate(order, start=1):
        process = processes[process_id]
        process.sequence = index
        process.save(update_fields=["sequence"])

    return JsonResponse({"status": "success"})
