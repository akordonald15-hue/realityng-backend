from django.db import migrations, models


def remove_lawyer_role(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(name="lawyer").delete()


def restore_lawyer_role(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.get_or_create(
        name="lawyer",
        defaults={"description": "Legal professional providing due diligence."},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_user_managers_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_lawyer_role, restore_lawyer_role),
        migrations.AlterField(
            model_name="role",
            name="name",
            field=models.CharField(
                choices=[
                    ("tenant", "Tenant"),
                    ("buyer", "Buyer"),
                    ("landlord", "Landlord"),
                    ("agent", "Agent"),
                    ("artisan", "Artisan"),
                    ("inspector", "Inspector"),
                    ("admin", "Admin"),
                    ("super_admin", "Super Admin"),
                ],
                max_length=64,
                unique=True,
            ),
        ),
    ]
