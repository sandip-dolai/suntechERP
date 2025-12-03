from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from .models import ItemMaster, CompanyMaster
from .forms import ItemMasterForm, CompanyMasterForm


# ======================  ITEM MASTER  ======================
@permission_required('master.view_itemmaster', raise_exception=True)
def item_list(request):
    queryset = ItemMaster.objects.all()
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    return render(request, 'master/item_master/item_list.html', {'items': items})


@permission_required('master.add_itemmaster', raise_exception=True)
def item_create(request):
    if request.method == 'POST':
        form = ItemMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('master:item_list')
    else:
        form = ItemMasterForm()
    return render(request, 'master/item_master/item_form.html', {'form': form, 'title': 'Create Item'})


@permission_required('master.change_itemmaster', raise_exception=True)
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


@permission_required('master.delete_itemmaster', raise_exception=True)
def item_delete(request, pk):
    obj = get_object_or_404(ItemMaster, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('master:item_list')
    return render(request, 'master/item_master/item_delete.html', {'obj': obj, 'type': 'Item'})


# ======================  COMPANY MASTER  ======================
@permission_required('master.view_companymaster', raise_exception=True)
def company_list(request):
    queryset = CompanyMaster.objects.all()
    paginator = Paginator(queryset, 25)
    page = request.GET.get('page')
    companies = paginator.get_page(page)
    return render(request, 'master/company_master/company_list.html', {'companies': companies})


@permission_required('master.add_companymaster', raise_exception=True)
def company_create(request):
    if request.method == 'POST':
        form = CompanyMasterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('master:company_list')
    else:
        form = CompanyMasterForm()
    return render(request, 'master/company_master/company_form.html', {'form': form, 'title': 'Create Company'})


@permission_required('master.change_companymaster', raise_exception=True)
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


@permission_required('master.delete_companymaster', raise_exception=True)
def company_delete(request, pk):
    obj = get_object_or_404(CompanyMaster, pk=pk)
    if request.method == 'POST':
        obj.delete()
        return redirect('master:company_list')
    return render(request, 'master/company_master/company_delete.html', {'obj': obj, 'type': 'Company'})