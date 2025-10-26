"""Feature-focused view modules for the archive app."""

from .attachments import attachment_delete, attachment_download, attachment_upload
from .passages import passage_add, passage_delete, passage_edit, passage_preview
from .sermons import sermon_create, sermon_detail, sermon_edit, sermon_list
from .widgets import bible_widget_list, verse_tools

__all__ = [
    'attachment_delete',
    'attachment_download',
    'attachment_upload',
    'bible_widget_list',
    'passage_add',
    'passage_delete',
    'passage_edit',
    'passage_preview',
    'sermon_create',
    'sermon_detail',
    'sermon_edit',
    'sermon_list',
    'verse_tools',
]
