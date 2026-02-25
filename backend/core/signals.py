"""
Auto-log model changes to AuditLog via post_save and post_delete signals.

Tracks models listed in settings.AUDIT_LOG_MODELS.
"""

import logging
import threading

from django.apps import apps
from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import AuditLog

logger = logging.getLogger(__name__)

# Thread-local storage for request context (set by middleware)
_thread_locals = threading.local()


def get_current_user():
    return getattr(_thread_locals, "user", None)


def get_current_ip():
    return getattr(_thread_locals, "ip_address", None)


def set_request_context(user=None, ip_address=None):
    _thread_locals.user = user
    _thread_locals.ip_address = ip_address


def clear_request_context():
    _thread_locals.user = None
    _thread_locals.ip_address = None


_tracked_models_cache = None


def _get_tracked_models():
    """Resolve model strings from settings.AUDIT_LOG_MODELS to actual model classes.

    Results are cached after first call since AUDIT_LOG_MODELS does not
    change at runtime.
    """
    global _tracked_models_cache
    if _tracked_models_cache is not None:
        return _tracked_models_cache

    tracked = set()
    for model_path in getattr(settings, "AUDIT_LOG_MODELS", []):
        try:
            tracked.add(apps.get_model(model_path))
        except LookupError:
            logger.warning("AuditLog: model %s not found, skipping", model_path)
    _tracked_models_cache = tracked
    return _tracked_models_cache


def _should_track(sender):
    """Check if sender is in the tracked models list."""
    return sender in _get_tracked_models()


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if not _should_track(sender):
        return

    # Don't create audit logs for AuditLog itself
    if sender is AuditLog:
        return

    action = "create" if created else "update"
    target_type = sender.__name__
    target_id = str(instance.pk)

    AuditLog.objects.create(
        user=get_current_user(),
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail={"action": action},
        ip_address=get_current_ip(),
    )


@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if not _should_track(sender):
        return

    if sender is AuditLog:
        return

    AuditLog.objects.create(
        user=get_current_user(),
        action="delete",
        target_type=sender.__name__,
        target_id=str(instance.pk),
        detail={"action": "delete"},
        ip_address=get_current_ip(),
    )
