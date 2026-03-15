from flask import Flask
import logging
from app.extensions import db, init_redis, migrate
from app.config import Config
from app.routes.submission_routes import submission_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Log to console
            logging.FileHandler('app.log')  # Log to file
        ]
    )
    app.logger = logging.getLogger(__name__)

    # initialize extensions
    db.init_app(app)
    init_redis(app)
    migrate.init_app(app, db)

    # register blueprints
    app.register_blueprint(submission_bp)

    return app