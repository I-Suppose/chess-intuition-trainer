"""Vercel Queues subscriber entrypoint for the Celery tasks."""

from app.workers.celery_app import celery_app as app
from app.workers import analysis_tasks, import_tasks  # noqa: F401

__all__ = ["app"]
