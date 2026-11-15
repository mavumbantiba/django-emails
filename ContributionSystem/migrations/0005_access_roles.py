from django.conf import settings
from django.db import migrations


ROLE_GROUPS = (
    "Academic",
    "Second Head of School",
    "Accountant/Clerk",
)


def create_role_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    database = schema_editor.connection.alias
    for role_name in ROLE_GROUPS:
        Group.objects.using(database).get_or_create(name=role_name)


class Migration(migrations.Migration):
    dependencies = [
        ("ContributionSystem", "0004_parent_created_by"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(create_role_groups, migrations.RunPython.noop),
    ]
