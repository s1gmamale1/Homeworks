"""Seed a realistic v2 demo homework (grade-6 fractions case study) for
integration testing + Playwright screenshots. Idempotent-ish: creates a new HW
each run and prints its id. Run against the local uvicorn on :8765."""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:8765"

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read())

content = {
    "flow_version": "v2",
    "meta": {"title": "Kasrlarni teng bo'lish", "subject_display": "Matematika", "section": "Oddiy kasrlar", "lang": "uz"},
    "case_based_preview": {
        "title": "Sinf tadbirida sharbatni bo'lish",
        "metadata": {"topic": "To'g'ri kasrni natural songa bo'lish", "case_type": "practical", "student_role": "yordamchi"},
        "case_setup": {
            "story": "Sinfingiz tadbir o'tkazmoqda. 3/5 litr apelsin sharbati bor va uni 3 ta bir xil stakanga teng bo'lish kerak.",
            "role": "Siz tadbir yordamchisisiz.",
            "task": "Har bir stakanga qancha sharbat quyilishini aniqlang."
        },
        "checkpoints": [
            {
                "kind": "identify",
                "question": "Bu vaziyatda qaysi amal kerak?",
                "options": ["Ko'paytirish", "Bo'lish", "Qo'shish", "Ayirish"],
                "answer_spec": {"type": "option_index", "expected": 1, "option_count": 4},
                "learning_block": "Teng bo'lish kerak bo'lganda — bo'lish amalini ishlatamiz. 3/5 ni 3 ga bo'lamiz."
            },
            {
                "kind": "decide",
                "question": "To'g'ri amal qaysi?",
                "options": ["3/5 × 3", "3/5 ÷ 3", "3/5 + 3", "3 ÷ 3/5"],
                "answer_spec": {"type": "option_index", "expected": 1, "option_count": 4},
                "learning_block": "Kasrni natural songa bo'lganda maxrajni songa ko'paytiramiz: 3/5 ÷ 3 = 3/15 = 1/5."
            },
            {
                "kind": "justify",
                "question": "Nega 3/5 × 3 noto'g'ri?",
                "options": [
                    "Chunki ko'paytirish natijani kattalashtiradi, lekin bizda atigi 3/5 litr bor",
                    "Chunki ko'paytirish har doim noto'g'ri",
                    "Chunki 3 toq son"
                ],
                "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3},
                "learning_block": "3/5 × 3 = 9/5 litr — bu 3/5 litrdan ko'p, ya'ni mavjud sharbatdan ko'p, demak mantiqsiz."
            }
        ],
        "final_simulation": {
            "correct_path": "3/5 ÷ 3 = 1/5 litr har bir stakanga. To'g'ri!",
            "wrong_path": "Agar 3/5 × 3 = 9/5 litr deb hisoblasangiz — bu imkonsiz, chunki atigi 3/5 litr sharbat bor."
        },
        "feedback_summary": {
            "student_understood": "Teng bo'lish = bo'lish amali",
            "what_to_review": "Kasrni natural songa bo'lish qoidasi"
        },
        "completion_rules": {"pass_condition": "ge_2_of_3"}
    },
    "flashcards": [
        {"id": "fc1", "term": "To'g'ri kasr", "def": "Surati maxrajidan kichik bo'lgan kasr (masalan, 3/5).", "hint": "Surat < maxraj"},
        {"id": "fc2", "term": "Kasrni natural songa bo'lish", "def": "Maxrajni shu songa ko'paytiramiz: a/b ÷ n = a/(b·n).", "example": "3/5 ÷ 3 = 3/15 = 1/5"},
        {"id": "fc3", "term": "3/5 ÷ 3", "def": "1/5", "hint": "Maxrajni 3 ga ko'paytiring"},
        {"id": "fc4", "term": "Surat (numerator)", "def": "Kasrning yuqori qismi — nechta ulush olinganini bildiradi."},
        {"id": "fc5", "term": "Maxraj (denominator)", "def": "Kasrning pastki qismi — butun nechta teng ulushga bo'linganini bildiradi."}
    ],
    "memory_check": {
        "pass_threshold_pct": 60,
        "modes_enabled": ["mcq", "fill_blank", "choose_explanation"],
        "items": [
            {"type": "mcq", "prompt": "3/5 ÷ 3 = ?", "options": ["1/5", "9/5", "3/15", "1/3"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 4}},
            {"type": "fill_blank", "prompt": "Kasrni natural songa bo'lganda, ___ ni songa ko'paytiramiz.", "answer_spec": {"type": "text_fuzzy", "expected": "maxraj"}},
            {"type": "true_false", "prompt": "3/5 × 3 = 9/5 (to'g'rimi?)", "options": ["To'g'ri", "Noto'g'ri"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
            {"type": "choose_explanation", "prompt": "Nega 1/5 to'g'ri javob?", "options": ["3/5 ni 3 ga bo'lsak har stakanga 1/5 tushadi", "Chunki 5 toq son", "Chunki 3 < 5"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3}},
            {"type": "mcq", "prompt": "Teng bo'lish uchun qaysi amal?", "options": ["Bo'lish", "Ko'paytirish", "Qo'shish"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3}}
        ]
    },
    "practice_arc": {"games": ["tile_match", "boss"]},
    "gb_tile_match": [
        {"id": "tm1", "left": "3/5 ÷ 3", "right": "1/5"},
        {"id": "tm2", "left": "Surat", "right": "Kasrning yuqori qismi"},
        {"id": "tm3", "left": "Maxraj", "right": "Kasrning pastki qismi"},
        {"id": "tm4", "left": "To'g'ri kasr", "right": "Surat < maxraj"}
    ],
    "boss_meta": {"boss_name": "Kasr Ustasi", "max_hp": 100},
    "boss_questions": [
        {"q": "NEGA kasrni songa bo'lishda maxrajni ko'paytiramiz? (Why)", "ans": ["chunki ulushlar maydalashadi", "ulush kichrayadi"], "dmg": 34, "answer_spec": {"type": "text_fuzzy", "expected": "ulushlar kichrayadi"}},
        {"q": "QANDAY hisoblaysiz: 2/3 ÷ 4 = ? (How)", "ans": ["2/12", "1/6"], "dmg": 33, "answer_spec": {"type": "text_fuzzy", "expected": "1/6"}},
        {"q": "Natija NIMANI bildiradi: 1/6 litr? (What)", "ans": ["har bir ulush hajmi", "bir qismga to'g'ri keladigan miqdor"], "dmg": 33, "answer_spec": {"type": "text_fuzzy", "expected": "har bir ulushga to'g'ri keladigan miqdor"}}
    ]
}

st, hw = call("POST", "/api/homeworks", {"title": "Kasrlarni teng bo'lish", "subject": "math-algebra", "grade": 6, "mode": "hard"})
assert st == 200, hw
hw_id = hw["id"]
st2, _ = call("PUT", f"/api/homeworks/{hw_id}", {"content_json": content})
assert st2 == 200
print(f"SEEDED_V2_DEMO={hw_id}")
print(f"URL=http://127.0.0.1:8765/h/{hw_id}")
