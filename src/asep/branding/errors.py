"""Errors raised by runtime branding persistence."""

from asep.errors import AsepError


class BrandingStorageError(AsepError):
    code = "BRANDING_STORAGE_ERROR"
    category = "persistence"
    next_action = "Verifique a integridade e as permissões do armazenamento."
    exit_code = 5


class BrandingStorageReadError(BrandingStorageError):
    code = "BRANDING_STORAGE_READ_ERROR"


class BrandingStorageWriteError(BrandingStorageError):
    code = "BRANDING_STORAGE_WRITE_ERROR"


class InvalidBrandingStorageFormatError(BrandingStorageError):
    code = "BRANDING_STORAGE_INVALID"
    category = "validation"
    exit_code = 3


class UnsupportedBrandingStorageVersionError(InvalidBrandingStorageFormatError):
    code = "BRANDING_STORAGE_VERSION_UNSUPPORTED"


__all__ = [
    "BrandingStorageError",
    "BrandingStorageReadError",
    "BrandingStorageWriteError",
    "InvalidBrandingStorageFormatError",
    "UnsupportedBrandingStorageVersionError",
]
