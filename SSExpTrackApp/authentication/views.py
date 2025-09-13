from django.shortcuts import render, redirect
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from email_validator import validate_email, EmailNotValidError
from django.contrib import messages
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.sites.shortcuts import get_current_site
from .utils import app_token
from django.contrib import auth
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.conf import settings
import threading

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send(fail_silently=False)

class EmailValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        email = data['email']
        try:
            # Validate email
            validate_email(email)
        except EmailNotValidError:
            return JsonResponse({'email_error': 'Email is invalid'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'email_error': 'Sorry email in use, please choose another one.'}, status=400)
        return JsonResponse({'email_valid': True}, status=200)


class UsernameValidationView(View):
    def post(self, request):
        data = json.loads(request.body)
        username = data['username']

        if not str(username).isalnum():
            return JsonResponse({'username_error': 'Username must be alphanumeric.'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'username_error': 'Sorry username in use, please choose another one.'}, status=400)
        return JsonResponse({'username_valid': True}, status=200)
        

class RegisterView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')
    
    def post(self, request):
        # GET USER DATA
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        context = {
            'fieldValues': request.POST
        }

        # VALIDATE
        if not User.objects.filter(username=username).exists():
            if not User.objects.filter(email=email).exists():
                if len(password) < 6:
                    messages.error(request, 'Password must be at least 6 characters long.')
                    return render(request, 'authentication/register.html', context)
                # Create a user account
                user = User.objects.create_user(username=username, email=email)
                user.set_password(password)
                user.is_active = False
                user.save()

                # path_to_view
                # - getting domain we are on
                # - relative url to verification
                # - encode uid
                # - token
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                domain = get_current_site(request).domain
                link = reverse('activate', kwargs={'uidb64': uidb64, 'token': app_token.make_token(user)})

                activate_url = 'http://'+domain+link

                email_subject = 'Activate your account'
                email_body = 'Hi ,'+user.username+'\n\nThank you for registering. Your account has been created successfully!\n\nPlease click the link below to activate your account:\n' + activate_url
                email = EmailMessage(
                    email_subject, 
                    email_body,
                   'noreply@example.com',
                   [email],
                )
                EmailThread(email).start()
                messages.success(request, 'Account created successfully!')
                return render(request, 'authentication/register.html')
            else:
                messages.error(request, 'Email is already in use.')
                return render(request, 'authentication/register.html')
        
        return render(request, 'authentication/register.html')
    

class VerificationView(View):
    def get(self, request, uidb64, token):

        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=id)

            if not app_token.check_token(user, token):
                return redirect('login'+'?message='+'User already activated')
            
            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()
            messages.success(request, 'Account activated successfully!')
            return redirect('login')
        
        except Exception as ex:
            print('Activation error:', ex)
        return redirect('login')

class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']

        if username and password:
            user = auth.authenticate(username=username, password=password)

            if user:
                if user.is_active:
                    auth.login(request, user)
                    messages.success(request, 'Welcome, ' + user.username + ' you are now logged in.')
                    return redirect('expenses')
                
                messages.error(request, 'Account is not active, please check your email to activate your account.')
                return render(request, 'authentication/login.html')
            messages.error(request, 'Invalid credentials, please try again.')
            return render(request, 'authentication/login.html')
        
        messages.error(request, 'Please fill in all fields.')
        return render(request, 'authentication/login.html')
    
class LogoutView(View):
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect('login')
    

class ForgotPasswordView(View):
    def get(self, request):
        return render(request, 'authentication/reset-password.html')
    
    def post(self, request):
        email = request.POST['email']
        context = {
            'values': request.POST
        }

        if not validate_email(email):
            messages.error(request, 'Please enter a valid email address.')
            return render(request, 'authentication/reset-password.html', context)

        current_site = get_current_site(request)
        user = User.objects.filter(email=email).first()   # ✅ FIXED

        if user:
            email_contents = {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': PasswordResetTokenGenerator().make_token(user),
            }

            link  = reverse('set-new-password', kwargs={
                'uidb64': email_contents['uid'],
                'token': email_contents['token']
            })

            reset_url = f"http://{current_site.domain}{link}"
            email_subject = 'Reset your password'

            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
            email = EmailMessage(
                email_subject,
                f"Hi {user.username},\n\nPlease click the link below to reset your password:\n{reset_url}",
                from_email,  # ✅ safe sender
                [user.email]
            )
            EmailThread(email).start()
            messages.success(request, 'Please check your email for the reset link.')
            return render(request, 'authentication/reset-password.html', context)

        messages.error(request, 'Email not found.')
        return render(request, 'authentication/reset-password.html', context)

class SetNewPasswordView(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }

        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                messages.error(request, 'The reset link is invalid, please request a new one.')
                return render(request, 'authentication/reset-password.html')
        except Exception as identifier:
            messages.error(request, 'An error occurred while resetting your password.')
            return render(request, 'authentication/set-new-password.html', context)
        
        return render(request, 'authentication/set-new-password.html', context)

    def post(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'authentication/set-new-password.html', context)
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long.')
            return render(request, 'authentication/set-new-password.html', context)
        
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id)
            user.set_password(password)
            user.save()

            messages.success(request, 'Password reset successful. You can now log in with your new password.')
            return redirect('login')
        except Exception as identifier:
            messages.error(request, 'An error occurred while resetting your password.')
            return render(request, 'authentication/set-new-password.html', context)