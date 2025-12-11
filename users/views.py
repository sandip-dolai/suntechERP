from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from .forms import LoginForm
from .models import CustomUser
from .forms import UserCreateForm, UserUpdateForm
from django.shortcuts import render, redirect, get_object_or_404
# from django.core.mail import send_mail
# from django.conf import settings



@login_required(login_url='/users/login/')
def dashboard_view(request):
    return render(request, 'base/dashboard.html')

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = LoginForm
    
    

@login_required
def user_list(request):
    users = CustomUser.objects.all()
    return render(request, "users/user_list.html", {"users": users})


@login_required
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
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("users:user_list")
    else:
        form = UserUpdateForm(instance=user)

    return render(request, "users/user_edit.html", {"form": form, "user": user})




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