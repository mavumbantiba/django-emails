import time
from collections.abc import Mapping
from functools import wraps
from typing import Any

from allauth.account import app_settings as account_settings
from allauth.account.authentication import get_authentication_records
from allauth.core.exceptions import ReauthenticationRequired
from allauth.mfa.models import Authenticator
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpRequest


def axes_login_identifier(
    request: HttpRequest,
    credentials: Mapping[str, Any],
) -> str | None:
    identifier = (
        credentials.get('email')
        or credentials.get('username')
        or credentials.get('login')
    )
    return str(identifier).strip().casefold() if identifier else None


def has_recent_mfa_authentication(request):
    records = get_authentication_records(request)
    latest = records[-1] if records else {}
    authenticated_at = latest.get("at")
    return (
        latest.get("method") == "mfa"
        and isinstance(authenticated_at, (int, float))
        and 0
        <= time.time() - authenticated_at
        < account_settings.REAUTHENTICATION_TIMEOUT
    )


def require_mfa_reauthentication(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and Authenticator.objects.filter(user=request.user).exists()
            and not has_recent_mfa_authentication(request)
        ):
            raise ReauthenticationRequired()
        return view_func(request, *args, **kwargs)

    return wrapped_view


def force_logout_home(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        request.GET = request.GET.copy()
        request.GET.pop(REDIRECT_FIELD_NAME, None)
        request.POST = request.POST.copy()
        request.POST.pop(REDIRECT_FIELD_NAME, None)
        return view_func(request, *args, **kwargs)

    return wrapped_view
