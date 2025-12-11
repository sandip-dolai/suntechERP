from django.shortcuts import render, redirect, get_object_or_404
from suntech_erp.permissions import login_required_view
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat, Coalesce
from django.utils.dateparse import parse_date

from .models import BillOfMaterials
from .forms import BillOfMaterialsForm
from po.models import PurchaseOrder
from master.models import CompanyMaster


@login_required_view
def bom_list(request):
    queryset = BillOfMaterials.objects.select_related(
        'po', 'po__company', 'item', 'created_by'
    ).annotate(
        creator_name=Coalesce(
            Concat('created_by__first_name', Value(' '), 'created_by__last_name'),
            'created_by__username',
            Value('—')
        )
    ).order_by('-po__po_date', '-id')

    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(po__po_number__icontains=q) |
            Q(item__code__icontains=q) |
            Q(item__name__icontains=q)
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'bom/bom_list.html', {
        'page_obj': page_obj,
        'search_query': q,
    })
# ----------------------------------------------------------------------
# 2. CREATE – standalone or from PO
# ----------------------------------------------------------------------
@login_required_view
def bom_create(request, po_id=None):
    po = None
    if po_id:
        po = get_object_or_404(PurchaseOrder, id=po_id)

    if request.method == 'POST':
        form = BillOfMaterialsForm(request.POST)
        if form.is_valid():
            bom = form.save(commit=False)
            if po:
                bom.po = po
            bom.created_by = request.user
            bom.save()
            messages.success(request, f'BOM line added for {bom.item}.')
            return redirect('bom:bom_list')
    else:
        initial = {'po': po} if po else {}
        form = BillOfMaterialsForm(initial=initial)

    title = f"Add BOM Line to PO {po.po_number}" if po else "Create BOM Line"
    return render(request, 'bom/bom_form.html', {
        'form': form,
        'title': title,
        'po': po,
    })


# ----------------------------------------------------------------------
# 3. EDIT
# ----------------------------------------------------------------------
@login_required_view
def bom_edit(request, pk):
    bom = get_object_or_404(BillOfMaterials, pk=pk)

    if request.method == 'POST':
        form = BillOfMaterialsForm(request.POST, instance=bom)
        if form.is_valid():
            form.save()
            messages.success(request, 'BOM line updated.')
            return redirect('bom:bom_list')
    else:
        form = BillOfMaterialsForm(instance=bom)

    return render(request, 'bom/bom_form.html', {
        'form': form,
        'title': 'Edit BOM Line',
        'bom': bom,
    })


# ----------------------------------------------------------------------
# 4. DELETE
# ----------------------------------------------------------------------
@login_required_view
def bom_delete(request, pk):
    bom = get_object_or_404(BillOfMaterials, pk=pk)

    if request.method == 'POST':
        po = bom.po
        bom.delete()
        messages.success(request, 'BOM line removed.')
        return redirect('po:po_detail', pk=po.id) if 'po:po_detail' in request.META.get('HTTP_REFERER', '') else redirect('bom:bom_list')

    return render(request, 'bom/bom_delete.html', {'bom': bom})


# ----------------------------------------------------------------------
# 5. REPORT – advanced filtering + creator name
# ----------------------------------------------------------------------
@login_required_view
def bom_report(request):
    queryset = BillOfMaterials.objects.select_related(
        'po', 'po__company', 'item', 'created_by'
    )

    # === FILTERS ===
    po_number  = request.GET.get('po_number', '').strip()
    company_id = request.GET.get('company', '')
    item_code  = request.GET.get('item_code', '').strip()
    date_from  = request.GET.get('date_from', '').strip()
    date_to    = request.GET.get('date_to', '').strip()

    if po_number:
        queryset = queryset.filter(po__po_number__icontains=po_number)
    if company_id and company_id.isdigit():
        queryset = queryset.filter(po__company_id=int(company_id))
    if item_code:
        queryset = queryset.filter(item__code__icontains=item_code)
    if date_from:
        d = parse_date(date_from)
        if d:
            queryset = queryset.filter(po__po_date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            queryset = queryset.filter(po__po_date__lte=d)

    # === ANNOTATE CREATOR NAME ===
    queryset = queryset.annotate(
        creator_name=Coalesce(
            Concat(F('created_by__first_name'), Value(' '), F('created_by__last_name')),
            F('created_by__username'),
            Value('—'),
            output_field=CharField()
        )
    ).order_by('-po__po_date', '-id')

    # === PAGINATION ===
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    # === CONTEXT ===
    context = {
        'page_obj': page_obj,
        'companies': CompanyMaster.objects.order_by('code'),
        'filters': {
            'po_number': po_number,
            'company': company_id,
            'item_code': item_code,
            'date_from': date_from,
            'date_to': date_to,
        },
    }
    return render(request, 'bom/bom_report.html', context)