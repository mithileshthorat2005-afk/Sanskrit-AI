from fastapi import FastAPI, HTTPException, Depends, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
import sys
import os
import json
from pydantic import BaseModel

# Keep Unicode status messages from optional modules from aborting startup in
# Windows terminals that use a legacy code page.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")

# Allow `uvicorn backend.main:app` from the project root as well as running
# `uvicorn main:app` from backend/.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import existing modules
from modules.database import MockDB
from modules.learning_engine import AdaptiveLearning
from modules.nlp_processor import SanskritNLP
from modules.auth import Authenticator
from modules.translator import SanskritTranslator
from modules.snake_ladder import start_new_game, process_turn
from modules.odd_one_out import get_random_question, check_answer
from modules.skill_mapper import SkillMapper
from modules.sqlite_repository import SQLiteRepository
from modules.auth_dependency import init_auth_dependencies, get_current_user, get_current_user_id, get_optional_user
from modules.translator import SanskritTranslator

app = FastAPI(title="SanskritAI API")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8005",
        "http://127.0.0.1:8005",
    ],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory for data
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Initialize modules
db = MockDB(data_dir=DATA_DIR)
learning_engine = AdaptiveLearning(lessons_file=os.path.join(DATA_DIR, 'lessons.json'))
nlp = SanskritNLP()
auth = Authenticator(users_file=os.path.join(DATA_DIR, 'users.json'))
translator = SanskritTranslator(
    csv_path=os.path.join(DATA_DIR, 'sanskrit_words.csv'),
    sentences_path=os.path.join(DATA_DIR, 'sanskrit_sentences.json')
)
skill_mapper = SkillMapper()
learning_db = SQLiteRepository(
    database_path=os.getenv(
        "SQLITE_DB_PATH", os.path.join(DATA_DIR, "sanskrit_ai.sqlite3")
    )
)
learning_db.initialize()

# Initialize auth dependencies
from modules.auth_dependency import init_auth_dependencies
init_auth_dependencies(auth, learning_db)


def _ensure_learning_user(username: str) -> int:
    """Create a learning-only profile; authentication data stays in users.json."""
    profile = getattr(auth, "users", {}).get(username, {})
    if not isinstance(profile, dict):
        profile = {}
    return learning_db.ensure_user(
        username,
        role=str(profile.get("role", "student")),
        level=str(profile.get("level", "beginner")),
        created_at=profile.get("created_at"),
    )


def _migrate_legacy_bkt_snapshot() -> None:
    """Seed SQLite from legacy BKT JSON without editing or replacing that file."""
    source = os.path.join(DATA_DIR, "bkt_progress.json")
    if not os.path.exists(source):
        return
    try:
        with open(source, "r", encoding="utf-8") as progress_file:
            snapshot = json.load(progress_file)
        if not isinstance(snapshot, dict):
            return
        for username, user_state in snapshot.items():
            if not isinstance(user_state, dict):
                continue
            user_id = _ensure_learning_user(str(username))
            skills = user_state.get("skills", {})
            if not isinstance(skills, dict):
                continue
            for skill_id, mastery in skills.items():
                if not isinstance(mastery, dict):
                    continue
                learning_db.import_skill_mastery(
                    user_id,
                    str(skill_id),
                    mastery.get("mastery", 0.0),
                    mastery.get("attempts", 0),
                    mastery.get("correct", 0),
                )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"SQLite progress migration skipped: {type(exc).__name__}")


_migrate_legacy_bkt_snapshot()

# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str

class SignupRequest(BaseModel):
    username: str
    password: str
    role: str = "student"

class TranslateRequest(BaseModel):
    text: str
    direction: str = "en_to_sa"  # "en_to_sa" or "sa_to_en"
    use_api: bool = True

class GrammarRequest(BaseModel):
    text: str
    use_ai: bool = False

class QuizSubmissionRequest(BaseModel):
    lesson_id: str
    answers: Dict[str, int]
    quiz_id: str = "lesson_quiz"

class DailyActivityRequest(BaseModel):
    activity_date: Optional[str] = None
    score_percent: Optional[float] = None

class GameTurnRequest(BaseModel):
    current_position: int = 0
    asked_word: str
    user_answer: str

class OddAnswerRequest(BaseModel):
    question_data: Dict
    user_choice: int  # 1-based index

# Endpoints
@app.get("/")
def read_root():
    return {"message": "SanskritAI API is running", "status": "online"}

@app.post("/auth/login")
def login(req: LoginRequest):
    user = auth.login(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return user

@app.post("/auth/signup")
def signup(req: SignupRequest):
    user = auth.signup(req.username, req.password, req.role)
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists")
    return user

@app.post("/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    """Revoke the current token."""
    from modules.jwt_auth import revoke_access_token
    if credentials:
        revoke_access_token(credentials.credentials)
    return {"message": "Logged out successfully"}

@app.get("/auth/me")
def get_current_user_info(user: Dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return user

@app.get("/lessons")
def get_lessons(level: Optional[str] = None):
    if level:
        return [l for l in learning_engine.lessons if l.get('level') == level]
    return learning_engine.lessons

@app.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int):
    lesson = next((l for l in learning_engine.lessons if l.get('id') == lesson_id), None)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson

@app.get("/api/lessons/greetings")
def get_greetings_lesson():
    data = db.get_greetings()
    return {"success": True, "data": data}

@app.get("/api/lessons/numbers")
def get_numbers_lesson():
    data = db.get_numbers()
    return {"success": True, "data": data}

@app.get("/api/lessons/self-intro")
def get_self_intro_lesson():
    data = db.get_self_intro()
    return {"success": True, "data": data}

@app.get("/api/lessons/pronouns")
def get_pronouns():
    return db.get_pronouns()

@app.get("/api/lessons/verbs")
def get_verbs():
    return db.get_verbs()

@app.get("/api/lessons/nouns")
def get_nouns():
    return db.get_nouns()

@app.get("/api/lessons/family")
def get_family():
    return db.get_family()

@app.get("/api/lessons/questions")
def get_question_words():
    return db.get_question_words()

@app.get("/api/lessons/time")
def get_time_and_days():
    return db.get_time_and_days()

@app.get("/api/lessons/vibhakti")
def get_vibhakti():
    """Get vibhakti (case) data for Lesson 11"""
    data = db.get_vibhakti()
    return {"success": True, "data": data}

@app.get("/api/lessons/sandhi")
def get_sandhi():
    """Get sandhi data for Lesson 12"""
    data = db.get_sandhi()
    return {"success": True, "data": data}

@app.get("/api/lessons/tenses")
def get_tenses():
    """Get verb tenses data for Lesson 13"""
    data = db.get_tenses()
    return {"success": True, "data": data}

@app.get("/api/lessons/moods")
def get_moods():
    """Get verb moods data for Lesson 14"""
    data = db.get_moods()
    return {"success": True, "data": data}

@app.get("/api/lessons/pronouns-extended")
def get_pronouns_extended():
    """Get extended pronouns data for Lesson 15"""
    data = db.get_pronouns_extended()
    return {"success": True, "data": data}

@app.get("/api/lessons/upasarga")
def get_upasarga():
    """Get upasarga data for Lesson 16"""
    data = db.get_upasarga()
    return {"success": True, "data": data}

@app.get("/api/lessons/voice")
def get_voice():
    """Get active/passive voice data for Lesson 17"""
    data = db.get_voice()
    return {"success": True, "data": data}

@app.get("/api/lessons/indeclinables")
def get_indeclinables():
    """Get indeclinables data for Lesson 18"""
    data = db.get_indeclinables()
    return {"success": True, "data": data}

@app.get("/api/lessons/participles")
def get_participles():
    """Get participles data for Lesson 19"""
    data = db.get_participles()
    return {"success": True, "data": data}

@app.get("/api/lessons/reading-composition")
def get_reading_composition():
    """Get reading and composition data for Lesson 20"""
    data = db.get_reading_composition()
    return {"success": True, "data": data}

@app.get("/api/lessons/samasa1")
def get_samasa1():
    """Get Samāsa Part 1 data for Lesson 21"""
    data = db.get_samasa1()
    return {"success": True, "data": data}

@app.get("/api/lessons/samasa2")
def get_samasa2():
    data = db.get_samasa2()
    return {"success": True, "data": data}

@app.get("/api/lessons/participles2")
def get_participles2():
    data = db.get_participles2()
    return {"success": True, "data": data}

@app.get("/api/lessons/stri-pratyaya")
def get_stri_pratyaya():
    data = db.get_stri_pratyaya()
    return {"success": True, "data": data}

@app.get("/api/lessons/chandas")
def get_chandas():
    data = db.get_chandas()
    return {"success": True, "data": data}

@app.get("/api/daily-questions")
def get_daily_questions():
    with open(os.path.join(DATA_DIR, 'dailyQuestions.json'), encoding='utf-8') as questions_file:
        return json.load(questions_file)

@app.get("/progress")
def get_progress(user: Dict = Depends(get_current_user)):
    username = user["username"]
    user_id = _ensure_learning_user(username)
    progress = db.get_user_progress(username)
    completed_ids = list(learning_db.get_completed_lesson_ids(user_id))
    streak = learning_db.get_streak_summary(user_id)
    # Keep the legacy fields and add persisted completion/streak details.
    return {
        **progress,
        "completed_lesson_ids": completed_ids,
        "lessons_completed": max(int(progress.get("completed", 0)), len(completed_ids)),
        "current_streak": streak["current_streak"],
        "longest_streak": streak["longest_streak"],
    }

@app.get("/activities")
def get_activities(user: Dict = Depends(get_current_user)):
    username = user["username"]
    user_id = _ensure_learning_user(username)
    recent = learning_db.get_dashboard_summary(user_id, learning_engine.lessons)["recent_activity"]
    if not recent:
        return db.get_recent_activities(username)
    activity_names = {"lesson": "Completed lesson", "quiz": "Quiz attempt", "grammar": "Grammar check"}
    return [
        {
            "action": activity_names.get(item["type"], "Learning activity"),
            "details": item["detail"],
            "timestamp": item["occurred_at"],
            "score": f"{item['score_percent']}%" if item["score_percent"] is not None else "",
        }
        for item in recent
    ]


@app.get("/dashboard")
def get_persisted_dashboard(user: Dict = Depends(get_current_user)):
    username = user["username"]
    user_id = _ensure_learning_user(username)
    summary = learning_db.get_dashboard_summary(user_id, learning_engine.lessons)
    mastery = learning_db.get_skill_mastery(user_id)
    summary["mastery"] = {
        "average": round(sum(item["mastery"] for item in mastery.values()) / len(mastery), 4) if mastery else 0.0,
        "mastered_skills": sum(1 for item in mastery.values() if item["mastery"] >= 0.7),
        "skills": mastery,
    }
    return summary


@app.get("/streak")
def get_learning_streak(user: Dict = Depends(get_current_user)):
    username = user["username"]
    return learning_db.get_streak_summary(_ensure_learning_user(username))


@app.post("/streak/activity")
def record_daily_activity(req: DailyActivityRequest, user: Dict = Depends(get_current_user)):
    username = user["username"]
    return learning_db.record_learning_day(
        _ensure_learning_user(username),
        activity_date=req.activity_date,
        source="daily_streak",
        challenge_id="daily_questions",
        completed=1,
        score_percent=req.score_percent,
    )


@app.post("/progress/complete")
def complete_lesson(payload: Dict[str, Any] = Body(...), user: Dict = Depends(get_current_user)):
    username = user["username"]
    lesson_id = payload.get("lesson_id")
    if not isinstance(lesson_id, (int, str)) or not str(lesson_id).strip():
        raise HTTPException(status_code=400, detail="lesson_id is required")
    lesson = next((item for item in learning_engine.lessons if str(item.get("id")) == str(lesson_id)), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    user_id = _ensure_learning_user(username)
    completion = learning_db.complete_lesson(user_id, str(lesson_id))
    if completion["created"]:
        db.update_progress(username, int(lesson_id), "completed")
        learning_db.record_learning_day(user_id, source="lesson")
    return {
        "success": True,
        "username": username,
        "lesson_id": str(lesson_id),
        "completed": completion["completed_count"],
        "message": "Lesson marked as complete",
    }


def _get_lesson_quiz_questions(lesson: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return normalized quiz questions for either lesson format.

    New format: lesson["sections"] entries with {"type": "quiz",
    "questions": [{"id", "correct"}]} where "correct" is the right option index.
    Legacy format (lessons.json): lesson["quiz"] entries with
    {"id", "question", "options", "answer"} where the correct option index is
    the position of "answer" within "options".
    """
    sections = lesson.get("sections") or []
    section_questions = [
        question
        for section in sections if section.get("type") == "quiz"
        for question in section.get("questions", [])
    ]
    if section_questions:
        return [
            {"id": str(question.get("id")), "correct": question.get("correct")}
            for question in section_questions
        ]
    legacy = lesson.get("quiz") or []
    normalized = []
    for question in legacy:
        options = question.get("options", []) or []
        try:
            correct = options.index(question.get("answer"))
        except ValueError:
            correct = 0
        normalized.append({"id": str(question.get("id")), "correct": correct})
    return normalized


@app.post("/progress/quiz")
def submit_lesson_quiz(req: QuizSubmissionRequest, user: Dict = Depends(get_current_user)):
    username = user["username"]
    lesson = next((item for item in learning_engine.lessons if str(item.get("id")) == str(req.lesson_id)), None)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if not req.quiz_id or len(req.quiz_id) > 128:
        raise HTTPException(status_code=400, detail="quiz_id is invalid")
    questions = _get_lesson_quiz_questions(lesson)
    if not questions:
        raise HTTPException(status_code=400, detail="Lesson has no quiz")
    expected_ids = {str(question.get("id")) for question in questions}
    if set(req.answers) != expected_ids:
        raise HTTPException(status_code=400, detail="All quiz answers are required")
    correct_answers = sum(
        req.answers[str(question["id"])] == question.get("correct") for question in questions
    )
    total_questions = len(questions)
    score = round(correct_answers * 100 / total_questions, 2)
    user_id = _ensure_learning_user(username)
    attempt = learning_db.record_quiz_attempt(
        user_id, str(req.lesson_id), req.quiz_id, score, correct_answers, total_questions
    )
    mastery = None
    difficulty = int(lesson.get("difficulty", 3))
    for question in questions:
        is_correct = req.answers[str(question["id"])] == question.get("correct")
        mastery = learning_db.record_bkt_observation(user_id, req.lesson_id, is_correct, difficulty)
        db.record_bkt_attempt(username, int(req.lesson_id), is_correct, difficulty)
    learning_db.record_learning_day(user_id, source="quiz", score_percent=score)
    if correct_answers == total_questions:
        completion = learning_db.complete_lesson(user_id, str(req.lesson_id), source="quiz")
        if completion["created"]:
            db.update_progress(username, int(req.lesson_id), "completed")
    return {**attempt, "mastery": mastery}

@app.post("/translate")
def translate_text(req: TranslateRequest):
    try:
        if req.direction == "en_to_sa":
            result = translator.English_to_sanskrit(req.text, req.use_api)
        else:
            result = translator.sanskrit_to_English(req.text, req.use_api)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/grammar/check")
def check_grammar(req: GrammarRequest, user: Optional[Dict] = Depends(get_optional_user)):
    analysis = nlp.analyze_text(req.text, use_ai=req.use_ai)
    if "error" in analysis:
        return analysis

    bkt_updates = []
    skipped_issues = []
    seen_skill_ids = set()

    # Only persist grammar outcomes when the caller identifies the learner.
    # This keeps old clients compatible and avoids assigning attempts to a
    # shared demo account by default.
    if user:
        username = user["username"]
        learning_user_id = _ensure_learning_user(username)
        for issue in analysis.get("issues", []):
            raw_error_type = (
                issue.get("error_type", "") if isinstance(issue, dict)
                else str(issue)
            )
            skill_info = skill_mapper.map_error_to_skill(raw_error_type)
            if skill_info is None:
                skipped_issues.append({
                    "raw_error_type": raw_error_type,
                    "reason": "unmapped error type; no BKT update",
                })
                continue

            skill_id = skill_info.get("skill_id")
            if skill_id is None or skill_id in seen_skill_ids:
                continue
            seen_skill_ids.add(skill_id)

            lesson = next(
                (item for item in learning_engine.lessons if item.get("id") == skill_id),
                None,
            )
            difficulty = (lesson or {}).get("difficulty", skill_info.get("difficulty", 3))
            result = db.record_bkt_attempt(
                username, skill_id, is_correct=False, difficulty=difficulty
            )
            learning_db.record_bkt_observation(
                learning_user_id, skill_id, is_correct=False, difficulty=difficulty
            )
            bkt_updates.append({
                "error_type": skill_mapper.normalize_error_type(raw_error_type),
                "skill_id": skill_id,
                "skill_name": skill_info.get("skill_name"),
                "mastery": result["mastery"],
                "attempts": result["attempts"],
            })

        learning_db.record_grammar_activity(
            user_id=learning_user_id,
            input_text=req.text,
            score_percent=float(analysis.get("score", 0)),
            analysis_mode=str(analysis.get("analysis_mode", "Grammar Check")),
            word_count=int(analysis.get("word_count", 0)),
            issue_count=len(analysis.get("issues", [])),
            result=analysis,
        )
        learning_db.record_learning_day(learning_user_id, source="grammar")

    recommendation = (
        db.get_bkt_recommendation(username, learning_engine.lessons)
        if user and bkt_updates else None
    )
    return {
        **analysis,
        "bkt_updates": bkt_updates,
        "skipped_issues": skipped_issues,
        "recommendation": recommendation,
    }

@app.get("/dashboard/stats")
def get_dashboard_stats(user: Dict = Depends(get_current_user)):
    username = user["username"]
    progress = db.get_user_progress(username)
    user_id = _ensure_learning_user(username)
    summary = learning_db.get_dashboard_summary(user_id, learning_engine.lessons)
    activities = summary["recent_activity"] or db.get_recent_activities(username)
    stats = translator.get_database_stats()
    return {
        "words_learned": len(activities),
        "lessons_completed": max(progress.get('completed', 0), summary["statistics"]["lessons_completed"]),
        "current_level": progress.get('level', 'beginner'),
        "points": progress.get('points', 0),
        "db_stats": stats,
        "learning_stats": summary["statistics"],
    }


@app.get("/grammar/history")
def get_grammar_history(limit: int = 20, user: Dict = Depends(get_current_user)):
    username = user["username"]
    rows = learning_db.list_grammar_activities(_ensure_learning_user(username), limit)
    return [
        {
            "id": row["id"],
            "input_text": row["input_text"],
            "score_percent": row["score_percent"],
            "analysis_mode": row["analysis_mode"],
            "word_count": row["word_count"],
            "issue_count": row["issue_count"],
            "result": json.loads(row["result_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]

# ─── Suggestions Endpoint (Local DB + Groq Fallback) ──────────────────────────
@app.get("/suggestions")
def get_suggestions(prefix: str, limit: int = 6):
    """
    Return Devanagari word suggestions using local DB + Groq API.
    """
    if not prefix or len(prefix) < 1:
        return {"suggestions": []}
    
    matches = []
    seen = set()
    
    # First, search local database in 'devanagari' column
    df = translator.df
    for _, row in df.iterrows():
        dev = str(row.get('devanagari', ''))
        if dev.startswith(prefix) and dev not in seen:
            seen.add(dev)
            matches.append({
                "word": dev,
                "meaning": str(row.get('english', '')),
                "sanskrit": str(row.get('sanskrit', ''))
            })
            if len(matches) >= limit:
                return {"suggestions": matches}
    
    # Also check 'sanskrit' transliterated column (e.g., "agniḥ" -> "अग्निः")
    if len(matches) < limit:
        for _, row in df.iterrows():
            san = str(row.get('sanskrit', ''))
            # Convert IAST/roman to Devanagari for matching? For now, direct compare
            if san.startswith(prefix) and san not in seen:
                seen.add(san)
                matches.append({
                    "word": san,
                    "meaning": str(row.get('english', '')),
                    "sanskrit": san
                })
                if len(matches) >= limit:
                    return {"suggestions": matches}
    
    # If not enough matches and Groq API key exists, call AI for suggestions
    if len(matches) < limit and translator.api_key:
        try:
            import requests
            import json
            import re
            remaining = limit - len(matches)
            prompt = f"""
            You are a Sanskrit lexicon. Given the Devanagari prefix "{prefix}", suggest {remaining} common Sanskrit words (in Devanagari script) that start with this prefix.
            Return only a JSON array of objects with fields: "word" (Devanagari), "meaning" (English), "sanskrit" (transliterated IAST).
            Example: [{{"word": "नमस्ते", "meaning": "hello", "sanskrit": "namaste"}}]
            """
            headers = {"Authorization": f"Bearer {translator.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": translator.ai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(f"{translator.base_url}/chat/completions", headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ai_suggestions = json.loads(json_match.group(0))
                    for sugg in ai_suggestions[:remaining]:
                        word = sugg.get("word", "")
                        if word and word not in seen:
                            matches.append({
                                "word": word,
                                "meaning": sugg.get("meaning", ""),
                                "sanskrit": sugg.get("sanskrit", "")
                            })
                            if len(matches) >= limit:
                                break
        except Exception as e:
            print(f"Groq suggestion error: {e}")
    
    return {"suggestions": matches}

# ─── Snake & Ladder Translation Game ──────────────────────────
@app.get("/game/start")
def game_start():
    """Initialize a new Snake & Ladder game session."""
    return start_new_game()

@app.post("/game/turn")
def game_turn(req: GameTurnRequest):
    """Process one turn: validate the answer, move the player."""
    return process_turn(req.current_position, req.asked_word, req.user_answer)

# ─── Odd One Out Game ─────────────────────────────────────────
@app.get("/game/odd/question")
def odd_question():
    """Get a random Odd One Out question."""
    return get_random_question()

@app.post("/game/odd/answer")
def odd_answer(req: OddAnswerRequest):
    """Check the user's answer for Odd One Out."""
    return check_answer(req.question_data, req.user_choice)

# ─── BKT / Adaptive Learning Endpoints ──────────────────

class LessonAttemptRequest(BaseModel):
    lesson_id: int
    correct: bool

@app.post("/lesson/attempt")
def lesson_attempt(req: LessonAttemptRequest, user: Dict = Depends(get_current_user)):
    """
    Record a student's attempt on a lesson (skill).
    Updates BKT mastery and returns updated progress.
    """
    # Get lesson difficulty to set initial parameters
    lesson = next((l for l in learning_engine.lessons if l.get('id') == req.lesson_id), None)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    difficulty = lesson.get('difficulty', 3)
    result = db.record_bkt_attempt(user["username"], req.lesson_id, req.correct, difficulty)
    user_id = _ensure_learning_user(user["username"])
    learning_db.record_bkt_observation(user_id, req.lesson_id, req.correct, difficulty)
    learning_db.record_quiz_attempt(
        user_id=user_id,
        lesson_id=str(req.lesson_id),
        quiz_id="lesson_attempt",
        score_percent=100.0 if req.correct else 0.0,
        correct_answers=1 if req.correct else 0,
        total_questions=1,
    )
    learning_db.record_learning_day(user_id, source="lesson_attempt", score_percent=100.0 if req.correct else 0.0)
    if req.correct:
        completion = learning_db.complete_lesson(user_id, str(req.lesson_id), source="lesson_attempt")
        if completion["created"]:
            db.update_progress(user["username"], req.lesson_id, "completed")
    else:
        db.update_progress(user["username"], req.lesson_id, "started")
    
    # Also update traditional progress
    # The legacy JSON progress file remains updated for existing consumers.
    
    # Get next recommendation
    recommended = db.get_bkt_recommendation(user["username"], learning_engine.lessons)
    
    return {
        "skill_id": result["skill_id"],
        "mastery": result["mastery"],
        "attempts": result["attempts"],
        "correct": result["correct"],
        "recommended_lesson": recommended,
    }

@app.get("/recommendation")
def get_recommendation(user: Dict = Depends(get_current_user)):
    """Get the next recommended lesson based on BKT."""
    recommended = db.get_bkt_recommendation(user["username"], learning_engine.lessons)
    if not recommended:
        return {"recommendation": None, "message": "All lessons mastered or no lessons available."}
    return {"recommendation": recommended}

@app.get("/bkt/summary")
def get_bkt_summary(user: Dict = Depends(get_current_user)):
    """Get BKT progress summary for a user."""
    return db.get_bkt_summary(user["username"])

@app.get("/bkt/mastery")
def get_bkt_mastery(user: Dict = Depends(get_current_user)):
    """Get mastery for all lessons (or specific ones via query param)."""
    lessons = learning_engine.lessons
    skill_ids = [l.get('id') for l in lessons if l.get('id')]
    mastery_map = db.get_bkt_mastery_for_skills(user["username"], skill_ids)
    return {
        "mastery": {str(k): v for k, v in mastery_map.items()},
        "total_lessons": len(lessons),
    }


# ─── Test API Key Endpoint ────────────────────────────────────
@app.get("/test-api")
def test_api():
    """Test if API key is loaded correctly"""
    api_key = os.getenv("XAI_API_KEY")
    base_url = os.getenv("BASE_URL")
    return {
        "has_api_key": bool(api_key),
        "key_preview": api_key[:10] + "..." if api_key and len(api_key) > 10 else None,
        "provider": "Groq" if api_key and api_key.startswith("gsk_") else "Grok" if api_key else "None",
        "base_url": base_url,
        "ai_available": bool(api_key)
    }


# ─── Support Chat Endpoint ────────────────────────────────────────
class SupportChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = []


# Allowlist of approved support questions - frontend must only send these exact questions
SUPPORT_QUESTION_ALLOWLIST = [
    "How do I use the Sanskrit Grammar Checker?",
    "How do I translate English into Sanskrit?",
    "How do I use lessons and quizzes?",
    "How can I track my learning progress?",
    "How do I use Sanskrit pronunciation and audio?",
    "What should I do if a feature is not working?",
]


class SupportChatResponse(BaseModel):
    response: str
    error: Optional[str] = None


# System prompt for the Sanskrit AI Tutor support chatbot
SUPPORT_SYSTEM_PROMPT = """You are the official support assistant for Sanskrit AI Tutor, an adaptive Sanskrit learning application.

Your role is to help users with questions specifically about Sanskrit AI Tutor. You have knowledge of the following features that actually exist in the application:

**Features that EXIST in Sanskrit AI Tutor:**
1. **Translation** - English ↔ Sanskrit translation with dictionary lookup, local NLLB model, and optional AI-powered translation (Groq). Users can toggle "AI Engine" on/off.
2. **Grammar Checker** - Analyzes Sanskrit sentences for grammar errors using Paninian analysis (vibhakti, sandhi, verb conjugation, etc.). Has an "AI Scan" toggle for Groq-powered deep analysis.
3. **Lessons** - 25 structured lessons across beginner, intermediate, and advanced levels covering: greetings, numbers, self-intro, pronouns, verbs, nouns, family, question words, time/days, vibhakti (cases), sandhi, tenses, moods, extended pronouns, upasarga (prefixes), voice, indeclinables, participles, reading/composition, samasa (compounds), stri-pratyaya (feminine formation), chandas (prosody).
4. **Quizzes** - Each lesson has quizzes with adaptive BKT (Bayesian Knowledge Tracing) mastery tracking.
5. **Games** - Snake & Ladder translation game, Odd One Out vocabulary game.
6. **Grammar Checker** - Real-time Sanskrit sentence analysis with Paninian rule-based analysis and optional AI verification.
6. **Progress Tracking** - BKT-based mastery tracking, lesson completion, streak tracking, daily questions, quiz scores.
7. **Audio Pronunciation** - Text-to-speech for Sanskrit words/sentences.
8. **Translation** - English ↔ Sanskrit with dictionary, local NLLB model, and optional external AI (Groq/Grok, Google, MyMemory, LibreTranslate).

**Features that DO NOT EXIST (do not claim these exist):**
- Spaced repetition / SRS flashcards
- Speech recognition / voice input
- Community features / forums / leaderboards
- Teacher dashboard / classroom management
- Offline mode / mobile app
- Handwriting recognition
- Custom lesson creation
- Vocabulary spaced repetition

**Your behavior guidelines:**
- Answer ONLY about Sanskrit AI Tutor features listed above
- Be concise and step-by-step
- If unsure or the feature doesn't exist, say "That feature isn't currently available in Sanskrit AI Tutor" and suggest alternatives
- Never invent features, settings, or capabilities
- If you don't know, say "I don't have enough information about that. Please check the app or contact the developer."
- Never act as a general-purpose chatbot (no coding help, general knowledge, creative writing, etc.)
- Keep responses concise and helpful
- If the user asks about troubleshooting, give step-by-step guidance based on actual features
- Ground responses in actual app behavior, not assumptions

**Suggested questions you can help with:**
- How to use the Grammar Checker
- How translation works (AI Engine toggle, local model vs API)
- How lessons and quizzes work
- How progress tracking and BKT mastery work
- How to use the games
- Troubleshooting tips for features that actually exist"""


@app.post("/support/chat", response_model=SupportChatResponse)
async def support_chat(
    req: SupportChatRequest,
    user: Optional[Dict] = Depends(get_optional_user)
):
    """
    Support chat endpoint for Sanskrit AI Tutor.
    Uses the existing Groq integration from the translator.
    Validates submitted questions against an allowlist.
    """
    # Validate question against allowlist - reject arbitrary questions
    if req.message not in SUPPORT_QUESTION_ALLOWLIST:
        return SupportChatResponse(
            response="",
            error="Invalid question. Please use one of the predefined support questions."
        )
    
    try:
        # Get the translator instance (which has the Groq integration)
        translator = SanskritTranslator()
        
        if not translator.api_key:
            return SupportChatResponse(
                response="",
                error="AI support is not available. Please configure the XAI_API_KEY environment variable."
            )
        
        # Build the conversation history
        messages = [
            {"role": "system", "content": SUPPORT_SYSTEM_PROMPT}
        ]
        
        # Add conversation history (limit to last 10 messages to keep context manageable)
        for msg in req.history[-10:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": req.message})
        
        # Call Groq API
        headers = {
            "Authorization": f"Bearer {translator.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": translator.ai_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        
        response = requests.post(
            f"{translator.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        if response.status_code != 200:
            return SupportChatResponse(
                response="",
                error=f"AI service error: {response.status_code} - {response.text}"
            )
        
        result = response.json()
        ai_response = result["choices"][0]["message"]["content"]
        
        return SupportChatResponse(response=ai_response.strip())
        
    except requests.Timeout:
        return SupportChatResponse(
            response="",
            error="The AI service timed out. Please try again."
        )
    except Exception as e:
        return SupportChatResponse(
            response="",
            error=f"An error occurred: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Allow overriding the port via .env file, mapping it gracefully for user execution.
    port_str = os.getenv("PORT", "8005")
    port = int(port_str) if port_str.isdigit() else 8005
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except OSError as e:
        if "10048" in str(e) or "EADDRINUSE" in str(e):
            print(f"\n[PORT CONFLICT] The backend server is ALREADY RUNNING on port {port}.")
            print("You don't need to run 'python main.py' manually if it's already running in your other terminal.")
            print(f"To change the port, set PORT=8006 in your .env file.\n")
        else:
            raise
