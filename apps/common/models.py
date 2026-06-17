"""Shared abstract model primitives for future domain apps."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone


class UUIDPrimaryKeyMixin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=True)

    def deleted(self) -> SoftDeleteQuerySet:
        return self.filter(deleted_at__isnull=False)

    def delete(self) -> tuple[int, dict[str, int]]:
        updated = self.update(deleted_at=timezone.now())
        return updated, {self.model._meta.label: updated}

    def hard_delete(self) -> tuple[int, dict[str, int]]:
        return super().delete()


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self) -> SoftDeleteQuerySet:
        return super().get_queryset().alive()


class SoftDeleteMixin(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        self.deleted_at = timezone.now()
        update_fields = (
            ["deleted_at", "updated_at"] if hasattr(self, "updated_at") else ["deleted_at"]
        )
        self.save(update_fields=update_fields)
        return 1, {self._meta.label: 1}

    def hard_delete(
        self,
        using: str | None = None,
        keep_parents: bool = False,
    ) -> tuple[int, dict[str, int]]:
        return super().delete(using=using, keep_parents=keep_parents)


class BaseModel(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Base model for mutable domain entities introduced in later sprints."""

    class Meta:
        abstract = True
