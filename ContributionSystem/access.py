from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import StudentCollection


ACADEMIC_ROLE = "Academic"
SECOND_HEAD_ROLE = "Second Head of School"
ACCOUNTANT_ROLE = "Accountant/Clerk"
ROLE_NAMES = (ACADEMIC_ROLE, SECOND_HEAD_ROLE, ACCOUNTANT_ROLE)

ACCOUNTANT_COLLECTION_CATEGORIES = {
    StudentCollection.Category.TSHIRT,
    StudentCollection.Category.SCHOOL_GUARD_FEE,
    StudentCollection.Category.NECKTIE,
    StudentCollection.Category.TABLE,
    StudentCollection.Category.CHAIR,
}


def get_school_role(user):
    if not user.is_authenticated or user.is_superuser:
        return None

    roles = tuple(
        user.groups.filter(name__in=ROLE_NAMES).values_list("name", flat=True)
    )
    return roles[0] if len(roles) == 1 else None


def has_role(user, *roles):
    return user.is_superuser or get_school_role(user) in roles


def allowed_collection_categories(user):
    if user.is_superuser:
        return tuple(value for value, _ in StudentCollection.Category.choices)

    role = get_school_role(user)
    if role == ACADEMIC_ROLE:
        allowed = {StudentCollection.Category.ACADEMIC_FEE}
    elif role == ACCOUNTANT_ROLE:
        allowed = ACCOUNTANT_COLLECTION_CATEGORIES
    else:
        allowed = set()

    return tuple(
        value
        for value, _ in StudentCollection.Category.choices
        if value in allowed
    )


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not has_role(request.user, *roles):
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
