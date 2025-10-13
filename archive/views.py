from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import UploadedFile
from django.db.models import Max
from .models import Sermon, BibleBook, BibleVerse, SermonPassage, Attachment
from .verse_parser import tolerant_parse_reference
from .storage import save_attachment_file

@login_required
def sermon_list(request):
    q = request.GET.get('q', '').strip()
    sermons = Sermon.objects.all()
    if q:
        sermons = sermons.filter(title__icontains=q)
    return render(request, 'archive/sermon_list.html', {'sermons': sermons, 'q': q})

@login_required
def sermon_detail(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    return render(request, 'archive/sermon_detail.html', {'sermon': sermon})

@login_required
def sermon_create(request):
    if request.method == 'POST':
        data = request.POST
        sermon = Sermon.objects.create(
            preached_on=data.get('preached_on') or None,
            title=data.get('title', ''),
            speaker_name=data.get('speaker_name', ''),
            series_name=data.get('series_name', ''),
            location_name=data.get('location_name', ''),
            notes_md=data.get('notes_md', ''),
        )
        return redirect('sermon_detail', pk=sermon.pk)
    return render(request, 'archive/sermon_form.html')

@login_required
def sermon_edit(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if request.method == 'POST':
        data = request.POST
        for f in ['preached_on','title','speaker_name','series_name','location_name','notes_md']:
            setattr(sermon, f, data.get(f, getattr(sermon, f)))
        sermon.save()
        return redirect('sermon_detail', pk=sermon.pk)
    return render(request, 'archive/sermon_form.html', {'sermon': sermon})

@login_required
def passage_preview(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    ref_text = request.GET.get('ref', '').strip()
    start_v = end_v = None
    error_message = ''
    if ref_text:
        try:
            start_v, end_v = tolerant_parse_reference(ref_text)
        except ValueError as e:
            error_message = str(e)
    ctx = {
        'sermon': sermon,
        'ref_text': ref_text,
        'start_v': start_v,
        'end_v': end_v,
        'error_message': error_message,
    }
    return render(request, 'archive/_partials/passage_preview.html', ctx)

@login_required
@require_POST
def passage_add(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    ref_text = request.POST.get('ref_text', '').strip()
    context_note = request.POST.get('context_note', '').strip()
    try:
        start_v, end_v = tolerant_parse_reference(ref_text)
    except ValueError as e:
        return HttpResponseBadRequest(str(e))
    next_ord = (
        SermonPassage.objects
        .filter(sermon=sermon)
        .aggregate(m=Max('ord'))['m'] or 0
    ) + 1
    SermonPassage.objects.create(
        sermon=sermon, start_verse=start_v, end_verse=end_v,
        context_note=context_note, ord=next_ord
    )
    passages = (
        SermonPassage.objects
        .filter(sermon=sermon)
        .select_related('start_verse__book', 'end_verse__book')
        .order_by('ord')
    )
    return render(request, 'archive/_partials/passage_list.html', {'sermon': sermon, 'passages': passages})

@login_required
def passage_delete(request, pk: int, ord: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    SermonPassage.objects.filter(sermon=sermon, ord=ord).delete()
    for i, sp in enumerate(
        SermonPassage.objects.filter(sermon=sermon).order_by('ord'), start=1
    ):
        if sp.ord != i:
            sp.ord = i
            sp.save(update_fields=['ord'])
    passages = (
        SermonPassage.objects
        .filter(sermon=sermon)
        .select_related('start_verse__book', 'end_verse__book')
        .order_by('ord')
    )
    return render(request, 'archive/_partials/passage_list.html', {'sermon': sermon, 'passages': passages})

@login_required
@require_POST
def attachment_upload(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    file: UploadedFile = request.FILES.get('attachment')
    if not file:
        return HttpResponseBadRequest('No file provided.')
    rel_path, meta = save_attachment_file(sermon, file)
    Attachment.objects.create(
        sermon=sermon,
        rel_path=rel_path,
        original_filename=file.name,
        mime_type=meta['mime_type'],
        byte_size=meta['byte_size'],
    )
    return render(request, 'archive/_partials/attachment_list.html', {'sermon': sermon})

@login_required
def attachment_delete(request, pk: int, att_id: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    Attachment.objects.filter(sermon=sermon, id=att_id).delete()
    return render(request, 'archive/_partials/attachment_list.html', {'sermon': sermon})

