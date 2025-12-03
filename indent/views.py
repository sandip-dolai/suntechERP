# indent/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat, Coalesce
from django.utils.dateparse import parse_date
from .models import Indent
from .forms import IndentForm
from bom.models import BillOfMaterials
from po.models import PurchaseOrder
from master.models import CompanyMaster


# === ENHANCED LIST ===
@permission_required('indent.view_indent', raise_exception=True)
def indent_list(request):
    queryset = Indent.objects.select_related(
        'bom__po__company', 'bom__item', 'created_by'
    ).annotate(
        po_number=F('bom__po__po_number'),
        company_name=F('bom__po__company__name'),
        item_code=F('bom__item__code'),
        item_name=F('bom__item__name'),
        creator_name=Coalesce(
            Concat('created_by__first_name', Value(' '), 'created_by__last_name'),
            'created_by__username',
            Value('—'),
            output_field=CharField()
        )
    ).order_by('-indent_date', '-id')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(indent_number__icontains=q) |
            Q(po_number__icontains=q) |
            Q(item_code__icontains=q)
        )

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'indent/indent_list.html', {
        'page_obj': page_obj,
        'search_query': q,
    })


# === CREATE / EDIT (unchanged, but form now works) ===
@permission_required('indent.add_indent', raise_exception=True)
def indent_create(request):
    if request.method == 'POST':
        form = IndentForm(request.POST)
        if form.is_valid():
            indent = form.save(commit=False)
            indent.created_by = request.user
            indent.save()
            return redirect('indent:indent_list')
    else:
        form = IndentForm()
    return render(request, 'indent/indent_form.html', {'form': form})


@permission_required('indent.change_indent', raise_exception=True)
def indent_edit(request, pk):
    indent = get_object_or_404(Indent, pk=pk)
    if request.method == 'POST':
        form = IndentForm(request.POST, instance=indent)
        if form.is_valid():
            form.save()
            return redirect('indent:indent_list')
    else:
        form = IndentForm(instance=indent)
    return render(request, 'indent/indent_form.html', {'form': form})


@permission_required('indent.delete_indent', raise_exception=True)
def indent_delete(request, pk):
    indent = get_object_or_404(Indent, pk=pk)
    if request.method == 'POST':
        indent.delete()
        return redirect('indent:indent_list')
    return render(request, 'indent/indent_delete.html', {'indent': indent})


# === INDENT REPORT ===
@permission_required('indent.view_indent', raise_exception=True)
def indent_report(request):
    queryset = Indent.objects.select_related(
        'bom__po__company', 'bom__item', 'created_by'
    ).annotate(
        po_number=F('bom__po__po_number'),
        company_name=F('bom__po__company__name'),
        item_code=F('bom__item__code'),
        item_name=F('bom__item__name'),
        creator_name=Coalesce(
            Concat('created_by__first_name', Value(' '), 'created_by__last_name'),
            'created_by__username',
            Value('—'),
            output_field=CharField()
        )
    )

    # Filters
    indent_number = request.GET.get('indent_number', '').strip()
    po_number = request.GET.get('po_number', '').strip()
    company_id = request.GET.get('company', '')
    item_code = request.GET.get('item_code', '').strip()
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if indent_number:
        queryset = queryset.filter(indent_number__icontains=indent_number)
    if po_number:
        queryset = queryset.filter(po_number__icontains=po_number)
    if company_id and company_id.isdigit():
        queryset = queryset.filter(bom__po__company_id=int(company_id))
    if item_code:
        queryset = queryset.filter(item_code__icontains=item_code)
    if status:
        queryset = queryset.filter(status=status)
    if date_from:
        d = parse_date(date_from)
        if d:
            queryset = queryset.filter(indent_date__gte=d)
    if date_to:
        d = parse_date(date_to)
        if d:
            queryset = queryset.filter(indent_date__lte=d)

    queryset = queryset.order_by('-indent_date', '-id')

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'companies': CompanyMaster.objects.order_by('code'),
        'statuses': Indent.STATUS_CHOICES,
        'filters': {
            'indent_number': indent_number,
            'po_number': po_number,
            'company': company_id,
            'item_code': item_code,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        },
    }
    return render(request, 'indent/indent_report.html', context)