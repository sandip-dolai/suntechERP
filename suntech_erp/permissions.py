from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

def is_admin(user):
    if user.is_superuser:
        return True
    if user.is_staff:
        return True
    if user.department == "Admin":
        return True
    return False

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)

        if not is_admin(request.user):
            return render(request, "403.html", status=403)

        return view_func(request, *args, **kwargs)
    return wrapper

def login_required_view(view_func):
    return login_required(view_func)
