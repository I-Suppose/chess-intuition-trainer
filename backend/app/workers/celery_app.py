import os
from celery import Celery
from app.core.config import settings

if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
    broker_url = "vercel://"
    result_backend = "vercel-runtime-cache://"
else:
    broker_url = settings.redis_url
    result_backend = settings.redis_url

celery_app = Celery("chess_trainer", broker=broker_url, backend=result_backend)
celery_app.conf.update(task_track_started=True, task_acks_late=True, worker_prefetch_multiplier=1, task_reject_on_worker_lost=True,
                       imports=("app.workers.import_tasks", "app.workers.analysis_tasks"))
celery_app.autodiscover_tasks(["app.workers"])
