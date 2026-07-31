from django.db import migrations


CATEGORIES = [
    (
        "Repairs",
        "repairs",
        "Repair and maintenance services for homes and properties.",
        "wrench",
        10,
        False,
        [
            ("Electrical", "electrical", "Electrical repairs and installations.", "zap", 10, True),
            ("Plumbing", "plumbing", "Plumbing repairs and water systems.", "droplet", 20, True),
            ("Painting", "painting", "Interior and exterior painting.", "paintbrush", 30, False),
            ("Carpentry", "carpentry", "Woodwork, doors, fittings, and repairs.", "hammer", 40, False),
        ],
    ),
    (
        "Utilities",
        "utilities",
        "Installation and utility services for connected properties.",
        "plug",
        20,
        False,
        [
            ("CCTV", "cctv", "CCTV and security camera installation.", "camera", 10, True),
            ("Solar", "solar", "Solar power installation and maintenance.", "sun", 20, True),
            (
                "Internet Installation",
                "internet-installation",
                "Internet and connectivity installation.",
                "wifi",
                30,
                False,
            ),
        ],
    ),
    (
        "Home Services",
        "home-services",
        "Move-in, cleaning, and home support services.",
        "home",
        30,
        False,
        [
            ("Cleaning", "cleaning", "Residential and commercial cleaning.", "sparkles", 10, False),
            ("Moving", "moving", "Moving, relocation, and packing services.", "truck", 20, False),
            ("Pest Control", "pest-control", "Pest inspection and treatment.", "shield", 30, True),
        ],
    ),
    (
        "Construction",
        "construction-services",
        "Construction and professional building services.",
        "hard-hat",
        40,
        False,
        [
            ("Construction", "construction", "General construction services.", "building", 10, True),
            ("Architecture", "architecture", "Architectural design and planning.", "drafting-compass", 20, True),
            ("Surveying", "surveying", "Land and building surveying services.", "map", 30, True),
        ],
    ),
]


def seed_categories(apps, schema_editor):
    TradeCategory = apps.get_model("services", "TradeCategory")
    for name, slug, description, icon, order, requires_certification, children in CATEGORIES:
        parent, _ = TradeCategory.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "icon": icon,
                "display_order": order,
                "requires_certification": requires_certification,
                "is_active": True,
                "parent": None,
            },
        )
        for child_name, child_slug, child_description, child_icon, child_order, child_requires in children:
            TradeCategory.objects.update_or_create(
                slug=child_slug,
                defaults={
                    "name": child_name,
                    "description": child_description,
                    "icon": child_icon,
                    "display_order": child_order,
                    "requires_certification": child_requires,
                    "is_active": True,
                    "parent": parent,
                },
            )


def unseed_categories(apps, schema_editor):
    TradeCategory = apps.get_model("services", "TradeCategory")
    slugs = []
    for _, slug, *_rest, children in CATEGORIES:
        slugs.append(slug)
        slugs.extend(child[1] for child in children)
    TradeCategory.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
