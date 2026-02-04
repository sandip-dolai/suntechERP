from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def is_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    # department-based access
    if user.department and str(user.department).strip().lower() == "admin":
        return True

    return False


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            return render(request, "403.html", status=403)
        return view_func(request, *args, **kwargs)

    return wrapper

def can_view_value(user):
    return is_admin(user)