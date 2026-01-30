from django.shortcuts import render, redirect, get_object_or_404
from suntech_erp.permissions import admin_required
from django.core.paginator import Paginator
from .models import (
    # ItemMaster,
    CompanyMaster,
    ProcessStatusMaster,
    DepartmentProcessMaster,
)
from .forms import (
    # ItemMasterForm,
    CompanyMasterForm,
    ProcessStatusMasterForm,
    DepartmentProcessMasterForm,
)


# ======================  COMPANY MASTER  ======================
@admin_required
def company_list(request):
    queryset = CompanyMaster.objects.all()
    paginator = Paginator(queryset, 25)
    page = request.GET.get("page")
    companies = paginator.get_page(page)
    return render(
        request, "master/company_master/company_list.html", {"companies": companies}
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
    queryset = DepartmentProcessMaster.objects.all()
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
        {"form": form, "title": "Create Department Process"},
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
        {"form": form, "title": "Edit Department Process"},
    )
