from django.apps import AppConfig


class ContributionsystemConfig(AppConfig):
    name = 'ContributionSystem'

    def ready(self):
        from . import audit
