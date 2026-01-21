-- Create the database
CREATE DATABASE IF NOT EXISTS sermon_archive;
USE sermon_archive;

-- ------------------------------------------------------------
-- 1. Bible data tables
-- ------------------------------------------------------------

-- List of Bible books (seed once, 66 rows total)
CREATE TABLE bible_books (
  book_id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) NOT NULL,
  order_num TINYINT UNSIGNED NOT NULL,
  testament ENUM('OT', 'NT') NOT NULL
) ENGINE=InnoDB;

-- Each verse in the Bible, translation-independent
CREATE TABLE bible_verses (
  verse_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  book_id TINYINT UNSIGNED NOT NULL,
  chapter SMALLINT UNSIGNED NOT NULL,
  verse SMALLINT UNSIGNED NOT NULL,
  weight FLOAT NOT NULL,
  FOREIGN KEY (book_id) REFERENCES bible_books(book_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Text of each verse for a specific translation (KJV, WEB, etc.)
CREATE TABLE verse_texts (
  verse_text_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  verse_id BIGINT UNSIGNED NOT NULL,
  translation VARCHAR(16) NOT NULL,
  text LONGTEXT NOT NULL,
  FOREIGN KEY (verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE verse_texts_marked (
  verse_text_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  verse_id BIGINT UNSIGNED NOT NULL,
  translation VARCHAR(16) NOT NULL,
  marked_text LONGTEXT NOT NULL,  -- original with markers
  plain_text LONGTEXT NOT NULL,  -- marker-free text for display/search
  FOREIGN KEY (verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  UNIQUE KEY uq_translation_verse (translation, verse_id)
) ENGINE=InnoDB;

-- Personal or study notes on verses
CREATE TABLE verse_notes (
  note_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  verse_id BIGINT UNSIGNED NOT NULL,
  note_md LONGTEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- Cross references between verses
CREATE TABLE verse_crossrefs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  from_verse_id BIGINT UNSIGNED NOT NULL,
  to_start_verse_id BIGINT UNSIGNED NOT NULL,
  to_end_verse_id BIGINT UNSIGNED DEFAULT NULL,
  votes INT,
  note VARCHAR(255),
  UNIQUE KEY uq_cross (from_verse_id, to_start_verse_id, to_end_verse_id),
  FOREIGN KEY (from_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (to_start_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (to_end_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ------------------------------------------------------------
-- 2. Sermon data tables
-- ------------------------------------------------------------

-- Main sermon info
CREATE TABLE sermons (
  sermon_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  preached_on DATE NOT NULL,
  title VARCHAR(256) NOT NULL,
  speaker_name VARCHAR(128),
  series_name VARCHAR(128),
  location_name VARCHAR(128),
  notes_md LONGTEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Files or resources linked to a sermon
CREATE TABLE attachments (
  attachment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  sermon_id BIGINT UNSIGNED NOT NULL,
  rel_path VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255),
  mime_type VARCHAR(64),
  byte_size BIGINT UNSIGNED,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (sermon_id) REFERENCES sermons(sermon_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- Link table: which passages are used in each sermon
CREATE TABLE sermon_passages (
  sermon_id BIGINT UNSIGNED NOT NULL,
  start_verse_id BIGINT UNSIGNED NOT NULL,
  end_verse_id BIGINT UNSIGNED,
  ref_text VARCHAR(64),
  context_note VARCHAR(512),
  ord SMALLINT UNSIGNED DEFAULT 1,
  PRIMARY KEY (sermon_id, ord),
  FOREIGN KEY (sermon_id) REFERENCES sermons(sermon_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (start_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (end_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE bible_widget_verses (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  start_verse_id BIGINT UNSIGNED NOT NULL,
  end_verse_id BIGINT UNSIGNED NOT NULL,
  translation VARCHAR(16) NOT NULL,
  ref VARCHAR(64) NOT NULL,
  display_text TEXT NOT NULL,
  weight SMALLINT UNSIGNED NOT NULL DEFAULT 1, -- relative frequency control
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
             ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT uq_widget_passage_tr UNIQUE (start_verse_id, end_verse_id, translation),
  CONSTRAINT fk_widget_start_verse FOREIGN KEY (start_verse_id)
    REFERENCES bible_verses(verse_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_widget_end_verse FOREIGN KEY (end_verse_id)
    REFERENCES bible_verses(verse_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Church Fathers metadata (one row per author folder)
CREATE TABLE IF NOT EXISTS church_fathers (
  father_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  default_year INT,
  wiki_url VARCHAR(512),
  UNIQUE KEY uq_church_fathers_name (name)
) ENGINE=InnoDB;

-- Individual commentary quotes
CREATE TABLE IF NOT EXISTS commentaries (
  commentary_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  father_id BIGINT UNSIGNED NOT NULL,
  append_to_author_name VARCHAR(255),
  book_id TINYINT UNSIGNED NOT NULL,    -- FK to bible_books
  start_verse_id BIGINT UNSIGNED NOT NULL, -- FK to bible_verses
  end_verse_id BIGINT UNSIGNED NOT NULL,   -- FK to bible_verses
  txt LONGTEXT NOT NULL,
  source_url VARCHAR(2048),
  source_title VARCHAR(512),
  FOREIGN KEY (father_id) REFERENCES church_fathers(father_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (book_id) REFERENCES bible_books(book_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (start_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  FOREIGN KEY (end_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE footnotes (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  verse_id BIGINT UNSIGNED NOT NULL,
  translation VARCHAR(16) NOT NULL,
  order_in_translation INT NOT NULL,     -- corresponds to `o` from VERSION.json
  word_index SMALLINT UNSIGNED NOT NULL, -- corresponds to `w`
  footnote_label VARCHAR(8) NOT NULL,    -- a, b, c, etc.
  footnote_text LONGTEXT NULL,            -- corresponds to `t`

  -- Prevent accidental duplicates
  UNIQUE KEY uq_footnote_location (
    verse_id,
    translation,
    word_index,
    footnote_label
  ),

  KEY idx_footnotes_translation (translation),
  KEY idx_footnotes_verse (verse_id),

  FOREIGN KEY (verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE footnote_cross_refs (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  footnote_id BIGINT UNSIGNED NOT NULL,
  to_start_verse_id BIGINT UNSIGNED NOT NULL,
  to_end_verse_id BIGINT UNSIGNED DEFAULT NULL,

  source_order_number INT DEFAULT NULL, -- number after `*` in JSON
  reference_note VARCHAR(255),          -- optional parsed text if needed

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  KEY idx_crossref_footnote (footnote_id),
  KEY idx_crossref_target_start (to_start_verse_id),
  KEY idx_crossref_target_end (to_end_verse_id),

  UNIQUE KEY uq_cross (footnote_id, to_start_verse_id, to_end_verse_id, source_order_number),
  FOREIGN KEY (to_start_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE,
  FOREIGN KEY (to_end_verse_id) REFERENCES bible_verses(verse_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;
