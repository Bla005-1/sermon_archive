import os, mimetypes, uuid
from datetime import date
from django.conf import settings

BASE_STORAGE = settings.SERMON_STORAGE_ROOT

def save_attachment_file(sermon, uploaded_file):
    year = sermon.preached_on.year if sermon.preached_on else date.today().year
    root = os.path.join(BASE_STORAGE, str(year), str(sermon.id))
    os.makedirs(root, exist_ok=True)
    fn = f'{uuid.uuid4().hex}__{uploaded_file.name}'
    abs_path = os.path.join(root, fn)
    with open(abs_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)
    rel_path = os.path.relpath(abs_path, BASE_STORAGE)
    return rel_path, {
        'mime_type': mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream',
        'byte_size': uploaded_file.size,
    }

