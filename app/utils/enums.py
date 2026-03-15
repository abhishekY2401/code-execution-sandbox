from enum import Enum

class ExecutionStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
