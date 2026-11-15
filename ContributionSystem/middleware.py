from django.conf import settings
from django.shortcuts import redirect

from allauth.mfa.models import Authenticator


class RequireTOTPEnrollmentMiddleware:
    allowed_url_names = {
        "account_confirm_email",
        "account_email",
        "account_email_verification_by_code",
        "account_email_verification_sent",
        "account_logout",
        "account_reauthenticate",
        "mfa_activate_totp",
        "mfa_reauthenticate",
        "mfa_reauthenticate_webauthn",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        match = request.resolver_match
        if match and match.url_name in self.allowed_url_names:
            return None

        if (settings.STATIC_URL and request.path.startswith(settings.STATIC_URL)) or (
            settings.MEDIA_URL and request.path.startswith(settings.MEDIA_URL)
        ):
            return None

        if Authenticator.objects.filter(
            user=request.user,
            type=Authenticator.Type.TOTP,
        ).exists():
            return None

        return redirect("mfa_activate_totp")
