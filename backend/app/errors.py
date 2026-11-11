"""Service-layer errors. Adapters map them to HTTP codes / CLI messages."""


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFound(AppError):
    status_code = 404


class Forbidden(AppError):
    status_code = 403


class InvalidTransition(AppError):
    status_code = 409


class Unauthorized(AppError):
    status_code = 401


class LockedOut(AppError):
    status_code = 429
