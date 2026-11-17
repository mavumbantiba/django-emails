from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required


LIBRARY_STAFF_GROUPS = (
    "Academic",
    "Second Head of School",
    "Accountant/Clerk",
)


def can_manage_library(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name__in=LIBRARY_STAFF_GROUPS).exists()
    )


def library_staff_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not can_manage_library(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
