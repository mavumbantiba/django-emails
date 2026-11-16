import secrets
import time

from allauth.account import app_settings as account_settings
from allauth.account.authentication import get_authentication_records
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from allauth.mfa.models import Authenticator


class ResponseSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce
        response = self.get_response(request)
        policy_parts = []
        for directive, sources in settings.SECURE_CSP.items():
            if isinstance(sources, str):
                sources = [sources]
            rendered_sources = [
                source.replace('{nonce}', nonce) for source in sources
            ]
            if rendered_sources:
                policy_parts.append(
                    f"{directive} {' '.join(rendered_sources)}"
                )
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(policy_parts),
        )
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response


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
        if match and match.namespace == "admin" and match.url_name == "logout":
            return None

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
            if not match or match.namespace != "admin":
                return None

            authentication_records = get_authentication_records(request)
            latest_authentication = (
                authentication_records[-1] if authentication_records else {}
            )
            authenticated_at = latest_authentication.get("at")
            has_recent_mfa = (
                latest_authentication.get("method") == "mfa"
                and isinstance(authenticated_at, (int, float))
                and 0
                <= time.time() - authenticated_at
                < account_settings.REAUTHENTICATION_TIMEOUT
            )
            if has_recent_mfa:
                return None

            return redirect(
                f"{reverse('mfa_reauthenticate')}?"
                f"{urlencode({REDIRECT_FIELD_NAME: request.get_full_path()})}"
            )

        return redirect("mfa_activate_totp")
