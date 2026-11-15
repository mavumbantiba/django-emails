from .access import (
    ACCOUNTANT_ROLE,
    ACADEMIC_ROLE,
    SECOND_HEAD_ROLE,
    get_school_role,
)


def school_access(request):
    role = get_school_role(request.user)
    is_superuser = request.user.is_superuser
    return {
        "can_manage_students": is_superuser or role == SECOND_HEAD_ROLE,
        "can_manage_collections": is_superuser
        or role in {ACADEMIC_ROLE, ACCOUNTANT_ROLE},
        "can_manage_store_supplies": is_superuser,
    }
