from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone
from typing import TYPE_CHECKING
from apps.bible.models import (
    BibleBook,
    BibleVerse,
    Commentary,
    ChurchFather,
    VerseCrossReference,
    VerseNote,
    VerseText,
)
if TYPE_CHECKING:
    from django.db.models import Manager

# ----------------------------
# Auth / Django system tables
# ----------------------------

class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthGroupPermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthUserGroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigration(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


# ----------------------------
# Sermon data tables
# ----------------------------

class Sermon(models.Model):
    sermon_id = models.BigAutoField(primary_key=True)
    preached_on = models.DateField(blank=True, null=True)
    title = models.CharField(max_length=256)
    speaker_name = models.CharField(max_length=128, blank=True, null=True)
    series_name = models.CharField(max_length=128, blank=True, null=True)
    location_name = models.CharField(max_length=128, blank=True, null=True)
    notes_md = models.TextField(blank=True, null=True)
    # Avoid NULL on insert; DB has CURRENT_TIMESTAMP defaults.
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    preached_on_raw = ''
    if TYPE_CHECKING:
        attachments: Manager['Attachment']
        passages: Manager['SermonPassage']


    class Meta:
        managed = False
        db_table = 'sermons'

    def __str__(self):
        return f'{self.preached_on} — {self.title}'


class Attachment(models.Model):
    attachment_id = models.BigAutoField(primary_key=True)
    # DDL: ON DELETE CASCADE
    sermon = models.ForeignKey(
        Sermon,
        models.CASCADE,
        related_name='attachments',
    )
    rel_path = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    byte_size = models.PositiveBigIntegerField(blank=True, null=True)
    # Avoid NULL on insert
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attachments'

    def __str__(self):
        return self.rel_path


class OrderedPassageManager(models.Manager):
    """
    Transactionally assigns the next `ord` within a sermon to avoid (sermon, ord) unique collisions.
    """
    def add_ordered(self, *, sermon, start_verse, end_verse=None, ref_text=None, context_note=None):
        with transaction.atomic():
            current_max = (
                self.select_for_update()
                .filter(sermon=sermon)
                .aggregate(m=Max('ord'))
                .get('m')
            ) or 0
            return self.create(
                sermon=sermon,
                start_verse=start_verse,
                end_verse=end_verse,
                ref_text=ref_text or '',
                context_note=context_note or '',
                ord=current_max + 1,
            )


class SermonPassage(models.Model):
    id = models.BigAutoField(primary_key=True)
    # DDL: sermon_id FK ON DELETE CASCADE
    sermon = models.ForeignKey(Sermon, models.CASCADE, related_name='passages')
    # DDL: start_verse_id RESTRICT, end_verse_id RESTRICT
    start_verse = models.ForeignKey(BibleVerse, models.RESTRICT)
    end_verse = models.ForeignKey(
        BibleVerse,
        models.RESTRICT,
        related_name='sermonpassage_end_verse_set',
        blank=True,
        null=True
    )
    ref_text = models.CharField(max_length=64, blank=True, null=True)
    context_note = models.CharField(max_length=512, blank=True, null=True)
    # Match DB default (NOT NULL DEFAULT 1) to prevent NULL inserts
    ord = models.PositiveSmallIntegerField(default=1)

    objects = OrderedPassageManager()

    class Meta:
        managed = False
        db_table = 'sermon_passages'
        unique_together = (('sermon', 'ord'),)

    def __str__(self):
        return f'{self.sermon} · {self.ref_text or ""} · #{self.ord}'

    def ref_display(self):
        s, e = self.start_verse, self.end_verse
        if not e or (s.book.book_id == e.book.book_id and s.chapter == e.chapter and s.verse == e.verse):
            return f'{s.book.name} {s.chapter}:{s.verse}'
        if s.book.book_id == e.book.book_id:
            if s.chapter == e.chapter:
                return f'{s.book.name} {s.chapter}:{s.verse}–{e.verse}'
            return f'{s.book.name} {s.chapter}:{s.verse}–{e.chapter}:{e.verse}'
        return f'{s.book.name} {s.chapter}:{s.verse} – {e.book.name} {e.chapter}:{e.verse}'


# ----------------------------
# Bible widget tables
# ----------------------------


class BibleWidgetVerse(models.Model):
    id = models.BigAutoField(primary_key=True)

    start_verse = models.ForeignKey(
        BibleVerse,
        on_delete=models.CASCADE,
        db_column='start_verse_id',
        related_name='widget_start_entries',
    )

    end_verse = models.ForeignKey(
        BibleVerse,
        on_delete=models.CASCADE,
        db_column='end_verse_id',
        related_name='widget_end_entries',
    )

    translation = models.CharField(max_length=16)
    ref = models.CharField(max_length=64)
    display_text = models.TextField()
    weight = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'bible_widget_verses'
        ordering = ('-weight', 'ref')
        constraints = [
            models.UniqueConstraint(
                fields=['start_verse', 'end_verse', 'translation'],
                name='uq_widget_passage_tr'
            ),
            models.CheckConstraint(
                check=models.Q(start_verse__lte=models.F('end_verse')),
                name='chk_start_le_end'
            ),
        ]

    def __str__(self):
        return f'{self.ref} ({self.translation})'
    
