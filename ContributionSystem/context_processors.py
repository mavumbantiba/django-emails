from django.conf import settings

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


def umami_tracking(request):
    match = request.resolver_match
    return {
        "umami_script_url": settings.UMAMI_SCRIPT_URL,
        "umami_website_id": settings.UMAMI_WEBSITE_ID,
        "public_site_domain": settings.PUBLIC_SITE_DOMAIN,
        "umami_page_name": (
            match.url_name if match and match.url_name else "page"
        ),
    }
