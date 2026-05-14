"""Installable Python client for the Sermon Archive API."""

from sermon_archive.client.client import SermonArchiveClient, SermonArchiveClientError

__all__ = ["SermonArchiveClient", "SermonArchiveClientError"]
