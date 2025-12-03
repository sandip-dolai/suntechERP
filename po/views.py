from operator import concat
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.db.models import F, Value, CharField
from datetime import datetime
from .models import PurchaseOrder
from .forms import PurchaseOrderForm
from master.models import CompanyMaster
from django.db.models import Q, Value, CharField
from django.db.models.functions import Concat, Coalesce

# -------------------------------------------------
# 1. PO LIST – with Creator Name
# -------------------------------------------------
@permission_required('po.view_purchaseorder', raise_exception=True)
def po_list(request):
    """
    List all POs, newest first, showing the creator’s full name.
    """
    pos = (
        PurchaseOrder.objects
        .select_related('created_by')
        .annotate(
            creator_name=Concat(
                F('created_by__first_name'), Value(' '), F('created_by__last_name'),
                output_field=CharField()
            )
        )
        .order_by('-id')
    )

    # Fallback: empty name → username (or “—”)
    for po in pos:
        if not po.creator_name or not po.creator_name.strip():
            po.creator_name = po.created_by.username if po.created_by else '—'

    return render(request, 'po/po_list.html', {'pos': pos})


# -------------------------------------------------
# 2. CREATE PO
# -------------------------------------------------
@permission_required('po.add_purchaseorder', raise_exception=True)
def po_create(request):
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST)
        if form.is_valid():
            po = form.save(commit=False)
            po.created_by = request.user
            po.save()
            return redirect('po:po_list')
    else:
        form = PurchaseOrderForm()
    return render(request, 'po/po_form.html', {'form': form})


# -------------------------------------------------
# 3. EDIT PO
# -------------------------------------------------
@permission_required('po.change_purchaseorder', raise_exception=True)
def po_edit(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=po)
        if form.is_valid():
            form.save()
            return redirect('po:po_list')
    else:
        form = PurchaseOrderForm(instance=po)
    return render(request, 'po/po_form.html', {'form': form})


# -------------------------------------------------
# 4. DELETE PO
# -------------------------------------------------
@permission_required('po.delete_purchaseorder', raise_exception=True)
def po_delete(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    if request.method == 'POST':
        po.delete()
        return redirect('po:po_list')
    return render(request, 'po/po_delete.html', {'po': po})


# -------------------------------------------------
# 5. PO REPORT – with Filters + Creator Name
# -------------------------------------------------
@permission_required('po.view_purchaseorder', raise_exception=True)
def po_report(request):
    # Base queryset with related data
    queryset = PurchaseOrder.objects.select_related('created_by', 'company')

    # GET parameters
    po_number = request.GET.get('po_number', '').strip()
    company_id = request.GET.get('company', '')
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    # Filters
    if po_number:
        queryset = queryset.filter(po_number__icontains=po_number)
    if company_id:
        queryset = queryset.filter(company_id=company_id)
    if date_from:
        try:
            queryset = queryset.filter(po_date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            queryset = queryset.filter(po_date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    # Annotate creator name + fallback in ONE DB call
    queryset = queryset.annotate(
        creator_name=Coalesce(
            Concat(F('created_by__first_name'), Value(' '), F('created_by__last_name')),
            F('created_by__username'),
            Value('—'),
            output_field=CharField()
        )
    ).order_by('-po_date')

    # No Python loop needed anymore!

    context = {
        'pos': queryset,
        'companies': CompanyMaster.objects.order_by('code'),
        'filters': {
            'po_number': po_number,
            'company': company_id,
            'date_from': date_from,
            'date_to': date_to,
        },
    }
    return render(request, 'po/po_report.html', context)