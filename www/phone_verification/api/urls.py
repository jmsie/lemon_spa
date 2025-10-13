"""Routing for phone verification API endpoints."""

from django.urls import path

from .views import ResendVerificationCodeView, VerifyCodeView

app_name = "phone_verification"

urlpatterns = [
    path("verify/", VerifyCodeView.as_view(), name="verify"),
    path("resend/", ResendVerificationCodeView.as_view(), name="resend"),
]
