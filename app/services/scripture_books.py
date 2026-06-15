"""Bible book names, preferred abbreviations, and lookup aliases."""

from __future__ import annotations

import re


BOOKS: tuple[dict[str, object], ...] = (
    {"name": "Genesis", "abbreviation": "Gen.", "aliases": ["Ge", "Gn"]},
    {"name": "Exodus", "abbreviation": "Ex.", "aliases": ["Exod", "Exo"]},
    {"name": "Leviticus", "abbreviation": "Lev.", "aliases": ["Le", "Lv"]},
    {"name": "Numbers", "abbreviation": "Num.", "aliases": ["Nu", "Nm", "Nb"]},
    {"name": "Deuteronomy", "abbreviation": "Deut.", "aliases": ["De", "Dt"]},
    {"name": "Joshua", "abbreviation": "Josh.", "aliases": ["Jos", "Jsh"]},
    {"name": "Judges", "abbreviation": "Judg.", "aliases": ["Jdg", "Jg", "Jdgs"]},
    {"name": "Ruth", "abbreviation": "Ruth", "aliases": ["Rth", "Ru"]},
    {
        "name": "1 Samuel",
        "abbreviation": "1 Sam.",
        "aliases": [
            "1 Sm",
            "1 Sa",
            "1 S",
            "I Sam",
            "I Sa",
            "1Sam",
            "1Sa",
            "1S",
            "1st Samuel",
            "1st Sam",
            "First Samuel",
            "First Sam",
        ],
    },
    {
        "name": "2 Samuel",
        "abbreviation": "2 Sam.",
        "aliases": [
            "2 Sm",
            "2 Sa",
            "2 S",
            "II Sam",
            "II Sa",
            "2Sam",
            "2Sa",
            "2S",
            "2nd Samuel",
            "2nd Sam",
            "Second Samuel",
            "Second Sam",
        ],
    },
    {
        "name": "1 Kings",
        "abbreviation": "1 Kings",
        "aliases": [
            "1 Kgs",
            "1 Ki",
            "1Kgs",
            "1Kin",
            "1Ki",
            "1K",
            "I Kgs",
            "I Ki",
            "1st Kings",
            "1st Kgs",
            "First Kings",
            "First Kgs",
        ],
    },
    {
        "name": "2 Kings",
        "abbreviation": "2 Kings",
        "aliases": [
            "2 Kgs",
            "2 Ki",
            "2Kgs",
            "2Kin",
            "2Ki",
            "2K",
            "II Kgs",
            "II Ki",
            "2nd Kings",
            "2nd Kgs",
            "Second Kings",
            "Second Kgs",
        ],
    },
    {
        "name": "1 Chronicles",
        "abbreviation": "1 Chron.",
        "aliases": [
            "1 Chr",
            "1 Ch",
            "1Chron",
            "1Chr",
            "1Ch",
            "I Chron",
            "I Chr",
            "I Ch",
            "1st Chronicles",
            "1st Chron",
            "First Chronicles",
            "First Chron",
        ],
    },
    {
        "name": "2 Chronicles",
        "abbreviation": "2 Chron.",
        "aliases": [
            "2 Chr",
            "2 Ch",
            "2Chron",
            "2Chr",
            "2Ch",
            "II Chron",
            "II Chr",
            "II Ch",
            "2nd Chronicles",
            "2nd Chron",
            "Second Chronicles",
            "Second Chron",
        ],
    },
    {"name": "Ezra", "abbreviation": "Ezra", "aliases": ["Ezr", "Ez"]},
    {"name": "Nehemiah", "abbreviation": "Neh.", "aliases": ["Ne"]},
    {"name": "Esther", "abbreviation": "Est.", "aliases": ["Esth", "Es"]},
    {"name": "Job", "abbreviation": "Job", "aliases": ["Jb"]},
    {"name": "Psalms", "abbreviation": "Ps.", "aliases": ["Psalm", "Pslm", "Psa", "Psm", "Pss"]},
    {"name": "Proverbs", "abbreviation": "Prov.", "aliases": ["Prov", "Pro", "Prv", "Pr"]},
    {"name": "Ecclesiastes", "abbreviation": "Eccles.", "aliases": ["Eccle", "Ecc", "Ec", "Qoh", "Qoheleth"]},
    {
        "name": "Song of Solomon",
        "abbreviation": "Song",
        "aliases": ["Song of Songs", "SOS", "So", "Canticle of Canticles", "Canticles", "Cant"],
    },
    {"name": "Isaiah", "abbreviation": "Isa.", "aliases": ["Is"]},
    {"name": "Jeremiah", "abbreviation": "Jer.", "aliases": ["Je", "Jr"]},
    {"name": "Lamentations", "abbreviation": "Lam.", "aliases": ["La"]},
    {"name": "Ezekiel", "abbreviation": "Ezek.", "aliases": ["Eze", "Ezk"]},
    {"name": "Daniel", "abbreviation": "Dan.", "aliases": ["Da", "Dn"]},
    {"name": "Hosea", "abbreviation": "Hos.", "aliases": ["Ho"]},
    {"name": "Joel", "abbreviation": "Joel", "aliases": ["Jl"]},
    {"name": "Amos", "abbreviation": "Amos", "aliases": ["Am"]},
    {"name": "Obadiah", "abbreviation": "Obad.", "aliases": ["Ob"]},
    {"name": "Jonah", "abbreviation": "Jonah", "aliases": ["Jnh", "Jon"]},
    {"name": "Micah", "abbreviation": "Mic.", "aliases": ["Mc"]},
    {"name": "Nahum", "abbreviation": "Nah.", "aliases": ["Na"]},
    {"name": "Habakkuk", "abbreviation": "Hab.", "aliases": ["Hb"]},
    {"name": "Zephaniah", "abbreviation": "Zeph.", "aliases": ["Zep", "Zp"]},
    {"name": "Haggai", "abbreviation": "Hag.", "aliases": ["Hg"]},
    {"name": "Zechariah", "abbreviation": "Zech.", "aliases": ["Zec", "Zc"]},
    {"name": "Malachi", "abbreviation": "Mal.", "aliases": ["Ml"]},
    {"name": "Matthew", "abbreviation": "Matt.", "aliases": ["Mt"]},
    {"name": "Mark", "abbreviation": "Mark", "aliases": ["Mrk", "Mar", "Mk", "Mr"]},
    {"name": "Luke", "abbreviation": "Luke", "aliases": ["Luk", "Lk"]},
    {"name": "John", "abbreviation": "John", "aliases": ["Joh", "Jhn", "Jn"]},
    {"name": "Acts", "abbreviation": "Acts", "aliases": ["Act", "Ac", "Acts of the Apostles"]},
    {"name": "Romans", "abbreviation": "Rom.", "aliases": ["Ro", "Rm"]},
    {
        "name": "1 Corinthians",
        "abbreviation": "1 Cor.",
        "aliases": ["1 Co", "I Cor", "I Co", "1Cor", "1Co", "I Corinthians", "1Corinthians", "1st Corinthians", "First Corinthians"],
    },
    {
        "name": "2 Corinthians",
        "abbreviation": "2 Cor.",
        "aliases": ["2 Co", "II Cor", "II Co", "2Cor", "2Co", "II Corinthians", "2Corinthians", "2nd Corinthians", "Second Corinthians"],
    },
    {"name": "Galatians", "abbreviation": "Gal.", "aliases": ["Ga"]},
    {"name": "Ephesians", "abbreviation": "Eph.", "aliases": ["Ephes"]},
    {"name": "Philippians", "abbreviation": "Phil.", "aliases": ["Php", "Pp"]},
    {"name": "Colossians", "abbreviation": "Col.", "aliases": ["Co"]},
    {
        "name": "1 Thessalonians",
        "abbreviation": "1 Thess.",
        "aliases": ["1 Thes", "1 Th", "I Thessalonians", "I Thess", "I Thes", "I Th", "1Thessalonians", "1Thess", "1Thes", "1Th", "1st Thessalonians", "1st Thess", "First Thessalonians", "First Thess"],
    },
    {
        "name": "2 Thessalonians",
        "abbreviation": "2 Thess.",
        "aliases": ["2 Thes", "2 Th", "II Thessalonians", "II Thess", "II Thes", "II Th", "2Thessalonians", "2Thess", "2Thes", "2Th", "2nd Thessalonians", "2nd Thess", "Second Thessalonians", "Second Thess"],
    },
    {
        "name": "1 Timothy",
        "abbreviation": "1 Tim.",
        "aliases": ["1 Ti", "I Timothy", "I Tim", "I Ti", "1Timothy", "1Tim", "1Ti", "1st Timothy", "1st Tim", "First Timothy", "First Tim"],
    },
    {
        "name": "2 Timothy",
        "abbreviation": "2 Tim.",
        "aliases": ["2 Ti", "II Timothy", "II Tim", "II Ti", "2Timothy", "2Tim", "2Ti", "2nd Timothy", "2nd Tim", "Second Timothy", "Second Tim"],
    },
    {"name": "Titus", "abbreviation": "Titus", "aliases": ["Tit", "Ti"]},
    {"name": "Philemon", "abbreviation": "Philem.", "aliases": ["Phm", "Pm"]},
    {"name": "Hebrews", "abbreviation": "Heb.", "aliases": []},
    {"name": "James", "abbreviation": "James", "aliases": ["Jas", "Jm"]},
    {
        "name": "1 Peter",
        "abbreviation": "1 Pet.",
        "aliases": ["1 Pe", "1 Pt", "1 P", "I Pet", "I Pt", "I Pe", "1Peter", "1Pet", "1Pe", "1Pt", "1P", "I Peter", "1st Peter", "First Peter"],
    },
    {
        "name": "2 Peter",
        "abbreviation": "2 Pet.",
        "aliases": ["2 Pe", "2 Pt", "2 P", "II Peter", "II Pet", "II Pt", "II Pe", "2Peter", "2Pet", "2Pe", "2Pt", "2P", "2nd Peter", "Second Peter"],
    },
    {
        "name": "1 John",
        "abbreviation": "1 John",
        "aliases": ["1 Jhn", "1 Jn", "1 J", "1John", "1Jhn", "1Joh", "1Jn", "1Jo", "1J", "I John", "I Jhn", "I Joh", "I Jn", "I Jo", "1st John", "First John"],
    },
    {
        "name": "2 John",
        "abbreviation": "2 John",
        "aliases": ["2 Jhn", "2 Jn", "2 J", "2John", "2Jhn", "2Joh", "2Jn", "2Jo", "2J", "II John", "II Jhn", "II Joh", "II Jn", "II Jo", "2nd John", "Second John"],
    },
    {
        "name": "3 John",
        "abbreviation": "3 John",
        "aliases": ["3 Jhn", "3 Jn", "3 J", "3John", "3Jhn", "3Joh", "3Jn", "3Jo", "3J", "III John", "III Jhn", "III Joh", "III Jn", "III Jo", "3rd John", "Third John"],
    },
    {"name": "Jude", "abbreviation": "Jude", "aliases": ["Jud", "Jd"]},
    {"name": "Revelation", "abbreviation": "Rev.", "aliases": ["Rev", "Re", "The Revelation", "Revelation of John", "Apocalypse", "Revelations"]},
)


def normalize_book_key(value: str) -> str:
    """Normalize a Bible book spelling or abbreviation for alias lookup."""
    raw = re.sub(r"\s+", " ", value.replace(".", " ")).strip().lower()
    raw = re.sub(r"\bfirst\b|\b1st\b", "1", raw)
    raw = re.sub(r"\bsecond\b|\b2nd\b", "2", raw)
    raw = re.sub(r"\bthird\b|\b3rd\b", "3", raw)
    raw = re.sub(r"\bi{1}\b", "1", raw)
    raw = re.sub(r"\bi{2}\b", "2", raw)
    raw = re.sub(r"\bi{3}\b", "3", raw)
    raw = re.sub(r"^([123])\s+", r"\1", raw)
    return re.sub(r"[^a-z0-9]+", "", raw)


def _build_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for book in BOOKS:
        name = str(book["name"])
        values = [name, str(book["abbreviation"]), *(book.get("aliases") or [])]
        for value in values:
            aliases[normalize_book_key(str(value))] = name
    return aliases


BOOK_ALIASES = _build_aliases()


def canonical_book_name(value: str) -> str | None:
    """Return the canonical book name for a free-form book token."""
    return BOOK_ALIASES.get(normalize_book_key(value))


def all_book_aliases() -> list[str]:
    """Return spellings that should be recognized by reference extraction."""
    aliases: set[str] = set()
    for book in BOOKS:
        aliases.add(str(book["name"]))
        aliases.add(str(book["abbreviation"]))
        aliases.update(str(alias) for alias in (book.get("aliases") or []))
    return sorted(aliases, key=lambda value: (-len(value), value.lower()))
