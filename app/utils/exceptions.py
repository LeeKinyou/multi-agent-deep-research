from typing import Any, Dict, Optional


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class TaskNotFoundException(AppException):
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Task {task_id} not found",
            status_code=404,
        )


class PlanNotFoundException(AppException):
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Plan not found for task {task_id}",
            status_code=404,
        )


class InvalidTaskStateException(AppException):
    def __init__(self, task_id: str, current_state: str, expected_state: str):
        super().__init__(
            message=f"Task {task_id} is in {current_state} state, expected {expected_state}",
            status_code=400,
        )


class PlanAlreadyConfirmedException(AppException):
    def __init__(self, task_id: str):
        super().__init__(
            message=f"Plan for task {task_id} is already confirmed",
            status_code=400,
        )
