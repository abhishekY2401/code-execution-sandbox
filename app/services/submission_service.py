from app.extensions import db
import app.extensions as extensions
from app.models.submission import Submission
from app.utils.enums import ExecutionStatus
from app.workers.tasks import chunk_submissions
from app.services.kubernetes_job_service import count_active_batch_jobs
import logging

logger = logging.getLogger(__name__)

def create_submission(language: str, code: str):
    logger.info(f"Creating submission for language: {language}")
    submission = Submission(
        language=language,
        code=code,
        status=ExecutionStatus.PENDING.value
    )

    try:
        logger.debug("Adding submission to DB")
        db.session.add(submission)
        db.session.commit()
        logger.info(f"Submission committed to DB with ID: {submission.id}")
    except Exception as e:
        logger.error(f"DB commit failed: {str(e)}")
        raise

    # Note: Not enqueuing individual task; use process_pending_batches to batch them
    logger.info("Submission created, waiting for batch processing")

    return submission

def get_submission(submission_id: int):
    logger.debug(f"Fetching submission {submission_id}")
    return Submission.query.get(submission_id)

def process_pending_batches():
    logger.info("Processing pending submissions into batches")
    pending_submissions = Submission.query.filter_by(status=ExecutionStatus.PENDING.value).all()
    logger.info(f"Found {len(pending_submissions)} pending submissions")

    if not pending_submissions:
        logger.info("No pending submissions to process")
        return

    chunks = list(chunk_submissions(pending_submissions))
    logger.info(f"Created {len(chunks)} batches")

    # Limit to MAX_PARALLEL_PODS (based on active k8s batch jobs)
    from app.workers.tasks import MAX_PARALLEL_PODS

    active_jobs = count_active_batch_jobs()
    if active_jobs >= MAX_PARALLEL_PODS:
        logger.info(f"Already {active_jobs} active batch jobs, skipping enqueue")
        return

    available_slots = MAX_PARALLEL_PODS - active_jobs
    chunks_to_process = chunks[:available_slots]
    logger.info(
        f"Processing {len(chunks_to_process)} batches (active jobs: {active_jobs}, slots: {available_slots})"
    )

    for chunk in chunks_to_process:
        submission_ids = [s.id for s in chunk]
        logger.debug(f"Enqueuing batch for submissions: {submission_ids}")
        extensions.task_queue.enqueue(
            "app.workers.tasks.execute_batch_submissions",
            submission_ids
        )
        logger.info(f"Enqueued batch task for {len(submission_ids)} submissions")
        
        # Mark submissions as processing to prevent re-enqueueing
        for s in chunk:
            s.status = ExecutionStatus.PROCESSING.value
        db.session.commit()

    logger.info("Batch processing initiated")
    