import time
import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

def wait_for_db():
    database_url = os.getenv(
        "DATABASE_URL"
    )
    logger.info("Waiting for database to be ready")

    while True:
        try:
            logger.debug("Attempting to connect to database")
            conn = psycopg2.connect(database_url)
            conn.close()
            logger.info("Database is ready!")
            break
        except psycopg2.OperationalError as e:
            logger.warning(f"Database not ready: {e}, waiting...")
            time.sleep(2)