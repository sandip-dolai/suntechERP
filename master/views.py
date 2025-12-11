from django.shortcuts import render, redirect, get_object_or_404
from suntech_erp.permissions import admin_required
from django.core.paginator import Paginator
from .models import ItemMaster, CompanyMaster
from .forms import ItemMasterForm, CompanyMasterForm


# ======================  ITEM MASTER  ======================
@admin_required
def item_list(request):
    queryset = ItemMaster.objects.all()
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    return render(request, 'master/item_master/item_list.html', {'items': items})


@admin_required
def item_create(request):
    if request.method == 'POST':
        form = ItemMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('master:item_list')
    else:
        form = ItemMasterForm()
    return render(request, 'master/item_master/item_form.html', {'form': form, 'title': 'Create Item'})


@admin_required
def item_edit(request, pk):
    obj = get_object_or_404(ItemMaster, pk=pk)
    if request.method == 'POST':
        form = ItemMasterForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('master:item_list')
    else:
        form = ItemMasterForm(instance=obj)
    return render(request, 'master/item_master/item_form.html', {'form': form, 'title': 'Edit Item'})


@admin_required
def item_delete(request, pk):
    obj = get_object_or_404(ItemMaster, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('master:item_list')
    return render(request, 'master/item_master/item_delete.html', {'obj': obj, 'type': 'Item'})


# ======================  COMPANY MASTER  ======================
@admin_required
def company_list(request):
    queryset = CompanyMaster.objects.all()
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page')
    companies = paginator.get_page(page)
    return render(request, 'master/company_master/company_list.html', {'companies': companies})


@admin_required
def company_create(request):
    if request.method == 'POST':
        form = CompanyMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('master:company_list')
    else:
        form = CompanyMasterForm()
    return render(request, 'master/company_master/company_form.html', {'form': form, 'title': 'Create Company'})


@admin_required
def company_edit(request, pk):
    obj = get_object_or_404(CompanyMaster, pk=pk)
    if request.method == 'POST':
        form = CompanyMasterForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            return redirect('master:company_list')
    else:
        form = CompanyMasterForm(instance=obj)
    return render(request, 'master/company_master/company_form.html', {'form': form, 'title': 'Edit Company'})


@admin_required
def company_delete(request, pk):
    obj = get_object_or_404(CompanyMaster, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('master:company_list')
    return render(request, 'master/company_master/company_delete.html', {'obj': obj, 'type': 'Company'})