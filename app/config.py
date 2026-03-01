import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/coderunner"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv(
        "REDIS_URL",
        "redis://localhost:6379/0"
    )

    K8S_NAMESPACE = os.getenv(
        "K8S_NAMESPACE",
        "default"
    )