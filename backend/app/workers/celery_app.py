from celery import Celery
from app.core.config import settings

celery_app = Celery("chess_trainer", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, task_acks_late=True, worker_prefetch_multiplier=1,
                       imports=("app.workers.import_tasks", "app.workers.analysis_tasks"))
celery_app.autodiscover_tasks(["app.workers"])
