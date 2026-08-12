"""Public contracts for canonical runtime branding persistence."""

from asep.branding.errors import (
    BrandingStorageError,
    BrandingStorageReadError,
    BrandingStorageWriteError,
    InvalidBrandingStorageFormatError,
    UnsupportedBrandingStorageVersionError,
)
from asep.branding.file_repository import FileBrandingRepository
from asep.branding.in_memory import InMemoryBrandingRepository
from asep.branding.models import BrandingSettings, DEFAULT_BRANDING_SETTINGS
from asep.branding.repository import BrandingRepository
from asep.branding.serialization import BRANDING_STORAGE_VERSION, BrandingCodec
from asep.branding.sqlite_repository import SQLiteBrandingRepository

__all__ = [
    "BRANDING_STORAGE_VERSION",
    "DEFAULT_BRANDING_SETTINGS",
    "BrandingCodec",
    "BrandingRepository",
    "BrandingSettings",
    "BrandingStorageError",
    "BrandingStorageReadError",
    "BrandingStorageWriteError",
    "FileBrandingRepository",
    "InMemoryBrandingRepository",
    "InvalidBrandingStorageFormatError",
    "SQLiteBrandingRepository",
    "UnsupportedBrandingStorageVersionError",
]
