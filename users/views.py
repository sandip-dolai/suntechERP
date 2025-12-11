from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from .forms import LoginForm
from .models import CustomUser
from .forms import UserCreateForm, UserUpdateForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.hashers import make_password
# from django.core.mail import send_mail
# from django.conf import settings

def custom_404(request, exception):
    return render(request, "404.html", status=404)

def admin_only(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser or request.user.department != 'Admin':
            return render(request, "403.html", status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required(login_url='/users/login/')
def dashboard_view(request):
    return render(request, 'base/dashboard.html')

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = LoginForm
    
    

@login_required
@admin_only
def user_list(request):
    users = CustomUser.objects.all()
    return render(request, "users/user_list.html", {"users": users})


@login_required
@admin_only
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("users:user_list")
    else:
        form = UserCreateForm()

    return render(request, "users/user_create.html", {"form": form})


@login_required
@admin_only
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("users:user_list")
    else:
        form = UserUpdateForm(instance=user)

    return render(request, "users/user_edit.html", {"form": form, "selected_user": user})



@login_required
@admin_only
def user_reset_password(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        new_password = request.POST.get("password")
        user.password = make_password(new_password)
        user.save()
        messages.success(request, "Password reset successfully!")
        return redirect("users:user_edit", user_id=user.id)

    return render(request, "users/user_reset_password.html", {"user": user})



# def custom_page_not_found_view(request, exception):
#     return render(request, '404.html', status=404)
    
    
    
    


# def send_mail_page(request):
#     context = {}
#     address ='sd694722@gmail.com'
#     subject = 'Test Email from Suntech ERP'
#     message = 'This is a test email sent from the Suntech ERP Django application.'
    

#     if address and subject and message:
#         try:
#             send_mail(subject, message, settings.EMAIL_HOST_USER, [address])
#             context['result'] = 'Email sent successfully'
#         except Exception as e:
#             context['result'] = f'Error sending email: {e}'
#     else:
#         context['result'] = 'All fields are required'
    
#     return render(request, "users/index.html", context)