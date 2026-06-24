from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("properties", "0003_favorite"),
    ]

    operations = [
        migrations.AlterField(
            model_name="property",
            name="listing_type",
            field=models.CharField(
                choices=[
                    ("sale", "Sale"),
                    ("rent", "Rent"),
                    ("apartment_share", "Apartment Share"),
                ],
                max_length=20,
            ),
        ),
    ]
