from django.core.paginator import Paginator
from django.db.models import Q


def apply_master_search_pagination(
    request,
    queryset,
    search_fields=None,
    page_size=20,
):
    """
    Common search + pagination utility for all master tables
    """
    q = request.GET.get("q", "").strip()
    page = request.GET.get("page")

    # Search
    if q and search_fields:
        search_q = Q()
        for field in search_fields:
            search_q |= Q(**{f"{field}__icontains": q})
        queryset = queryset.filter(search_q)

    # Pagination
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    return {
        "page_obj": page_obj,
        "q": q,
    }
