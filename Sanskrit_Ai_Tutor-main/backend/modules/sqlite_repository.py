import os
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Iterator, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    level TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lesson_completions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lesson_id TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    source TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    lesson_id TEXT NOT NULL,
    quiz_id TEXT NOT NULL,
    score_percent REAL NOT NULL,
    correct_answers INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS grammar_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    input_text TEXT NOT NULL,
    score_percent REAL NOT NULL,
    analysis_mode TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    issue_count INTEGER NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS daily_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity_date TEXT NOT NULL,
    challenge_id TEXT NOT NULL,
    completed INTEGER NOT NULL,
    score_percent REAL,
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, activity_date)
);

CREATE TABLE IF NOT EXISTS xp_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS skill_mastery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    skill_id TEXT NOT NULL,
    mastery REAL NOT NULL,
    attempts INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_lesson_completions_user_completed
    ON lesson_completions (user_id, completed_at);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_submitted
    ON quiz_attempts (user_id, submitted_at);
CREATE INDEX IF NOT EXISTS idx_grammar_attempts_user_created
    ON grammar_attempts (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_daily_activity_user_date
    ON daily_activity (user_id, activity_date);
CREATE INDEX IF NOT EXISTS idx_xp_transactions_user_created
    ON xp_transactions (user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_skill_mastery_user_skill
    ON skill_mastery (user_id, skill_id);
"""


class SQLiteRepository:
    """Persistence boundary for users and learning-progress records."""

    def __init__(self, database_path: str):
        self.database_path = database_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        os.makedirs(os.path.dirname(os.path.abspath(self.database_path)), exist_ok=True)
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def migrate_users(self, users: Dict[str, Dict[str, Any]]) -> int:
        """Copy users into SQLite without changing the source JSON data.

        Existing SQLite rows are left unchanged, making repeated startup
        migrations idempotent and preventing later JSON edits from overwriting
        database values.
        """
        migrated = 0
        with self.connect() as connection:
            for username, user in users.items():
                # Passwords stay in the existing authentication store. This
                # repository contains learning metadata only.
                required_fields = ("role", "level", "created_at")
                if not isinstance(user, dict) or any(field not in user for field in required_fields):
                    raise ValueError(f"Invalid user record for {username!r}")

                changes_before = connection.total_changes
                connection.execute(
                    """
                    INSERT INTO users (username, role, level, created_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(username) DO NOTHING
                    """,
                    (
                        username,
                        user["role"],
                        user["level"],
                        user["created_at"],
                    ),
                )
                migrated += connection.total_changes - changes_before
        return migrated

    def ensure_user(
        self,
        username: str,
        role: str = "student",
        level: str = "beginner",
        created_at: Optional[str] = None,
    ) -> int:
        """Ensure a learning profile exists without storing authentication data."""
        if not isinstance(username, str) or not username.strip():
            raise ValueError("username must be a non-empty string")
        timestamp = created_at or datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO users (username, role, level, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(username) DO NOTHING""",
                (username.strip(), role, level, timestamp),
            )
            row = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username.strip(),)
            ).fetchone()
        return int(row["id"])

    def import_skill_mastery(
        self,
        user_id: int,
        skill_id: str,
        mastery: float,
        attempts: int,
        correct: int,
        updated_at: Optional[str] = None,
    ) -> bool:
        """Import legacy BKT data once; never overwrite an existing SQL record."""
        timestamp = updated_at or datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            cursor = connection.execute(
                """INSERT INTO skill_mastery
                       (user_id, skill_id, mastery, attempts, correct, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, skill_id) DO NOTHING""",
                (user_id, str(skill_id), float(mastery), int(attempts), int(correct), timestamp),
            )
        return cursor.rowcount > 0

    def get_user_id(self, username: str) -> Optional[int]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
        return int(row["id"]) if row else None

    def record_bkt_observation(
        self,
        user_id: int,
        skill_id: str,
        is_correct: bool,
        difficulty: int = 3,
    ) -> Dict[str, Any]:
        """Apply the BKT algorithm and persist mastery for one SQLite user."""
        try:
            from modules.bkt_engine import BKTEngine
        except ImportError:
            # Supports `uvicorn backend.main:app` from the project root.
            from backend.modules.bkt_engine import BKTEngine  # type: ignore

        timestamp = datetime.now(timezone.utc).isoformat()
        skill_key = str(skill_id)
        calculator = BKTEngine.__new__(BKTEngine)
        numeric_skill_id = int(skill_id) if skill_key.isdigit() else 0
        params = calculator.get_skill_params(numeric_skill_id, difficulty)
        with self.connect() as connection:
            row = connection.execute(
                "SELECT mastery, attempts, correct FROM skill_mastery "
                "WHERE user_id = ? AND skill_id = ?",
                (user_id, skill_key),
            ).fetchone()
            current_mastery = float(row["mastery"]) if row else 0.0
            attempts = int(row["attempts"]) if row else 0
            correct = int(row["correct"]) if row else 0
            if attempts == 0:
                current_mastery = params["l0"]
            new_mastery = calculator.update_mastery(current_mastery, is_correct, params)
            attempts += 1
            if is_correct:
                correct += 1
            connection.execute(
                """
                INSERT INTO skill_mastery
                    (user_id, skill_id, mastery, attempts, correct, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, skill_id) DO UPDATE SET
                    mastery = excluded.mastery,
                    attempts = excluded.attempts,
                    correct = excluded.correct,
                    updated_at = excluded.updated_at
                """,
                (user_id, skill_key, new_mastery, attempts, correct, timestamp),
            )
        return {
            "skill_id": skill_id,
            "mastery": new_mastery,
            "attempts": attempts,
            "correct": correct,
        }

    def get_skill_mastery(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """Return only persisted mastery rows belonging to one user."""
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT skill_id, mastery, attempts, correct, updated_at "
                "FROM skill_mastery WHERE user_id = ? ORDER BY skill_id",
                (user_id,),
            ).fetchall()
        return {row["skill_id"]: dict(row) for row in rows}

    def _normalize_utc_date(self, value: Optional[str], field_name: str = "activity_date") -> str:
        if value is None:
            return datetime.now(timezone.utc).date().isoformat()
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a UTC date string")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a valid ISO date or datetime") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date().isoformat()

    def record_learning_day(
        self,
        user_id: int,
        activity_date: Optional[str] = None,
        source: str = "learning_activity",
        challenge_id: str = "learning_activity",
        completed: int = 1,
        score_percent: Optional[float] = None,
        completed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a per-user/day learning summary row without duplicating entries."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        normalized_date = self._normalize_utc_date(activity_date, "activity_date")
        timestamp = completed_at or datetime.now(timezone.utc).isoformat()
        transformed_source = str(source or "learning_activity")
        challenge_name = str(challenge_id or "learning_activity")
        with self.connect() as connection:
            before_count = connection.execute(
                "SELECT COUNT(*) FROM daily_activity WHERE user_id = ? AND activity_date = ?",
                (user_id, normalized_date),
            ).fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO daily_activity
                    (user_id, activity_date, challenge_id, completed, score_percent, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, activity_date) DO NOTHING
                """,
                (
                    user_id,
                    normalized_date,
                    challenge_name,
                    completed,
                    score_percent,
                    timestamp,
                ),
            )
            created = cursor.rowcount > 0
            if not created and before_count == 0:
                created = connection.execute(
                    "SELECT COUNT(*) FROM daily_activity WHERE user_id = ? AND activity_date = ?",
                    (user_id, normalized_date),
                ).fetchone()[0] > 0
            row = connection.execute(
                "SELECT user_id, activity_date, challenge_id, completed, score_percent, completed_at "
                "FROM daily_activity WHERE user_id = ? AND activity_date = ?",
                (user_id, normalized_date),
            ).fetchone()

        return {
            "created": created,
            "user_id": int(row["user_id"]) if row else user_id,
            "activity_date": row["activity_date"] if row else normalized_date,
            "challenge_id": row["challenge_id"] if row else challenge_name,
            "completed": int(row["completed"]) if row else int(completed),
            "score_percent": row["score_percent"] if row else score_percent,
            "completed_at": row["completed_at"] if row else timestamp,
            "source": transformed_source,
        }

    def get_active_dates(self, user_id: int) -> Iterable[str]:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT activity_date FROM daily_activity WHERE user_id = ? ORDER BY activity_date ASC",
                (user_id,),
            ).fetchall()
        return [row["activity_date"] for row in rows]

    def get_streak_summary(self, user_id: int, as_of_utc_date: Optional[str] = None) -> Dict[str, int]:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        active_dates = set(self.get_active_dates(user_id))
        if not active_dates:
            return {"current_streak": 0, "longest_streak": 0, "active_days": 0}

        today = self._normalize_utc_date(as_of_utc_date, "as_of_utc_date")
        today_date = date.fromisoformat(today)

        current_streak = 0
        streak_start = today_date
        if streak_start.isoformat() not in active_dates:
            previous_day = streak_start - timedelta(days=1)
            if previous_day.isoformat() not in active_dates:
                return {"current_streak": 0, "longest_streak": 0, "active_days": len(active_dates)}
            streak_start = previous_day

        cursor_date = streak_start
        while cursor_date.isoformat() in active_dates:
            current_streak += 1
            cursor_date -= timedelta(days=1)

        longest_streak = 0
        current_run = 0
        previous_date = None
        for activity_date in sorted(active_dates):
            current_day = date.fromisoformat(activity_date)
            if previous_date is None:
                current_run = 1
            elif (current_day - previous_date).days == 1:
                current_run += 1
            else:
                current_run = 1
            longest_streak = max(longest_streak, current_run)
            previous_date = current_day

        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "active_days": len(active_dates),
        }

    def complete_lesson(
        self,
        user_id: int,
        lesson_id: str,
        source: str = "lesson",
        completed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record one lesson completion and return its compatibility summary."""
        timestamp = completed_at or datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            changes_before = connection.total_changes
            connection.execute(
                """
                INSERT INTO lesson_completions
                    (user_id, lesson_id, completed_at, source)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, lesson_id) DO NOTHING
                """,
                (user_id, lesson_id, timestamp, source),
            )
            row = connection.execute(
                """
                SELECT id, user_id, lesson_id, completed_at, source
                FROM lesson_completions
                WHERE user_id = ? AND lesson_id = ?
                """,
                (user_id, lesson_id),
            ).fetchone()
            completed_count = connection.execute(
                "SELECT COUNT(*) FROM lesson_completions WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
            created = connection.total_changes > changes_before

        return {
            "created": created,
            "completion": dict(row),
            "completed_count": completed_count,
        }

    def get_completed_lesson_ids(self, user_id: int) -> Iterable[str]:
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT lesson_id FROM lesson_completions WHERE user_id = ? ORDER BY completed_at ASC",
                (user_id,),
            ).fetchall()
        return [row["lesson_id"] for row in rows]

    def get_next_lesson_recommendation(
        self,
        user_id: int,
        lessons: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Choose the next lesson in curriculum order that is ready for the user."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")

        raw_catalog = list(lessons) if lessons is not None else []
        # Safely extract list if wrapped in a dict
        if raw_catalog and isinstance(raw_catalog[0], str) and len(raw_catalog) <= 5:
            return {"status": "no_lessons_available", "lesson_id": None, "title": None, "description": None}

        completed = set(self.get_completed_lesson_ids(user_id))
        module_priority = {
            "module_1_foundations": 1,
            "foundations": 1,
            "module_2_building": 2,
            "building": 2,
            "module_3_nouns": 3,
            "nouns": 3,
            "module_4_tenses": 4,
            "tenses": 4,
            "module_5_grammar": 5,
            "grammar": 5,
            "module_6_syntax": 6,
            "syntax": 6,
            "module_7_advanced": 7,
            "advanced": 7,
        }

        def lesson_order_key(lesson: Dict[str, Any]) -> tuple:
            lesson_id = str(lesson.get("id") or "")
            module_name = str(lesson.get("module") or lesson.get("category") or "")
            module_rank = module_priority.get(module_name, 99)
            file_name = str(lesson.get("file") or lesson_id)
            if file_name.endswith(".json"):
                file_name = file_name[:-5]
            return (module_rank, file_name, lesson_id)

        ordered_lessons = sorted(raw_catalog, key=lesson_order_key)
        for lesson in ordered_lessons:
            if not isinstance(lesson, dict):
                continue
            lesson_id = str(lesson.get("id") or "")
            if not lesson_id or lesson_id in completed:
                continue
            prereqs = lesson.get("prerequisites") or []
            normalized_prereqs = {str(item) for item in prereqs}
            if normalized_prereqs.issubset(completed):
                title = lesson.get("title") or lesson.get("name") or "Introduction to Sanskrit"
                desc = lesson.get("description") or "Continue along your Sanskrit journey."
                est_time = lesson.get("estimated_time") or lesson.get("duration") or 15
                level = lesson.get("level")
                if not level:
                    diff = int(lesson.get("difficulty", 1))
                    level = "beginner" if diff <= 2 else "intermediate" if diff <= 4 else "advanced"

                return {
                    "status": "ready",
                    "lesson_id": lesson_id,
                    "id": lesson_id,
                    "title": title,
                    "description": desc,
                    "module": lesson.get("module") or lesson.get("category"),
                    "estimated_time": est_time,
                    "duration": est_time,
                    "level": level,
                    "prerequisites": list(normalized_prereqs),
                }

        return {
            "status": "all_lessons_completed",
            "lesson_id": None,
            "title": None,
            "description": None,
            "module": None,
            "estimated_time": None,
            "level": None,
            "prerequisites": [],
            "completed_count": len(completed),
        }

    def get_dashboard_summary(
        self,
        user_id: int,
        lessons: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Aggregate dashboard data for one user without exposing raw records."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        with self.connect() as connection:
            lesson_count = connection.execute(
                "SELECT COUNT(*) FROM lesson_completions WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            quiz_stats = connection.execute(
                "SELECT COUNT(*) AS attempts, COALESCE(AVG(score_percent), 0) AS average_score "
                "FROM quiz_attempts WHERE user_id = ?", (user_id,)
            ).fetchone()
            grammar_stats = connection.execute(
                "SELECT COUNT(*) AS attempts, COALESCE(AVG(score_percent), 0) AS average_score "
                "FROM grammar_attempts WHERE user_id = ?", (user_id,)
            ).fetchone()
            recent_rows = connection.execute(
                """
                SELECT activity_type, detail, score_percent, occurred_at
                FROM (
                    SELECT 'lesson' AS activity_type, lesson_id AS detail,
                           NULL AS score_percent, completed_at AS occurred_at
                    FROM lesson_completions WHERE user_id = ?
                    UNION ALL
                    SELECT 'quiz', lesson_id || ':' || quiz_id,
                           score_percent, submitted_at
                    FROM quiz_attempts WHERE user_id = ?
                    UNION ALL
                    SELECT 'grammar', analysis_mode,
                           score_percent, created_at
                    FROM grammar_attempts WHERE user_id = ?
                )
                ORDER BY occurred_at DESC
                LIMIT 10
                """,
                (user_id, user_id, user_id),
            ).fetchall()

        streak = self.get_streak_summary(user_id)
        catalog = list(lessons) if lessons is not None else []
        total_lessons = len(catalog)
        recent_activity = [
            {
                "type": row["activity_type"],
                "detail": row["detail"],
                "score_percent": row["score_percent"],
                "occurred_at": row["occurred_at"],
            }
            for row in recent_rows
        ]
        return {
            "statistics": {
                "lessons_completed": int(lesson_count),
                "total_lessons": total_lessons,
                "quiz_attempts": int(quiz_stats["attempts"]),
                "quiz_average_score": round(float(quiz_stats["average_score"]), 2),
                # Average of THIS user's own grammar-check scores. Kept
                # separate from quiz_average_score so the UI never presents a
                # general quiz average as "grammar accuracy".
                "grammar_activity_count": int(grammar_stats["attempts"]),
                "grammar_average_score": round(float(grammar_stats["average_score"]), 2),
                "current_streak": streak["current_streak"],
                "longest_streak": streak["longest_streak"],
                "active_learning_days": streak["active_days"],
            },
            "recommendation": self.get_next_lesson_recommendation(user_id, catalog),
            "recent_activity": recent_activity,
        }

    def award_xp(
        self,
        user_id: int,
        amount: int,
        reason: str,
        source_type: str,
        source_id: str,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Record one XP award for genuine learning evidence.

        Idempotent on ``idempotency_key`` (the column carries a UNIQUE
        constraint): replaying the same award — refreshing the page,
        resubting a quiz, retrying a completion — is a no-op, so the balance
        can never be inflated by repetition. Callers must therefore derive the
        key from the underlying event (user + lesson/quiz + attempt), never
        from a timestamp or a request counter.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        if not idempotency_key or len(idempotency_key) > 200:
            raise ValueError("idempotency_key is required")
        award = int(amount)
        if award <= 0:
            raise ValueError("amount must be positive")
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO xp_transactions
                    (user_id, amount, reason, source_type, source_id,
                     idempotency_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO NOTHING
                """,
                (
                    user_id,
                    award,
                    reason,
                    source_type,
                    str(source_id),
                    idempotency_key,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            created = cursor.rowcount == 1
        return {"awarded": created, "amount": award if created else 0}

    def get_xp_balance(self, user_id: int) -> int:
        """Total XP earned by one user from persisted transactions."""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        with self.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM xp_transactions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return int(row[0])

    def get_quiz_summary(self, user_id: int) -> Dict[str, Any]:
        """Real, per-user quiz performance derived only from submitted rows.

        Every figure is an aggregate of persisted ``quiz_attempts`` rows —
        nothing is estimated, defaulted or carried over from another account.
        An account with no submissions returns zeroed counts and ``None``
        averages so the UI can render an honest "no attempts yet" state
        instead of a fabricated 0%.
        """
        if not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("user_id must be a positive integer")
        empty: Dict[str, Any] = {
            "attempts": 0,
            "average_score": None,
            "best_score": None,
            "last_score": None,
            "last_submitted_at": None,
            "lessons_attempted": 0,
            "perfect_attempts": 0,
            "questions_correct": 0,
            "questions_answered": 0,
        }
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS attempts,
                       AVG(score_percent) AS average_score,
                       MAX(score_percent) AS best_score,
                       COUNT(DISTINCT lesson_id) AS lessons_attempted,
                       SUM(CASE WHEN score_percent >= 100 THEN 1 ELSE 0 END) AS perfect_attempts,
                       COALESCE(SUM(correct_answers), 0) AS questions_correct,
                       COALESCE(SUM(total_questions), 0) AS questions_answered
                FROM quiz_attempts WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            last = connection.execute(
                """
                SELECT score_percent, submitted_at FROM quiz_attempts
                WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 1
                """,
                (user_id,),
            ).fetchone()

        if row is None or int(row["attempts"]) == 0:
            return empty
        average = row["average_score"]
        best = row["best_score"]
        return {
            "attempts": int(row["attempts"]),
            "average_score": round(float(average), 2) if average is not None else None,
            "best_score": round(float(best), 2) if best is not None else None,
            "last_score": round(float(last["score_percent"]), 2) if last else None,
            "last_submitted_at": last["submitted_at"] if last else None,
            "lessons_attempted": int(row["lessons_attempted"] or 0),
            "perfect_attempts": int(row["perfect_attempts"] or 0),
            "questions_correct": int(row["questions_correct"] or 0),
            "questions_answered": int(row["questions_answered"] or 0),
        }

    def record_quiz_attempt(
        self,
        user_id: int,
        lesson_id: str,
        quiz_id: str,
        score_percent: float,
        correct_answers: int,
        total_questions: int,
        submitted_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist a quiz attempt and assign its per-quiz attempt number."""
        timestamp = submitted_at or datetime.now(timezone.utc).isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous_attempts = connection.execute(
                """
                SELECT COUNT(*) FROM quiz_attempts
                WHERE user_id = ? AND lesson_id = ? AND quiz_id = ?
                """,
                (user_id, lesson_id, quiz_id),
            ).fetchone()[0]
            attempt_number = previous_attempts + 1
            cursor = connection.execute(
                """
                INSERT INTO quiz_attempts
                    (user_id, lesson_id, quiz_id, score_percent,
                     correct_answers, total_questions, submitted_at, attempt_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    lesson_id,
                    quiz_id,
                    score_percent,
                    correct_answers,
                    total_questions,
                    timestamp,
                    attempt_number,
                ),
            )
            attempt_id = cursor.lastrowid

        return {
            "id": attempt_id,
            "user_id": user_id,
            "lesson_id": lesson_id,
            "quiz_id": quiz_id,
            "score_percent": score_percent,
            "correct_answers": correct_answers,
            "total_questions": total_questions,
            "submitted_at": timestamp,
            "attempt_number": attempt_number,
        }

    def record_grammar_activity(
        self,
        user_id: int,
        input_text: str,
        score_percent: float,
        analysis_mode: str,
        word_count: int,
        issue_count: int,
        result: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist one successful grammar analysis for a user."""
        timestamp = created_at or datetime.now(timezone.utc).isoformat()
        result_json = json.dumps(result, ensure_ascii=False)
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO grammar_attempts
                    (user_id, input_text, score_percent, analysis_mode,
                     word_count, issue_count, result_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    input_text,
                    score_percent,
                    analysis_mode,
                    word_count,
                    issue_count,
                    result_json,
                    timestamp,
                ),
            )
            activity_id = cursor.lastrowid

        return {
            "id": activity_id,
            "user_id": user_id,
            "input_text": input_text,
            "score_percent": score_percent,
            "analysis_mode": analysis_mode,
            "word_count": word_count,
            "issue_count": issue_count,
            "result_json": result_json,
            "created_at": timestamp,
        }

    def list_grammar_activities(self, user_id: int, limit: int = 20) -> Iterable[sqlite3.Row]:
        """Return a user's grammar history, newest activity first."""
        safe_limit = max(1, min(int(limit), 100))
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT id, user_id, input_text, score_percent, analysis_mode,
                       word_count, issue_count, result_json, created_at
                FROM grammar_attempts
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, safe_limit),
            ).fetchall()

    def list_users(self) -> Iterable[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                "SELECT id, username, role, level, created_at "
                "FROM users ORDER BY id"
            ).fetchall()
