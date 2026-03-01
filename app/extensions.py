import redis
from rq import Queue
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

redis_conn = None
task_queue = None

def init_redis(app):
    global redis_conn, task_queue
    redis_url = app.config["REDIS_URL"]
    redis_conn = redis.from_url(redis_url)
    task_queue = Queue("submission_queue", connection=redis_conn)