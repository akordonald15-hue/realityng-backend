from __future__ import annotations

from django.db import models


class NotificationType(models.TextChoices):
    LEAD_ASSIGNED = "lead_assigned", "Lead Assigned"
    LEAD_STAGE_CHANGED = "lead_stage_changed", "Lead Stage Changed"
    FOLLOW_UP_DUE = "follow_up_due", "Follow-up Due"
    NEW_MESSAGE = "new_message", "New Message"
    INQUIRY_CREATED = "inquiry_created", "Inquiry Created"
    INQUIRY_STATUS_CHANGED = "inquiry_status_changed", "Inquiry Status Changed"
    VIEWING_REQUESTED = "viewing_requested", "Viewing Requested"
    VIEWING_CONFIRMED = "viewing_confirmed", "Viewing Confirmed"
    VIEWING_RESCHEDULED = "viewing_rescheduled", "Viewing Rescheduled"
    VIEWING_CANCELLED = "viewing_cancelled", "Viewing Cancelled"
    APPLICATION_SUBMITTED = "application_submitted", "Application Submitted"
    APPLICATION_STATUS_CHANGED = "application_status_changed", "Application Status Changed"
    SYSTEM = "system", "System"


class NotificationChannel(models.TextChoices):
    IN_APP = "in_app", "In-App"
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    PUSH = "push", "Push"
