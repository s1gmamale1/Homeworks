"""Seed a v2 demo HW with ALL Practice-Arc game arrays + pre-unlock the gate for
a fixed session, so the games can be browser-walked. Run against :8767."""
import json, urllib.request

BASE = "http://127.0.0.1:8767"
SESSION = "walk-session"

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read())

content = {
    "flow_version": "v2",
    "meta": {"title": "Games Walkthrough Demo", "subject_display": "Matematika", "lang": "uz"},
    "case_based_preview": {
        "title": "Sharbatni bo'lish",
        "case_setup": {"story": "3/5 litr sharbat, 3 ta stakan.", "role": "Yordamchi", "task": "Har stakanga qancha?"},
        "checkpoints": [
            {"kind": "identify", "question": "Qaysi amal?", "options": ["Ko'paytirish", "Bo'lish", "Qo'shish", "Ayirish"],
             "answer_spec": {"type": "option_index", "expected": 1, "option_count": 4}, "learning_block": "Teng bo'lish = bo'lish."},
            {"kind": "decide", "question": "To'g'ri amal?", "options": ["3/5 × 3", "3/5 ÷ 3", "3/5 + 3", "3 ÷ 3/5"],
             "answer_spec": {"type": "option_index", "expected": 1, "option_count": 4}, "learning_block": "3/5 ÷ 3 = 1/5."},
            {"kind": "justify", "question": "Nega 3/5 × 3 noto'g'ri?", "options": ["Natija kattalashadi", "Har doim noto'g'ri", "3 toq"],
             "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3}, "learning_block": "9/5 > 3/5, mantiqsiz."}
        ],
        "final_simulation": {"correct_path": "1/5 litr.", "wrong_path": "9/5 imkonsiz."},
        "feedback_summary": {"student_understood": "Bo'lish amali", "what_to_review": "Kasrni songa bo'lish"},
        "completion_rules": {"pass_condition": "ge_2_of_3"}
    },
    "flashcards": [
        {"id": "fc1", "term": "To'g'ri kasr", "def": "Surati maxrajidan kichik."},
        {"id": "fc2", "term": "3/5 ÷ 3", "def": "1/5"}
    ],
    "memory_check": {
        "pass_threshold_pct": 60,
        "items": [
            {"type": "mcq", "prompt": "3/5 ÷ 3 = ?", "options": ["1/5", "9/5", "3/15", "1/3"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 4}},
            {"type": "fill_blank", "prompt": "Kasrni songa bo'lganda ___ ni ko'paytiramiz.", "answer_spec": {"type": "text_fuzzy", "expected": "maxraj"}},
            {"type": "true_false", "prompt": "3/5 × 3 = 9/5?", "options": ["To'g'ri", "Noto'g'ri"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 2}},
            {"type": "choose_explanation", "prompt": "Nega 1/5?", "options": ["3/5 ni 3 ga bo'lsak", "5 toq", "3 < 5"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3}},
            {"type": "mcq", "prompt": "Teng bo'lish amali?", "options": ["Bo'lish", "Ko'paytirish", "Qo'shish"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3}}
        ]
    },
    "practice_arc": {"games": ["tile_match", "ttt", "adaptive_quiz", "mystery_box", "puzzle_lock", "boss"]},
    "gb_tile_match": [
        {"id": "tm1", "left": "3/5 ÷ 3", "right": "1/5"},
        {"id": "tm2", "left": "Surat", "right": "Yuqori qism"},
        {"id": "tm3", "left": "Maxraj", "right": "Pastki qism"},
        {"id": "tm4", "left": "To'g'ri kasr", "right": "Surat < maxraj"}
    ],
    "gb_ttt": [
        {"id": "ttt1", "q": "3/5 ÷ 3 = ?", "correct": "1/5", "distractors": ["9/5", "3/15", "1/3"]},
        {"id": "ttt2", "q": "2/4 = ?", "correct": "1/2", "distractors": ["2/2", "4/2", "1/4"]},
        {"id": "ttt3", "q": "1/2 + 1/2 = ?", "correct": "1", "distractors": ["2/4", "1/4", "2"]}
    ],
    "gb_adaptive_quiz": [
        {"q": "3/5 ÷ 3 = ?", "options": ["1/5", "9/5", "3/15", "1/3"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 4}},
        {"q": "Kasrni songa bo'lish uchun nimani ko'paytiramiz?", "options": ["Maxraj", "Surat", "Ikkalasi"], "answer_spec": {"type": "option_index", "expected": 0, "option_count": 3}}
    ],
    "gb_mystery_box": [
        {"category": "Ta'rif", "q": "Kasrning pastki qismi nima deyiladi?", "a": "maxraj"},
        {"category": "Hisob", "q": "1/2 + 1/2 = ?", "a": "1"}
    ],
    "gb_puzzle_lock": [
        {"content": "Birinchi tumbler", "q": "3/5 ÷ 3 ning maxraji nechaga ko'payadi?", "a": "3"},
        {"content": "Ikkinchi tumbler", "q": "Natija qanday kasr: 1/5?", "a": "to'g'ri kasr"}
    ],
    "boss_meta": {"boss_name": "Kasr Ustasi", "max_hp": 100},
    "boss_questions": [
        {"q": "NEGA maxrajni ko'paytiramiz? (Why)", "ans": ["ulushlar kichrayadi"], "dmg": 50, "answer_spec": {"type": "text_fuzzy", "expected": "ulushlar kichrayadi"}},
        {"q": "QANDAY: 2/3 ÷ 4 = ? (How)", "ans": ["1/6"], "dmg": 50, "answer_spec": {"type": "text_fuzzy", "expected": "1/6"}}
    ]
}

st, hw = call("POST", "/api/homeworks", {"title": "Games Walkthrough Demo", "subject": "math-algebra", "grade": 6, "mode": "hard"})
assert st == 200, hw
hw_id = hw["id"]
st2, _ = call("PUT", f"/api/homeworks/{hw_id}", {"content_json": content})
assert st2 == 200

# Pre-unlock the gate for SESSION: submit correct CBP (>=2/3) + MC (>=60%) answers.
cbp_answers = ["1", "1", "0"]
for idx, ans in enumerate(cbp_answers):
    call("POST", "/api/ai/check-answer", {"phase": "case_based_preview", "homework_id": hw_id,
         "session_id": SESSION, "item_index": idx, "student_answer": ans})
mc_answers = ["0", "maxraj", "0", "0", "0"]
for idx, ans in enumerate(mc_answers):
    call("POST", "/api/ai/check-answer", {"phase": "memory_check", "homework_id": hw_id,
         "session_id": SESSION, "item_index": idx, "student_answer": ans})

# Confirm gate state.
stg, gate = call("GET", f"/api/runtime/homeworks/{hw_id}/gate-state?session_id={SESSION}")
print(f"SEEDED_HW={hw_id}")
print(f"GATE={json.dumps(gate)}")
print(f"URL=http://127.0.0.1:8767/h/{hw_id}?session={SESSION}")
