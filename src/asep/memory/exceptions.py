"""Exceções da fronteira de memória."""


class MemoryException(Exception):
    pass


class MemoryValidationError(MemoryException):
    pass


class MemoryNotFoundError(MemoryException):
    pass


class MemoryAlreadyExistsError(MemoryException):
    pass


class MemoryStorageError(MemoryException):
    pass


class MemorySecurityError(MemoryValidationError):
    pass


__all__ = [
    "MemoryAlreadyExistsError",
    "MemoryException",
    "MemoryNotFoundError",
    "MemorySecurityError",
    "MemoryStorageError",
    "MemoryValidationError",
]

