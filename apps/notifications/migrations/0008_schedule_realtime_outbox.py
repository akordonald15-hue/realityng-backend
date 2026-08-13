from __future__ import annotations

import json

from django.db import migrations


def create_realtime_outbox_schedule(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    interval, _ = IntervalSchedule.objects.get_or_create(
        every=30,
        period="seconds",
    )
    PeriodicTask.objects.update_or_create(
        name="Process realtime outbox events",
        defaults={
            "task": "notifications.process_due_realtime_outbox_events",
            "interval": interval,
            "args": json.dumps([]),
            "kwargs": json.dumps({"limit": 100}),
            "enabled": True,
            "description": "Retries due realtime message and notification outbox events.",
        },
    )


def remove_realtime_outbox_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="Process realtime outbox events").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
        ("notifications", "0007_message_thread_sequence_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_realtime_outbox_schedule,
            remove_realtime_outbox_schedule,
        ),
    ]
