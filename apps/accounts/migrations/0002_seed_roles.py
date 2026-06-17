from django.db import migrations

ROLES = [
    ("tenant", "Local or diaspora rental user."),
    ("buyer", "Property buyer or diaspora investor."),
    ("landlord", "Property owner listing homes or land."),
    ("agent", "Real estate agent representing properties."),
    ("artisan", "Verified service provider or vendor."),
    ("lawyer", "Legal professional providing due diligence."),
    ("inspector", "Property or construction inspector."),
    ("admin", "RealityNG operations administrator."),
    ("super_admin", "RealityNG super administrator."),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for name, description in ROLES:
        Role.objects.update_or_create(name=name, defaults={"description": description})


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(name__in=[name for name, _description in ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
