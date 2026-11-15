from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context


DELETE_URL_NAMES = {
    "collection-delete",
    "clothing-verification-delete",
    "parent-delete",
    "student-delete",
    "supply-delete",
}


class SchoolAccountAdapter(DefaultAccountAdapter):
    def get_reauthentication_methods(self, user):
        methods = super().get_reauthentication_methods(user)
        request = context.request
        url_name = (
            request.resolver_match.url_name
            if request and request.resolver_match
            else None
        )
        is_admin_delete = (
            request
            and request.path.startswith("/admin/")
            and url_name
            and url_name.endswith("_delete")
        )
        if url_name in DELETE_URL_NAMES or is_admin_delete:
            return [
                method
                for method in methods
                if method["id"].startswith("mfa_reauthenticate")
            ]
        return methods
