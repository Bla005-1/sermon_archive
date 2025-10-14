```
SELECT 
  b.name AS book_name,
  v.chapter,
  v.verse,
  t.translation,
  t.text
FROM bible_books AS b
JOIN bible_verses AS v ON v.book_id = b.book_id
JOIN verse_texts AS t ON t.verse_id = v.verse_id
WHERE b.name = 'John' AND v.chapter = 3 AND v.verse = 16
  AND t.translation = 'KJV';

SELECT 
  sp.ord,
  sp.ref_text,
  sp.context_note,
  sb.name AS start_book,
  sv.chapter AS start_chapter,
  sv.verse AS start_verse,
  eb.name AS end_book,
  ev.chapter AS end_chapter,
  ev.verse AS end_verse
FROM sermon_passages AS sp
JOIN bible_verses AS sv ON sp.start_verse_id = sv.verse_id
JOIN bible_books AS sb ON sv.book_id = sb.book_id
LEFT JOIN bible_verses AS ev ON sp.end_verse_id = ev.verse_id
LEFT JOIN bible_books AS eb ON ev.book_id = eb.book_id
WHERE sp.sermon_id = 42
ORDER BY sp.ord;

SELECT DISTINCT 
  s.sermon_id,
  s.title,
  s.speaker_name,
  s.preached_on
FROM sermons AS s
JOIN sermon_passages AS sp ON sp.sermon_id = s.sermon_id
JOIN bible_verses AS v ON v.verse_id = sp.start_verse_id
JOIN bible_books AS b ON b.book_id = v.book_id
WHERE b.name = 'Romans'
ORDER BY s.preached_on DESC;

SELECT 
  s.title,
  a.original_filename,
  a.mime_type,
  a.byte_size,
  a.created_at
FROM attachments AS a
JOIN sermons AS s ON a.sermon_id = s.sermon_id
WHERE s.sermon_id = 42;

SELECT DISTINCT 
  s.sermon_id,
  s.title,
  s.speaker_name,
  s.preached_on
FROM sermons AS s
JOIN sermon_passages AS sp ON sp.sermon_id = s.sermon_id
JOIN bible_verses AS start_v ON sp.start_verse_id = start_v.verse_id
JOIN bible_verses AS end_v ON sp.end_verse_id = end_v.verse_id
WHERE (start_v.book_id = 43 AND start_v.chapter = 3 AND start_v.verse <= 16)
  AND (end_v.book_id = 43 AND end_v.chapter = 3 AND end_v.verse >= 16);

SELECT 
  s.sermon_id,
  s.title,
  s.preached_on,
  s.speaker_name,
  sp.ref_text AS passage,
  a.original_filename AS attachment
FROM sermons AS s
LEFT JOIN sermon_passages AS sp ON sp.sermon_id = s.sermon_id
LEFT JOIN attachments AS a ON a.sermon_id = s.sermon_id
ORDER BY s.preached_on DESC, sp.ord;

SELECT 
  b.name AS book_name,
  v.chapter,
  v.verse,
  n.note_md,
  n.updated_at
FROM verse_notes AS n
JOIN bible_verses AS v ON n.verse_id = v.verse_id
JOIN bible_books AS b ON v.book_id = b.book_id
WHERE b.name = 'Psalms'
ORDER BY v.chapter, v.verse;
```