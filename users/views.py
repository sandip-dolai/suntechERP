from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.views import LoginView
from .forms import LoginForm

# from django.core.mail import send_mail
# from django.conf import settings



@login_required(login_url='/users/login/')
def dashboard_view(request):
    return render(request, 'base/dashboard.html')

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = LoginForm
    
    

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