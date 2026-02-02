from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from .models import Notification


# ======================================================
# EXISTING: Notification List Page (HTML)
# ======================================================
@login_required
def notification_list(request):
    # Latest 100 notifications only
    qs = (
        request.user.notifications
        .order_by("-created_at")[:100]
    )

    # Paginate: 20 per page
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": page_obj,
        },
    )


# ======================================================
# EXISTING: Mark Single Notification as Read (Redirect)
# ======================================================
@login_required
def mark_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect(notification.url or "notifications:notification_list")


# ======================================================
# EXISTING: Mark All Notifications as Read (Redirect)
# ======================================================
@login_required
def mark_all_as_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return redirect("notifications:notification_list")


# ======================================================
# EXISTING: Unread Notifications API (Header Polling)
# ======================================================
@login_required
def unread_notifications_api(request):
    qs = request.user.notifications.filter(is_read=False).order_by("-created_at")

    data = {
        "count": qs.count(),
        "notifications": [
            {
                "id": n.id,
                "message": n.message,
                "url": n.url,
                "created": n.created_at.strftime("%d %b %Y %H:%M"),
            }
            for n in qs[:5]
        ],
    }
    return JsonResponse(data)


# ======================================================
# AJAX Notifications List (For Notifications Page)
# ======================================================
@login_required
def notifications_list_api(request):
    qs = request.user.notifications.all().order_by("-created_at")

    return JsonResponse(
        {
            "notifications": [
                {
                    "id": n.id,
                    "message": n.message,
                    "is_read": n.is_read,
                    "url": n.url,
                    "created": n.created_at.strftime("%d %b %Y %H:%M"),
                }
                for n in qs
            ]
        }
    )


# ======================================================
# AJAX Mark Single Notification as Read
# ======================================================
@login_required
@require_POST
def notification_mark_read_api(request, pk):
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user,
    )
    notification.is_read = True
    notification.save(update_fields=["is_read"])

    return JsonResponse({"success": True})


# ======================================================
# AJAX Mark All Notifications as Read
# ======================================================
@login_required
@require_POST
def notification_mark_all_read_api(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({"success": True})
