from flask import Flask
from .extensions import db, init_redis
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # initialize extensions
    db.init_app(app)
    init_redis(app)

    # register blueprints
    # from .routes.submission_routes import submission_bp
    # app.register_blueprint(submission_bp, url_prefix='/api/submissions')
    
    return app