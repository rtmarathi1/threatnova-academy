"""
Shared business logic: progress tracking, lab scoring, and the certification engine.
"""
from __future__ import annotations

import secrets
from . import db


# --------------------------------------------------------------------------- #
# Course structure helpers
# --------------------------------------------------------------------------- #
def course_by_slug(slug):
    return db.query_one("SELECT * FROM courses WHERE slug = ?", (slug,))


def course_lessons(course_id):
    return db.query(
        """SELECT l.* FROM lessons l
           JOIN modules m ON m.id = l.module_id
           WHERE m.course_id = ?
           ORDER BY m.position, l.position""",
        (course_id,),
    )


def course_labs(course_id):
    return db.query("SELECT * FROM labs WHERE course_id = ? ORDER BY position, id", (course_id,))


def course_modules_with_lessons(course_id):
    modules = db.query("SELECT * FROM modules WHERE course_id = ? ORDER BY position, id", (course_id,))
    result = []
    for m in modules:
        lessons = db.query("SELECT * FROM lessons WHERE module_id = ? ORDER BY position, id", (m["id"],))
        result.append({"module": m, "lessons": lessons})
    return result


def is_enrolled(user_id, course_id):
    return db.query_one(
        "SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?", (user_id, course_id)
    )


def enroll(user_id, course_id):
    if not is_enrolled(user_id, course_id):
        db.execute("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", (user_id, course_id))


# --------------------------------------------------------------------------- #
# Progress & scoring
# --------------------------------------------------------------------------- #
def completed_lesson_ids(user_id, course_id):
    rows = db.query(
        """SELECT lp.lesson_id FROM lesson_progress lp
           JOIN lessons l ON l.id = lp.lesson_id
           JOIN modules m ON m.id = l.module_id
           WHERE lp.user_id = ? AND m.course_id = ?""",
        (user_id, course_id),
    )
    return {r["lesson_id"] for r in rows}


def solved_lab_ids(user_id, course_id):
    rows = db.query(
        """SELECT DISTINCT s.lab_id FROM lab_submissions s
           JOIN labs lb ON lb.id = s.lab_id
           WHERE s.user_id = ? AND lb.course_id = ? AND s.correct = 1""",
        (user_id, course_id),
    )
    return {r["lab_id"] for r in rows}


def course_progress(user_id, course_id):
    """Return dict with lesson/lab counts and an overall completion percentage."""
    lessons = course_lessons(course_id)
    labs = course_labs(course_id)
    done_lessons = completed_lesson_ids(user_id, course_id)
    done_labs = solved_lab_ids(user_id, course_id)

    total_units = len(lessons) + len(labs)
    done_units = len([l for l in lessons if l["id"] in done_lessons]) + \
                 len([l for l in labs if l["id"] in done_labs])
    pct = int(round(100 * done_units / total_units)) if total_units else 0

    total_points = sum(l["points"] for l in labs) or 0
    earned_points = sum(l["points"] for l in labs if l["id"] in done_labs)

    return {
        "lessons_total": len(lessons),
        "lessons_done": len([l for l in lessons if l["id"] in done_lessons]),
        "labs_total": len(labs),
        "labs_done": len([l for l in labs if l["id"] in done_labs]),
        "percent": pct,
        "total_points": total_points,
        "earned_points": earned_points,
        "done_lesson_ids": done_lessons,
        "done_lab_ids": done_labs,
    }


def mark_lesson_complete(user_id, lesson_id):
    db.execute(
        "INSERT OR IGNORE INTO lesson_progress (user_id, lesson_id) VALUES (?, ?)",
        (user_id, lesson_id),
    )


# --------------------------------------------------------------------------- #
# Certification engine
# --------------------------------------------------------------------------- #
def _gen_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    block = lambda: "".join(secrets.choice(alphabet) for _ in range(4))
    return f"TN-{block()}-{block()}-{block()}"


def get_certificate(user_id, course_id):
    return db.query_one(
        "SELECT * FROM certificates WHERE user_id = ? AND course_id = ?", (user_id, course_id)
    )


def evaluate_and_issue(user_id, course_id):
    """
    Check whether the student has met the course pass threshold.
    If so (and no certificate exists yet), issue one and mark the enrollment complete.
    Returns the certificate row if issued/existing, else None.
    """
    course = db.query_one("SELECT * FROM courses WHERE id = ?", (course_id,))
    if not course:
        return None

    existing = get_certificate(user_id, course_id)
    if existing:
        return existing

    prog = course_progress(user_id, course_id)
    if prog["percent"] < course["pass_threshold"]:
        return None

    code = _gen_code()
    db.execute(
        "INSERT INTO certificates (code, user_id, course_id, title, score) VALUES (?, ?, ?, ?, ?)",
        (code, user_id, course_id, course["title"], prog["percent"]),
    )
    db.execute(
        "UPDATE enrollments SET completed_at = datetime('now') WHERE user_id = ? AND course_id = ?",
        (user_id, course_id),
    )
    return get_certificate(user_id, course_id)


def verify_certificate(code):
    return db.query_one(
        """SELECT c.*, u.name AS student_name, co.title AS course_title,
                  co.category AS category, co.difficulty AS difficulty
           FROM certificates c
           JOIN users u ON u.id = c.user_id
           JOIN courses co ON co.id = c.course_id
           WHERE c.code = ?""",
        (code.strip().upper(),),
    )



# --------------------------------------------------------------------------- #
# Flag hashing (labs)
# --------------------------------------------------------------------------- #
import hashlib


def hash_flag(flag: str) -> str:
    """Normalize (trim + lowercase) and hash a flag for storage/comparison."""
    normalized = (flag or "").strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def check_flag(lab_row, submitted: str) -> bool:
    return hash_flag(submitted) == lab_row["flag_hash"]
