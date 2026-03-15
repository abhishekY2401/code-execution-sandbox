import json
from app.extensions import db
from app.models.submission import Submission
from app.utils.enums import ExecutionStatus
import logging

from app.services.kubernetes_job_service import (
    create_execution_job,
    create_batch_execution_job,
)

MAX_SUBMISSIONS_PER_POD = 10
MAX_PARALLEL_PODS = 50

logger = logging.getLogger(__name__)

def chunk_submissions(submissions, chunk_size=MAX_SUBMISSIONS_PER_POD):
    logger.debug(f"Chunking {len(submissions)} submissions into chunks of size {chunk_size}")
    for i in range(0, len(submissions), chunk_size):
        yield submissions[i:i + chunk_size]

def execute_batch_submissions(submission_ids):
    logger.info(f"Starting batch execution for submissions {submission_ids}")
    from app import create_app
    app = create_app()

    with app.app_context():
        submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
        if len(submissions) != len(submission_ids):
            missing = set(submission_ids) - {s.id for s in submissions}
            logger.error(f"Missing submissions: {missing}")
            return

        # Prepare data for the job
        submissions_data = [
            {
                "id": s.id,
                "code": s.code,
                "language": s.language
            }
            for s in submissions
        ]

        # Update all to RUNNING
        for s in submissions:
            s.status = ExecutionStatus.RUNNING.value
        db.session.commit()

        try:
            logger.info(f"Creating Kubernetes batch job for {len(submissions)} submissions")
            job_name = create_batch_execution_job(submissions_data)

            logger.info(f"Kubernetes batch job created: {job_name}")

            for s in submissions:
                s.output = f"job:{job_name}"

        except Exception as e:
            logger.error(f"Error creating batch job for submissions {submission_ids}: {str(e)}")
            for s in submissions:
                s.status = ExecutionStatus.FAILED.value
                s.error = str(e)

        logger.info(f"Committing statuses for batch submissions {submission_ids}")
        db.session.commit()