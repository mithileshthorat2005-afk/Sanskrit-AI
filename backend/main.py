import sys
import os

# Ensure the backend/ directory is on sys.path so that `modules.*` imports
# work regardless of where uvicorn is invoked from.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Windows terminals can default to cp1252; reconfigure stdout for Unicode.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import json
from pydantic import BaseModel

# Import existing modules
from modules.database import MockDB
from modules.learning_engine import AdaptiveLearning
from modules.nlp_processor import SanskritNLP
from modules.auth import Authenticator
from modules.translator import SanskritTranslator
from modules.snake_ladder import start_new_game, process_turn
from modules.odd_one_out import get_random_question, check_answer
from modules.skill_mapper import SkillMapper          # NEW

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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
skill_mapper = SkillMapper()                          # NEW

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
    username: str = "demo"        # NEW — needed for BKT persistence

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
    success = auth.signup(req.username, req.password, req.role)
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    return {"message": "Account created successfully"}

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
    data = db.get_vibhakti()
    return {"success": True, "data": data}

@app.get("/api/lessons/sandhi")
def get_sandhi():
    data = db.get_sandhi()
    return {"success": True, "data": data}

@app.get("/api/lessons/tenses")
def get_tenses():
    data = db.get_tenses()
    return {"success": True, "data": data}

@app.get("/api/lessons/moods")
def get_moods():
    data = db.get_moods()
    return {"success": True, "data": data}

@app.get("/api/lessons/pronouns-extended")
def get_pronouns_extended():
    data = db.get_pronouns_extended()
    return {"success": True, "data": data}

@app.get("/api/lessons/upasarga")
def get_upasarga():
    data = db.get_upasarga()
    return {"success": True, "data": data}

@app.get("/api/lessons/voice")
def get_voice():
    data = db.get_voice()
    return {"success": True, "data": data}

@app.get("/api/lessons/indeclinables")
def get_indeclinables():
    data = db.get_indeclinables()
    return {"success": True, "data": data}

@app.get("/api/lessons/participles")
def get_participles():
    data = db.get_participles()
    return {"success": True, "data": data}

@app.get("/api/lessons/reading-composition")
def get_reading_composition():
    data = db.get_reading_composition()
    return {"success": True, "data": data}

@app.get("/api/lessons/samasa1")
def get_samasa1():
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

@app.get("/progress/{username}")
def get_progress(username: str):
    return db.get_user_progress(username)

@app.get("/activities/{username}")
def get_activities(username: str):
    return db.get_recent_activities(username)

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

# ─── Grammar Check — with Skill-Mapping + BKT pipeline ───────────────────────
@app.post("/grammar/check")
def check_grammar(req: GrammarRequest):
    """
    Grammar analysis with linguistically-grounded BKT pipeline:

    1. Run NLP analysis  → structured issues list (each has error_type)
    2. For each issue    → SkillMapper resolves error_type → skill_id
    3. Deduplicate       → one BKT observation per unique skill per submission
    4. BKT update        → db.record_bkt_attempt(username, skill_id, correct=False)
    5. One recommendation→ db.get_bkt_recommendation(username) after all updates
    6. Return analysis + bkt_updates + skipped_issues + recommendation
    """
    analysis = nlp.analyze_text(req.text, use_ai=req.use_ai)
    if "error" in analysis:
        return analysis

    issues = analysis.get("issues", [])
    bkt_updates   = []
    skipped_issues = []
    seen_skill_ids: set = set()

    for issue in issues:
        # Issues from updated nlp_processor are dicts; guard against plain strings
        if isinstance(issue, dict):
            raw_error_type = issue.get("error_type", "")
        else:
            raw_error_type = str(issue)

        skill_info = skill_mapper.map_error_to_skill(raw_error_type)

        # Not in mapping at all
        if skill_info is None:
            skipped_issues.append({
                "raw_error_type": raw_error_type,
                "reason": "error_type not found in skill_mapping.json — no BKT update",
            })
            continue

        # Intentionally unmapped (e.g. agreement_error, unknown_error)
        # Use .get() throughout — works with both new SkillMapper dict
        # and the raw JSON dict that older skill_mapper.py versions return.
        is_unmapped = skill_info.get("intentionally_unmapped", False)
        if is_unmapped:
            skipped_issues.append({
                "raw_error_type": raw_error_type,
                "normalized_error_type": skill_info.get("normalized_error_type", raw_error_type),
                "reason": "intentionally_unmapped — no BKT update",
            })
            continue

        skill_id = skill_info.get("skill_id")
        if skill_id is None:
            skipped_issues.append({
                "raw_error_type": raw_error_type,
                "reason": "skill_id is None — no BKT update",
            })
            continue

        # Deduplicate: one observation per skill per submission
        if skill_id in seen_skill_ids:
            continue
        seen_skill_ids.add(skill_id)

        # Grammar error → is_correct = False
        difficulty = skill_info.get("difficulty") or 3
        lesson = next(
            (l for l in learning_engine.lessons if l.get("id") == skill_id), None
        )
        actual_difficulty = lesson.get("difficulty", difficulty) if lesson else difficulty

        result = db.record_bkt_attempt(
            req.username, skill_id, is_correct=False, difficulty=actual_difficulty
        )
        bkt_updates.append({
            "error_type":  skill_info.get("normalized_error_type", raw_error_type),
            "skill_id":    skill_id,
            "skill_name":  skill_info.get("skill_name"),
            "mastery":     result["mastery"],
            "attempts":    result["attempts"],
        })

    # Single recommendation computed after all BKT updates
    recommendation = db.get_bkt_recommendation(req.username) if bkt_updates else None

    return {
        **analysis,
        "bkt_updates":    bkt_updates,
        "skipped_issues": skipped_issues,
        "recommendation": recommendation,
    }

@app.get("/dashboard/stats/{username}")
def get_dashboard_stats(username: str):
    progress   = db.get_user_progress(username)
    activities = db.get_recent_activities(username)
    stats      = translator.get_database_stats()
    return {
        "words_learned":      len(activities),
        "lessons_completed":  progress.get('completed', 0),
        "current_level":      progress.get('level', 'beginner'),
        "points":             progress.get('points', 0),
        "db_stats":           stats
    }

# ─── Suggestions Endpoint (Local DB + Groq Fallback) ──────────────────────────
@app.get("/suggestions")
def get_suggestions(prefix: str, limit: int = 6):
    if not prefix or len(prefix) < 1:
        return {"suggestions": []}

    matches = []
    seen = set()

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

    if len(matches) < limit:
        for _, row in df.iterrows():
            san = str(row.get('sanskrit', ''))
            if san.startswith(prefix) and san not in seen:
                seen.add(san)
                matches.append({
                    "word": san,
                    "meaning": str(row.get('english', '')),
                    "sanskrit": san
                })
                if len(matches) >= limit:
                    return {"suggestions": matches}

    if len(matches) < limit and translator.api_key:
        try:
            import requests
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
    return start_new_game()

@app.post("/game/turn")
def game_turn(req: GameTurnRequest):
    return process_turn(req.current_position, req.asked_word, req.user_answer)

# ─── Odd One Out Game ─────────────────────────────────────────
@app.get("/game/odd/question")
def odd_question():
    return get_random_question()

@app.post("/game/odd/answer")
def odd_answer(req: OddAnswerRequest):
    return check_answer(req.question_data, req.user_choice)

# ─── BKT / Adaptive Learning Endpoints ───────────────────────

class LessonAttemptRequest(BaseModel):
    lesson_id: int
    correct: bool
    username: str

@app.post("/lesson/attempt")
def lesson_attempt(req: LessonAttemptRequest):
    lesson = next((l for l in learning_engine.lessons if l.get('id') == req.lesson_id), None)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    difficulty = lesson.get('difficulty', 3)
    result = db.record_bkt_attempt(req.username, req.lesson_id, req.correct, difficulty)
    db.update_progress(req.username, req.lesson_id, 'completed' if req.correct else 'started')
    recommended = db.get_bkt_recommendation(req.username)

    return {
        "skill_id":          result["skill_id"],
        "mastery":           result["mastery"],
        "attempts":          result["attempts"],
        "correct":           result["correct"],
        "recommended_lesson": recommended,
    }

@app.get("/recommendation/{username}")
def get_recommendation(username: str):
    recommended = db.get_bkt_recommendation(username)
    if not recommended:
        return {"recommendation": None, "message": "All lessons mastered or no lessons available."}
    return {"recommendation": recommended}

@app.get("/bkt/summary/{username}")
def get_bkt_summary(username: str):
    return db.get_bkt_summary(username)

@app.get("/bkt/mastery/{username}")
def get_bkt_mastery(username: str):
    lessons = learning_engine.lessons
    skill_ids = [l.get('id') for l in lessons if l.get('id')]
    mastery_map = db.get_bkt_mastery_for_skills(username, skill_ids)
    return {
        "mastery": {str(k): v for k, v in mastery_map.items()},
        "total_lessons": len(lessons),
    }

# ─── Test API Key Endpoint ────────────────────────────────────
@app.get("/test-api")
def test_api():
    api_key  = os.getenv("XAI_API_KEY")
    base_url = os.getenv("BASE_URL")
    return {
        "has_api_key":  bool(api_key),
        "key_preview":  api_key[:10] + "..." if api_key and len(api_key) > 10 else None,
        "provider":     "Groq" if api_key and api_key.startswith("gsk_") else "Grok" if api_key else "None",
        "base_url":     base_url,
        "ai_available": bool(api_key)
    }

if __name__ == "__main__":
    import uvicorn

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