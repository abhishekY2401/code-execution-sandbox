from app import create_app
from wait_for_db import wait_for_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Starting application")
wait_for_db()

app = create_app()

@app.route('/health')
def health():
    logger.debug("Health check requested")
    return {"status": "healthy"}

if __name__ == '__main__':
    logger.info("Running Flask app in debug mode")
    app.run(debug=True)