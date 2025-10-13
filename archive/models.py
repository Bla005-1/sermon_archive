from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone


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
# Bible / Verse data tables
# ----------------------------

class BibleBook(models.Model):
    book_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=64)
    order_num = models.PositiveIntegerField()

    TESTAMENT_CHOICES = [('OT', 'OT'), ('NT', 'NT')]
    testament = models.CharField(max_length=2, choices=TESTAMENT_CHOICES)

    class Meta:
        managed = False
        db_table = 'bible_books'

    def __str__(self):
        return self.name


class BibleVerse(models.Model):
    verse_id = models.BigAutoField(primary_key=True)
    book = models.ForeignKey(BibleBook, models.DO_NOTHING)
    chapter = models.PositiveSmallIntegerField()
    verse = models.PositiveSmallIntegerField()

    class Meta:
        managed = False
        db_table = 'bible_verses'
        unique_together = (('book', 'chapter', 'verse'),)

    def __str__(self):
        return f'{self.book.name} {self.chapter}:{self.verse}'


class VerseText(models.Model):
    verse_text_id = models.BigAutoField(primary_key=True)
    verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    translation = models.CharField(max_length=16)
    text = models.TextField()

    class Meta:
        managed = False
        db_table = 'verse_texts'
        unique_together = (('verse', 'translation'),)


class VerseNote(models.Model):
    note_id = models.BigAutoField(primary_key=True)
    verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    note_md = models.TextField(blank=True, null=True)
    # Avoid NULL on insert from Django; DB has defaults.
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'verse_notes'


# ----------------------------
# Sermon data tables
# ----------------------------

class Sermon(models.Model):
    sermon_id = models.BigAutoField(primary_key=True)
    preached_on = models.DateField()
    title = models.CharField(max_length=256)
    speaker_name = models.CharField(max_length=128, blank=True, null=True)
    series_name = models.CharField(max_length=128, blank=True, null=True)
    location_name = models.CharField(max_length=128, blank=True, null=True)
    notes_md = models.TextField(blank=True, null=True)
    # Avoid NULL on insert; DB has CURRENT_TIMESTAMP defaults.
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'sermons'

    def __str__(self):
        return f'{self.preached_on} — {self.title}'


class Attachment(models.Model):
    attachment_id = models.BigAutoField(primary_key=True)
    # DDL: ON DELETE CASCADE
    sermon = models.ForeignKey(Sermon, models.CASCADE)
    rel_path = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=64, blank=True, null=True)
    byte_size = models.PositiveBigIntegerField(blank=True, null=True)
    # Avoid NULL on insert
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attachments'

    def __str__(self):
        return self.rel_path


class Illustration(models.Model):
    illustration_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=256)
    body_md = models.TextField()
    keywords_csv = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=256, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'illustrations'

    def __str__(self):
        return self.title


class SermonIllustration(models.Model):
    # Composite PK per DDL (PRIMARY KEY (sermon_id, illustration_id))
    pk = models.CompositePrimaryKey('sermon_id', 'illustration_id')
    sermon = models.ForeignKey(Sermon, models.CASCADE)
    illustration = models.ForeignKey(Illustration, models.DO_NOTHING)  # DDL: ON DELETE RESTRICT
    ord = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sermon_illustrations'


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
    sermon = models.ForeignKey(Sermon, models.CASCADE)
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
    