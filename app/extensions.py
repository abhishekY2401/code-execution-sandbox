import redis
from rq import Queue
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging

logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()

redis_conn = None
task_queue = None

def init_redis(app):
    global redis_conn, task_queue
    redis_url = app.config["REDIS_URL"]
    logger.info(f"Initializing Redis connection to {redis_url}")
    redis_conn = redis.from_url(redis_url)
    task_queue = Queue("submission_queue", connection=redis_conn)
    logger.info("Redis and task queue initialized")