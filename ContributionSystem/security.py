import time
from functools import wraps

from allauth.account import app_settings as account_settings
from allauth.account.authentication import get_authentication_records
from allauth.core.exceptions import ReauthenticationRequired
from allauth.mfa.models import Authenticator


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
