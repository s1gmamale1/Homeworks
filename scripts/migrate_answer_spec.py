import argparse
import json
import sqlite3
import sys
from pathlib import Path

def guess_type(ans_list: list[str]) -> str:
    """Guess the type of answer_spec based on a list of accepted answers."""
    if not ans_list:
        return "semantic"
    
    # Check if they are all numeric
    all_numeric = True
    for ans in ans_list:
        try:
            float(ans.replace(',', '.'))
        except ValueError:
            all_numeric = False
            break
            
    if all_numeric:
        return "numeric"
    
    # Check for math sets (like ± or multiple numbers separated by comma)
    for ans in ans_list:
        if "±" in ans or ";" in ans or ("," in ans and not all_numeric):
            return "set_match"
            
    # Default to text_fuzzy, or text_exact if it's very short (like a single letter option)
    if len(ans_list) > 0 and len(ans_list[0]) <= 2:
        return "text_exact"
        
    return "text_fuzzy"

def migrate_question(question: dict) -> bool:
    """Migrates a single question dictionary in-place. Returns True if mutated."""
    # Look for the old answers array. Could be 'accepted_answers' or 'ans'
    old_answers = question.get("accepted_answers", question.get("ans", []))
    
    if "answer_spec" in question:
        return False
        
    if not isinstance(old_answers, list):
        if isinstance(old_answers, str):
            old_answers = [old_answers]
        else:
            old_answers = []
            
    ans_type = guess_type(old_answers)
    
    canonical = old_answers[0] if old_answers else ""
    
    if ans_type == "numeric" and canonical:
        try:
            expected = float(canonical.replace(',', '.'))
            if expected.is_integer():
                expected = int(expected)
        except ValueError:
            expected = canonical
            ans_type = "text_fuzzy"
    elif ans_type == "set_match":
        # Best effort basic parse
        expected = old_answers
    else:
        expected = canonical
        
    spec = {
        "type": ans_type,
        "expected": expected,
        "canonical_display": canonical,
        "allow_ai_fallback": True,
        "rubric": {
            "correct": f"Matches {ans_type} expected value.",
            "partial": "Partially correct.",
            "incorrect": "Incorrect."
        }
    }
    
    if ans_type == "numeric":
        spec["tolerance"] = 0
        spec["allow_ai_fallback"] = False
    elif ans_type == "text_exact":
        spec["allow_ai_fallback"] = False

    question["answer_spec"] = spec
    
    # Also standardize the old field to accepted_answers if requested by the user's prompt
    question["accepted_answers"] = old_answers
    if "ans" in question and question["ans"] == old_answers:
        pass # keep it if the app uses it for now
        
    return True

def migrate_content(content: dict) -> bool:
    """Migrates an entire content_json dict in-place."""
    mutated = False
    
    # Boss questions
    if "boss_questions" in content and isinstance(content["boss_questions"], list):
        for q in content["boss_questions"]:
            if migrate_question(q):
                mutated = True
                
    # Adaptive quiz
    if "gb_adaptive_quiz" in content and isinstance(content["gb_adaptive_quiz"], list):
        for q in content["gb_adaptive_quiz"]:
            if migrate_question(q):
                mutated = True
                
    # Memory sprint (sometimes has questions with ans)
    if "ms_questions" in content and isinstance(content["ms_questions"], list):
        for q in content["ms_questions"]:
            if migrate_question(q):
                mutated = True
                
    return mutated

def process_fixtures(dry_run: bool):
    fixtures_dir = Path("fixtures")
    if not fixtures_dir.exists():
        return
        
    for p in fixtures_dir.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = json.load(f)
            
            if migrate_content(content):
                if dry_run:
                    print(f"[DRY RUN] Would update fixture {p.name}")
                else:
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump(content, f, indent=2, ensure_ascii=False)
                    print(f"Updated fixture {p.name}")
        except Exception as e:
            print(f"Error processing {p.name}: {e}")

def process_db(dry_run: bool):
    # Try to find nets.db based on config
    db_path = Path("nets.db")
    if not db_path.exists():
        # Maybe inside server/
        db_path = Path("server/nets.db")
    
    if not db_path.exists():
        print("No SQLite DB found at nets.db or server/nets.db")
        return
        
    print(f"Connecting to DB {db_path}...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Migrate homeworks
    try:
        cursor.execute("SELECT id, content_json FROM homeworks")
        rows = cursor.fetchall()
        for row in rows:
            hw_id = row["id"]
            content_str = row["content_json"]
            if not content_str:
                continue
            try:
                content = json.loads(content_str)
                if migrate_content(content):
                    if dry_run:
                        print(f"[DRY RUN] Would update homework ID {hw_id}")
                    else:
                        new_str = json.dumps(content, ensure_ascii=False)
                        conn.execute("UPDATE homeworks SET content_json = ? WHERE id = ?", (new_str, hw_id))
                        print(f"Updated homework ID {hw_id}")
            except Exception as e:
                print(f"Error migrating homework {hw_id}: {e}")
                
        if not dry_run:
            conn.commit()
    except sqlite3.OperationalError:
        print("homeworks table not found or error reading.")
        
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Migrate answer_spec into content_json for hybrid grading.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without saving.")
    args = parser.parse_args()
    
    print("Processing fixtures...")
    process_fixtures(args.dry_run)
    print("Processing database...")
    process_db(args.dry_run)
    print("Done.")

if __name__ == "__main__":
    main()
