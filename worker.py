import os
import threading
import time
import multiprocessing
import redis
from rq import Worker
import logging

from app.extensions import db
from app.services.submission_service import process_pending_batches
from app.services.kubernetes_job_service import get_job_status, get_job_logs
from app.models.submission import Submission
from app.utils.enums import ExecutionStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

listen = ['submission_queue']

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
logger.info(f"Connecting to Redis at {redis_url}")
conn = redis.from_url(redis_url)

# Interval (seconds) between enqueue attempts
BATCH_SCHEDULER_INTERVAL = int(os.getenv('BATCH_SCHEDULER_INTERVAL', '30'))
# Number of concurrent RQ worker processes to spawn
RQ_WORKER_PROCESSES = int(os.getenv('RQ_WORKER_PROCESSES', '5'))


def start_batch_scheduler(interval_seconds=BATCH_SCHEDULER_INTERVAL):
    """Periodically triggers batch processing of pending submissions."""

    def loop():
        logger.info(f"Starting batch scheduler (interval: {interval_seconds}s)")
        from app import create_app
        app = create_app()
        with app.app_context():
            while True:
                try:
                    process_pending_batches()
                except Exception as e:
                    logger.exception(f"Batch scheduler error: {e}")
                time.sleep(interval_seconds)

    t = threading.Thread(target=loop, daemon=True, name="BatchScheduler")
    t.start()
    return t


def start_job_reconciler(interval_seconds=BATCH_SCHEDULER_INTERVAL):
    """Periodically reconciles Kubernetes job completion into DB status."""

    def loop():
        logger.info(f"Starting job reconciler (interval: {interval_seconds}s)")
        from app import create_app
        app = create_app()
        with app.app_context():
            while True:
                try:
                    running = Submission.query.filter_by(status=ExecutionStatus.RUNNING.value).all()
                    for sub in running:
                        if not sub.output or not sub.output.startswith("job:"):
                            continue

                        job_name = sub.output.split("job:", 1)[1]
                        status = get_job_status(job_name)

                        if status == "succeeded":
                            sub.status = ExecutionStatus.SUCCESS.value
                            sub.output = get_job_logs(job_name) or ""
                        elif status == "failed":
                            sub.status = ExecutionStatus.FAILED.value
                            sub.output = get_job_logs(job_name) or ""

                    db.session.commit()
                except Exception as e:
                    logger.exception(f"Job reconciler error: {e}")
                time.sleep(interval_seconds)

    t = threading.Thread(target=loop, daemon=True, name="JobReconciler")
    t.start()
    return t


def run_worker_process(name: str):
    logger.info(f"Starting RQ worker process: {name}")
    worker = Worker(listen, connection=conn)
    worker.work()


if __name__ == '__main__':
    logger.info("Starting RQ worker controller")

    # Start background scheduler to automatically enqueue batch jobs
    if os.getenv('BATCH_SCHEDULER_ENABLED', 'true').lower() in ('1', 'true', 'yes'):
        start_batch_scheduler()
    else:
        logger.info("Batch scheduler disabled via BATCH_SCHEDULER_ENABLED")

    processes = []
    for i in range(RQ_WORKER_PROCESSES):
        p = multiprocessing.Process(target=run_worker_process, args=(f"worker-{i+1}",))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()
