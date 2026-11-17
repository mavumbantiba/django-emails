from .access import can_manage_library


def library_access(request):
    return {"can_manage_library": can_manage_library(request.user)}
