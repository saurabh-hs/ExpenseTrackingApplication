from .views import LogoutView, RegisterView, SetNewPasswordView, UsernameValidationView, EmailValidationView, VerificationView, LoginView, ForgotPasswordView
from django.urls import path 
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('register', RegisterView.as_view(), name='register'),
    path('login', LoginView.as_view(), name='login'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('validate-username', csrf_exempt(UsernameValidationView.as_view()), name='validate-username'),
    path('validate-email', csrf_exempt(EmailValidationView.as_view()), name='validate-email'),
    path('activate/<uidb64>/<token>', VerificationView.as_view(), name='activate'),
    path('reset-password', ForgotPasswordView.as_view(), name='password_reset'),
    path('set-new-password/<uidb64>/<token>', SetNewPasswordView.as_view(), name='set-new-password'),
]
