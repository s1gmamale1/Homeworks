SUBJECTS = [
    "math-algebra",
    "geometriya-g7-11",
    "physics",
    "biology",
    "kimyo-g7-11",
    "english",
    "history",
]

SUBJECT_TO_FAMILY = {
    "math-algebra":     "aniq-fanlar",
    "geometriya-g7-11": "aniq-fanlar",
    "physics":          "tabiy-fanlar",
    "biology":          "tabiy-fanlar",
    "kimyo-g7-11":      "tabiy-fanlar",
    "english":          "til-fanlar",
    "history":          "ijtimoiy-fanlar",
}

ALWAYS_HARD = {"english", "history"}

SUBJECT_GRADES = {
    "math-algebra":     [5, 6, 7, 8, 9, 10, 11],
    "geometriya-g7-11": [7, 8, 9, 10, 11],
    "physics":          [6, 7, 8, 9, 10, 11],
    "biology":          [5, 6, 7, 8, 9, 10, 11],
    "kimyo-g7-11":      [7, 8, 9, 10, 11],
    "english":          [5, 6, 7, 8, 9, 10, 11],
    "history":          [5, 6, 7, 8, 9, 10, 11],
}

# `listening` (graded audio) and `extra_materials` (ungraded links) are
# available in EVERY pipeline: listening sits just after memory_sprint (after
# reading where that exists), extra_materials sits just before reflection. Both
# auto-skip at runtime when their content_json block is empty, so adding them to
# a pipeline only exposes the builder editor — it never forces an empty phase.
PHASE_PIPELINE = {
    ("aniq-fanlar",    "easy"): ["preview", "flashcards", "memory_sprint", "listening", "game_breaks", "extra_materials", "reflection"],
    ("aniq-fanlar",    "hard"): ["preview", "flashcards", "memory_sprint", "listening", "game_breaks", "real_life", "consolidation", "final_challenge", "extra_materials", "reflection"],
    ("tabiy-fanlar",   "easy"): ["preview", "flashcards", "memory_sprint", "listening", "game_breaks", "extra_materials", "reflection"],
    ("tabiy-fanlar",   "hard"): ["preview", "flashcards", "memory_sprint", "listening", "game_breaks", "real_life", "consolidation", "final_challenge", "extra_materials", "reflection"],
    ("til-fanlar",     "hard"): ["preview", "flashcards", "memory_sprint", "reading", "listening", "game_breaks", "real_life", "consolidation", "final_challenge", "extra_materials", "reflection"],
    ("ijtimoiy-fanlar","hard"): ["preview", "flashcards", "memory_sprint", "listening", "game_breaks", "consolidation", "final_challenge", "extra_materials", "reflection"],
}

BOSS_HP = {
    (1, 4):  50,
    (5, 8):  100,
    (9, 11): 150,
}

PHASE_NAMES = {
    "preview":         "Ko'rib chiqish",
    "flashcards":      "Flesh-kartalar",
    "memory_sprint":   "Xotira Sprint",
    "reading":         "O'qish",
    "listening":       "Tinglash",
    "game_breaks":     "O'yin tanaffus",
    "real_life":       "Hayotiy vazifa",
    "consolidation":   "Mustahkamlash",
    "final_challenge": "Yakuniy jang",
    "extra_materials": "Qo'shimcha materiallar",
    "reflection":      "Xulosa",
}

PHASE_ICONS = {
    "preview": "📋", "flashcards": "🃏", "memory_sprint": "⚡",
    "reading": "📖", "listening": "🎧", "game_breaks": "🎮", "real_life": "🌍",
    "consolidation": "🧠", "final_challenge": "👾",
    "extra_materials": "📺", "reflection": "💭",
}

FAMILY_COLORS = {
    "aniq-fanlar":     "#007AFF",
    "tabiy-fanlar":    "#34C759",
    "til-fanlar":      "#AF52DE",
    "ijtimoiy-fanlar": "#FF9500",
}

STATUS_COLORS = {
    "draft":      "#86868b",
    "generating": "#FF9500",
    "ready":      "#34C759",
    "error":      "#FF3B30",
}


def get_family(subject: str) -> str:
    if subject not in SUBJECT_TO_FAMILY:
        raise ValueError(f"Unknown subject: {subject}")
    return SUBJECT_TO_FAMILY[subject]


def get_phases(family: str, mode: str) -> list[str]:
    key = (family, mode)
    if key not in PHASE_PIPELINE:
        raise ValueError(f"No pipeline defined for family={family}, mode={mode}")
    return list(PHASE_PIPELINE[key])


def get_hp(grade: int, subject: str = None) -> int:
    if subject in ("math-algebra",) and grade in (5, 6):
        return 80
    for (low, high), hp in BOSS_HP.items():
        if low <= grade <= high:
            return hp
    raise ValueError(f"Grade {grade} out of range")


def normalize_mode(subject: str, mode: str) -> str:
    if subject in ALWAYS_HARD:
        return "hard"
    if mode not in ("easy", "hard"):
        raise ValueError(f"Invalid mode: {mode}")
    return mode


def validate_grade(subject: str, grade: int) -> bool:
    if subject not in SUBJECT_GRADES:
        return False
    return grade in SUBJECT_GRADES[subject]


def empty_content_scaffold(title: str, subject_display: str) -> dict:
    return {
        "meta": {
            "title": title,
            "subject_display": subject_display,
            "section": "",
            "cefr_level": "",
        },
        "quotes": [],
        "panels": [],
        "flashcards": [],
        "memory_sprint": [],
        "gb_adaptive_quiz": [],
        "gb_why_chain": [],
        "gb_memory_match": [],
        "gb_puzzle_lock": [],
        "gb_mystery_box": [],
        "gb_ttt": [],
        "gb_memory_palace": {},
        "real_life": None,
        "boss_questions": [],
        "reflection": None,
    }
