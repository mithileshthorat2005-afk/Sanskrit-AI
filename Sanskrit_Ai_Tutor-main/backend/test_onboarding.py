"""
Proficiency onboarding + BKT initialisation + skill-mapper flow tests.

Covers four scenarios against the real modules, sandboxed so no live user data
is touched:

  A. New user      — signup leaves onboarding outstanding, each of the three
                     proficiency choices seeds the exact documented values, and
                     the choice plus the seeded mastery survive a re-read.
  B. Existing user — a pre-existing account is never prompted, and its saved
                     mastery is unchanged afterwards.
  C. Skill mapper  — every recognised error type resolves to a lesson that
                     exists, unknown types update nothing, one submitted answer
                     moves only its own record, duplicates follow the existing
                     design, and seeded mastery survives the first BKT update.
  D. Auth/identity — the learner comes from the token, invalid values are
                     rejected, a failed save marks nothing complete, and a
                     repeat request never re-seeds.

Sandboxing: SQLITE_DB_PATH is pointed at a temp file BEFORE `main` is imported
so the app's own initialisation (including the legacy BKT snapshot migration)
cannot reach the real database. `main.db` and `main.auth` are then rebound to a
temp MockDB and a temp Authenticator for the same reason.

Run:   cd backend && python test_onboarding.py
Exit:  0 if all pass, 1 otherwise.

NOTE: no HTTP-level test is possible here — starlette's TestClient requires
`httpx`, which is not installed, and installing dependencies is out of scope.
Endpoints are exercised as the FastAPI route functions they are, with the
authenticated `user` resolved from a real signed token through the same
`get_current_user` dependency the server uses.
"""

import asyncio
import inspect
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict

# ── Sandbox FIRST, before main is imported ────────────────────────────────
SANDBOX = tempfile.mkdtemp(prefix="onboarding_test_")
os.environ["SQLITE_DB_PATH"] = os.path.join(SANDBOX, "sanskrit_ai.sqlite3")
with open(os.path.join(SANDBOX, "users.json"), "w", encoding="utf-8") as handle:
    json.dump({}, handle)

import main  # noqa: E402  (must come after the env override)
import modules.auth_dependency as auth_dependency  # noqa: E402
from modules.auth import Authenticator, VALID_ROLES  # noqa: E402
from modules.database import MockDB  # noqa: E402
from modules.sqlite_repository import SQLiteRepository  # noqa: E402
from modules.skill_mapper import (  # noqa: E402
    SkillMapper,
    RECOGNIZED_ERROR_TYPES,
    INTENTIONALLY_UNMAPPED,
)
from modules.bkt_engine import (  # noqa: E402
    BKTEngine,
    DEFAULT_PARAMS,
    INITIAL_MASTERY,
    CATALOG_LEVEL_TO_TIER,
    difficulty_band,
)
from fastapi import HTTPException  # noqa: E402
from fastapi.security import HTTPAuthorizationCredentials  # noqa: E402

# Rebind the module globals the endpoints read so every JSON/auth write below
# lands in the sandbox instead of the live data directory.
main.db = MockDB(data_dir=SANDBOX)
main.auth = Authenticator(users_file=os.path.join(SANDBOX, "users.json"))
auth_dependency.init_auth_dependencies(main.auth, main.learning_db)

learning_db: SQLiteRepository = main.learning_db
bkt_engine = BKTEngine.__new__(BKTEngine)
skill_mapper = SkillMapper()
LESSONS = main.learning_engine.lessons
LESSON_IDS = [lesson["id"] for lesson in LESSONS]
PASSWORD = "sanskritPass1!"

PASS = 0
FAIL = 0
FAILURES = []


def check(label, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        FAILURES.append(label)
        print(f"  FAIL  {label}")
        print(f"        expected: {expected!r}")
        print(f"        got:      {got!r}")


def check_true(label, condition, detail=""):
    """Assert `condition` is truthy; `detail` is what the failure should show."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        FAILURES.append(label)
        print(f"  FAIL  {label}")
        print(f"        expected: True")
        if detail:
            print(f"        detail:   {detail}")


def section(title):
    print(f"\n{'-' * 74}\n  {title}\n{'-' * 74}")


def as_user(token: str) -> Dict[str, Any]:
    """Resolve a real signed token the way the server does."""
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return asyncio.run(auth_dependency.get_current_user(None, credentials))


def signup_and_login(name: str) -> str:
    """Full new-account flow: POST /auth/signup then POST /auth/login."""
    main.signup(main.SignupRequest(username=name, password=PASSWORD, role="student"))
    return main.login(main.LoginRequest(username=name, password=PASSWORD))["access_token"]


def identity(name: str, level: str = "beginner") -> Dict[str, Any]:
    """A pre-existing account that has never gone through signup."""
    return {"username": name, "role": "student", "level": level, "completed": 0}


def mastery_rows(user_id: int) -> Dict[str, Dict[str, Any]]:
    return {
        key: {k: v for k, v in value.items() if k != "updated_at"}
        for key, value in learning_db.get_skill_mastery(user_id).items()
    }


def expected_tier_values(proficiency: str) -> Dict[str, float]:
    """The documented table, projected onto lessons via their declared level."""
    values = INITIAL_MASTERY[proficiency]
    plan = {}
    for lesson in LESSONS:
        tier = CATALOG_LEVEL_TO_TIER.get(lesson["level"]) or difficulty_band(
            lesson["difficulty"]
        )
        plan[str(lesson["id"])] = values[tier]
    return plan


def legacy_skills(name: str) -> Dict[str, Any]:
    with open(os.path.join(SANDBOX, "bkt_progress.json"), encoding="utf-8") as handle:
        return json.load(handle).get(name, {}).get("skills", {})


# ══════════════════════════════════════════════════════════════════════════
section("S0  Sandbox migration — onboarding columns exist and default safely")
# ══════════════════════════════════════════════════════════════════════════

with learning_db.connect() as connection:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
check_true("S0  users.proficiency column added", "proficiency" in columns, str(sorted(columns)))
check_true(
    "S0  users.onboarding_completed column added",
    "onboarding_completed" in columns,
    str(sorted(columns)),
)

# Running the migration again must be a no-op, not a crash.
learning_db.initialize()
with learning_db.connect() as connection:
    columns_again = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
check("S0  migration is idempotent (columns unchanged on rerun)", columns_again, columns)

# DEFAULT 1 means an account this code did not create is never prompted.
legacy_id = learning_db.ensure_user("zz_legacy_probe")
check(
    "S0  an account created outside signup defaults to onboarded",
    learning_db.get_onboarding_state(legacy_id),
    {"onboarding_completed": True, "proficiency": None},
)


# ══════════════════════════════════════════════════════════════════════════
section("S1  Scenario A — new user is prompted, then seeded exactly")
# ══════════════════════════════════════════════════════════════════════════

user_a = as_user(signup_and_login("zz_newbie"))
state = main.get_proficiency(user_a)
check("S1  a new signup is told onboarding is outstanding", state["onboarding_completed"], False)
check("S1  a new signup has no proficiency recorded yet", state["proficiency"], None)

for proficiency in ("beginner", "intermediate", "advanced"):
    name = f"zz_{proficiency}_user"
    account = as_user(signup_and_login(name))
    uid = learning_db.get_user_id(name)

    result = main.set_proficiency(main.ProficiencyRequest(proficiency=proficiency), account)
    check(f"S1  {proficiency}: request completed", result["completed"], True)
    check(f"S1  {proficiency}: every lesson seeded", result["skills_seeded"], len(LESSON_IDS))
    check(f"S1  {proficiency}: stored proficiency echoed", result["proficiency"], proficiency)

    rows = mastery_rows(uid)
    check(f"S1  {proficiency}: one row per lesson", len(rows), len(LESSON_IDS))
    check_true(
        f"S1  {proficiency}: no row invents attempts",
        all(row["attempts"] == 0 for row in rows.values()),
        str({k: v["attempts"] for k, v in rows.items()}),
    )

    expected = expected_tier_values(proficiency)
    mismatches = {
        key: (rows.get(key, {}).get("mastery"), expected[key])
        for key in expected
        if key not in rows or abs(rows[key]["mastery"] - expected[key]) > 1e-9
    }
    check(f"S1  {proficiency}: mastery matches the documented table", mismatches, {})

    distinct = sorted({round(row["mastery"], 2) for row in rows.values()})
    check(
        f"S1  {proficiency}: exactly the three documented tier values",
        distinct,
        sorted({round(v, 2) for v in INITIAL_MASTERY[proficiency].values()}),
    )

    # Persisted: a fresh read of the same account reports it onboarded.
    check(
        f"S1  {proficiency}: a re-read reports onboarding complete",
        main.get_proficiency(account)["onboarding_completed"],
        True,
    )
    check(
        f"S1  {proficiency}: a re-read reports the stored choice",
        main.get_proficiency(account)["proficiency"],
        proficiency,
    )
    # ... and the legacy JSON store carries the same numbers, because
    # /bkt/mastery reads it while /dashboard reads SQLite.
    legacy_mismatch = {
        key: (legacy_skills(name).get(key, {}).get("mastery"), expected[key])
        for key in expected
        if key not in legacy_skills(name)
        or abs(legacy_skills(name)[key]["mastery"] - expected[key]) > 1e-9
    }
    check(f"S1  {proficiency}: the legacy JSON store is seeded identically", legacy_mismatch, {})

check(
    "S1  the accepted internal values are beginner/intermediate/advanced",
    set(INITIAL_MASTERY),
    {"beginner", "intermediate", "advanced"},
)
check(
    "S1  'New to Sanskrit' is stored internally as 'beginner'",
    learning_db.get_onboarding_state(learning_db.get_user_id("zz_beginner_user"))["proficiency"],
    "beginner",
)
check(
    "S1  every projected value is a legal probability",
    all(0.0 <= value <= 1.0 for value in main._initial_mastery_plan("advanced").values()),
    True,
)


# ══════════════════════════════════════════════════════════════════════════
section("S2  Repeating the request is idempotent and never re-seeds")
# ══════════════════════════════════════════════════════════════════════════

repeat_user = as_user(signup_and_login("zz_repeater"))
repeat_id = learning_db.get_user_id("zz_repeater")

first = main.set_proficiency(main.ProficiencyRequest(proficiency="advanced"), repeat_user)
before = mastery_rows(repeat_id)
second = main.set_proficiency(main.ProficiencyRequest(proficiency="advanced"), repeat_user)
third = main.set_proficiency(main.ProficiencyRequest(proficiency="beginner"), repeat_user)
after = mastery_rows(repeat_id)

check("S2  the first call completes", first["completed"], True)
check("S2  a repeat call reports already_completed", second["completed"], False)
check("S2  a second repeat reports already_completed", third["completed"], False)
check("S2  a repeat call seeds nothing", second["seeded_skills"], [])
check("S2  a repeat reports the value that was requested", third["proficiency"], "beginner")
check(
    "S2  the stored choice is still the first one",
    learning_db.get_onboarding_state(repeat_id)["proficiency"],
    "advanced",
)
check("S2  mastery rows are identical after repeats", after, before)

# A repeat must also leave the legacy JSON store alone.
main.db.seed_bkt_mastery("zz_repeater", {"1": 0.99})
check(
    "S2  the legacy store refuses to overwrite a seeded skill",
    legacy_skills("zz_repeater")["1"]["mastery"],
    expected_tier_values("advanced")["1"],
)


# ══════════════════════════════════════════════════════════════════════════
section("S3  Scenario B — existing users are never prompted or reset")
# ══════════════════════════════════════════════════════════════════════════

existing_id = learning_db.ensure_user("zz_existing_user")
learning_db.record_bkt_observation(existing_id, 11, True, 6)
learning_db.record_bkt_observation(existing_id, 11, True, 6)
learning_db.record_bkt_observation(existing_id, 1, False, 3)
existing_before = mastery_rows(existing_id)
existing_legacy_before = legacy_skills("zz_existing_user")

existing = identity("zz_existing_user")
check(
    "S3  an existing user is told onboarding is already done",
    main.get_proficiency(existing)["onboarding_completed"],
    True,
)
attempted = main.set_proficiency(main.ProficiencyRequest(proficiency="advanced"), existing)
check("S3  an attempted re-onboard is refused", attempted["completed"], False)
check("S3  an attempted re-onboard seeds nothing", attempted["seeded_skills"], [])
check("S3  existing mastery is unchanged afterwards", mastery_rows(existing_id), existing_before)
check(
    "S3  the legacy JSON snapshot for that user is unchanged",
    legacy_skills("zz_existing_user"),
    existing_legacy_before,
)

# Accessing the account again (a repeat login, a refresh) changes nothing.
before_access = mastery_rows(existing_id)
main.get_proficiency(existing)
check("S3  re-reading the profile changes no mastery", mastery_rows(existing_id), before_access)

# A user with no mastery at all is also not prompted.
check(
    "S3  an existing user with no mastery is not prompted",
    main.get_proficiency(identity("zz_legacy_probe"))["onboarding_completed"],
    True,
)


# ══════════════════════════════════════════════════════════════════════════
section("S4  Scenario C — skill mapper resolves correctly and fails safely")
# ══════════════════════════════════════════════════════════════════════════

mapped = 0
for error_type in sorted(RECOGNIZED_ERROR_TYPES):
    skill = skill_mapper.map_error_to_skill(error_type)
    if skill is None:
        check_true(
            f"S4  {error_type} is deliberately unmapped (no BKT update)",
            error_type in INTENTIONALLY_UNMAPPED,
            str(skill),
        )
        continue
    mapped += 1
    check_true(
        f"S4  {error_type} resolves to a lesson that exists",
        skill["skill_id"] in LESSON_IDS,
        str(skill),
    )
    check(
        f"S4  {error_type} agrees with the lesson catalog's difficulty",
        skill["difficulty"],
        next(l for l in LESSONS if l["id"] == skill["skill_id"])["difficulty"],
    )
check("S4  the mapper covers 12 error types", mapped, 12)

check("S4  'Vibhakti Error' normalises", skill_mapper.normalize_error_type("Vibhakti Error"), "vibhakti_error")
check("S4  'SANDHI-ERROR' normalises", skill_mapper.normalize_error_type("SANDHI-ERROR"), "sandhi_error")
check("S4  'case selection error' normalises", skill_mapper.normalize_error_type("case selection error"), "vibhakti_error")
check("S4  junk normalises to unknown, not to a guess", skill_mapper.normalize_error_type("flurble"), "unknown_error")
check("S4  junk maps to no skill at all", skill_mapper.map_error_to_skill("flurble"), None)

# An unknown error type must not touch any mastery record.
probe_id = learning_db.ensure_user("zz_unknown_probe")
before_unknown = mastery_rows(probe_id)
targets = [
    skill
    for issue in [{"error_type": "flurble"}, {"error_type": "agreement_error"}]
    if (skill := skill_mapper.map_error_to_skill(issue["error_type"])) is not None
]
check("S4  unknown + unmapped types produce zero BKT targets", targets, [])
check("S4  no mastery row was created for them", mastery_rows(probe_id), before_unknown)

# The initialisation plan covers every lesson and nothing else.
plan = main._initial_mastery_plan("intermediate")
check("S4  the plan has one entry per lesson", len(plan), len(LESSON_IDS))
check("S4  the plan has no stray skill ids", set(plan), {str(i) for i in LESSON_IDS})
check(
    "S4  every plan value comes from the documented table",
    sorted({round(v, 2) for v in plan.values()}),
    sorted({round(v, 2) for v in INITIAL_MASTERY["intermediate"].values()}),
)

# Drift guard: the tiering used for onboarding is the one BKT already uses to
# pick its own starting l0 (BKT calls the <=4 tier "beginner", onboarding
# calls it "easy"; they must describe the same band).
l0_tier = {"easy": "beginner", "intermediate": "intermediate", "advanced": "advanced"}
drift = [
    d
    for d in range(1, 11)
    if bkt_engine.get_skill_params(1, d)["l0"]
    != DEFAULT_PARAMS["l0"][l0_tier[difficulty_band(d)]]
]
check("S4  difficulty tiers match BKT's own l0 banding for 1-10", drift, [])
check(
    "S4  catalog tier matches the difficulty band (lesson 24 is the one oddity)",
    [
        lesson["id"]
        for lesson in LESSONS
        if CATALOG_LEVEL_TO_TIER[lesson["level"]] != difficulty_band(lesson["difficulty"])
    ],
    [24],  # Strī Pratyaya: declared 'advanced' but difficulty 7 -> 'intermediate' band
)
check(
    "S4  the catalog's declared level covers every lesson",
    sorted({lesson["level"] for lesson in LESSONS}),
    ["advanced", "beginner", "intermediate"],
)

# A submitted answer must move exactly one record, and only that record.
# The quiz endpoint records ONE BKT observation per question (existing design),
# so a 10-question submission must produce exactly 10 graded attempts — no
# more, no fewer — and only for the submitted lesson.
quiz_account = as_user(signup_and_login("zz_quiz_user"))
quiz_user_id = learning_db.get_user_id("zz_quiz_user")
quiz_before = mastery_rows(quiz_user_id)
check("S4  the quiz user starts with no mastery rows", quiz_before, {})

lesson_12 = next(l for l in LESSONS if l["id"] == 12)
quiz_questions = lesson_12["quiz"]
# Answer every question correctly, exactly the way /progress/quiz grades it.
correct_answers = {
    str(q["id"]): (q["options"].index(q["answer"]) if q["answer"] in q["options"] else 0)
    for q in quiz_questions
}

main.submit_lesson_quiz(
    main.QuizSubmissionRequest(
        lesson_id="12",
        answers=dict(correct_answers),
        quiz_id="lesson_quiz",
    ),
    quiz_account,
)
quiz_after = mastery_rows(quiz_user_id)
check("S4  only the submitted lesson's record was created", set(quiz_after), {"12"})
check(
    "S4  one observation was recorded per submitted answer",
    quiz_after["12"]["attempts"],
    len(quiz_questions),
)
check(
    "S4  every correct answer was counted",
    quiz_after["12"]["correct"],
    len(correct_answers),
)

# A second submission of the same quiz is a further set of observations (the
# existing design) but must not duplicate the XP award.
xp_before = learning_db.get_xp_balance(quiz_user_id)
main.submit_lesson_quiz(
    main.QuizSubmissionRequest(
        lesson_id="12",
        answers=dict(correct_answers),
        quiz_id="lesson_quiz",
    ),
    quiz_account,
)
check(
    "S4  a repeat submission adds one observation per answer (existing design)",
    mastery_rows(quiz_user_id)["12"]["attempts"],
    len(quiz_questions) * 2,
)
check("S4  a repeat submission awards no extra XP", learning_db.get_xp_balance(quiz_user_id), xp_before)


# ══════════════════════════════════════════════════════════════════════════
section("S5  Seeded mastery survives the first real BKT update")
# ══════════════════════════════════════════════════════════════════════════

seed_account = as_user(signup_and_login("zz_seed_survival"))
seed_id = learning_db.get_user_id("zz_seed_survival")
seeded = learning_db.complete_onboarding(seed_id, "beginner", {"1": 0.20, "11": 0.05, "21": 0.01})
check("S5  seeding wrote three rows", sorted(seeded["seeded_skills"]), ["1", "11", "21"])

updated = learning_db.record_bkt_observation(seed_id, 1, True, 3)
params = bkt_engine.get_skill_params(1, 3)
expected_from_seed = bkt_engine.update_mastery(0.20, True, params)
expected_from_l0 = bkt_engine.update_mastery(DEFAULT_PARAMS["l0"]["beginner"], True, params)
check_true(
    "S5  the first update builds on the seeded 0.20, not on l0",
    abs(updated["mastery"] - expected_from_seed) < 1e-12,
    f"got={updated['mastery']} seeded-path={expected_from_seed} l0-path={expected_from_l0}",
)
check("S5  the untouched seed is still 0.05", mastery_rows(seed_id)["11"]["mastery"], 0.05)
check("S5  the advanced-tier seed is still 0.01", mastery_rows(seed_id)["21"]["mastery"], 0.01)
check("S5  attempts now counts the graded answer", mastery_rows(seed_id)["1"]["attempts"], 1)
check("S5  the response reports the same mastery", updated["mastery"], mastery_rows(seed_id)["1"]["mastery"])

# Same guarantee in the legacy JSON store.
main.db.seed_bkt_mastery("zz_json_seed", {"1": 0.20})
json_engine = main.db.get_bkt_engine()
json_result = json_engine.record_attempt("zz_json_seed", 1, True, 3)
json_expected = json_engine.update_mastery(0.20, True, json_engine.get_skill_params(1, 3))
check_true(
    "S5  the legacy JSON store also builds on the seeded value",
    abs(json_result["mastery"] - json_expected) < 1e-12,
    f"got={json_result['mastery']} expected={json_expected}",
)
check("S5  re-seeding the JSON store is a no-op", main.db.seed_bkt_mastery("zz_json_seed", {"1": 0.99}), 0)
check(
    "S5  the JSON store kept the real value",
    json_engine.get_user_skill_data("zz_json_seed", 1)["mastery"],
    json_result["mastery"],
)


# ══════════════════════════════════════════════════════════════════════════
section("S6  Scenario D — identity, validation and failure handling")
# ══════════════════════════════════════════════════════════════════════════

# The learner is taken from the token: neither endpoint accepts an account to
# act on, so one user cannot address another's mastery.
check(
    "S6  POST /proficiency takes no user identifier",
    [p for p in inspect.signature(main.set_proficiency).parameters if p not in ("req", "user")],
    [],
)
check(
    "S6  GET /proficiency takes no user identifier",
    [p for p in inspect.signature(main.get_proficiency).parameters if p != "user"],
    [],
)
request_fields = getattr(main.ProficiencyRequest, "model_fields", None) or main.ProficiencyRequest.__fields__
check("S6  the POST body holds only the proficiency choice", list(request_fields), ["proficiency"])

victim_id = learning_db.ensure_user("zz_victim")
learning_db.record_bkt_observation(victim_id, 5, True, 3)
victim_before = mastery_rows(victim_id)
victim_state_before = learning_db.get_onboarding_state(victim_id)

attacker = as_user(signup_and_login("zz_attacker"))
main.set_proficiency(main.ProficiencyRequest(proficiency="advanced"), attacker)
check("S6  another user's mastery was not modified", mastery_rows(victim_id), victim_before)
check(
    "S6  another user's onboarding state was not modified",
    learning_db.get_onboarding_state(victim_id),
    victim_state_before,
)

for bad in ("Expert", "", "   ", "beginner2", "9", "null", "true"):
    try:
        main.set_proficiency(main.ProficiencyRequest(proficiency=bad), attacker)
        check(f"S6  invalid proficiency {bad!r} is rejected", "no exception", "HTTPException 400")
    except HTTPException as exc:
        check(f"S6  invalid proficiency {bad!r} is rejected", exc.status_code, 400)

try:
    learning_db.complete_onboarding(victim_id, "wizard", {"1": 0.5})
    check("S6  the repository rejects an unknown value too", "no exception", "ValueError")
except ValueError:
    check("S6  the repository rejects an unknown value too", True, True)

# Case and surrounding whitespace normalise rather than creating a new value.
norm_account = as_user(signup_and_login("zz_normaliser"))
norm_id = learning_db.get_user_id("zz_normaliser")
main.set_proficiency(main.ProficiencyRequest(proficiency="  InterMediate "), norm_account)
check(
    "S6  case and whitespace are normalised",
    learning_db.get_onboarding_state(norm_id)["proficiency"],
    "intermediate",
)

# A failed save must not mark onboarding complete, and must not seed twice.
fail_account = as_user(signup_and_login("zz_failure"))
fail_id = learning_db.get_user_id("zz_failure")
real_complete = learning_db.complete_onboarding


def explode(*args, **kwargs):
    raise OSError("disk full")


learning_db.complete_onboarding = explode
try:
    main.set_proficiency(main.ProficiencyRequest(proficiency="advanced"), fail_account)
    check("S6  a storage failure surfaces as an error", "no exception", "an exception")
except (HTTPException, OSError):
    check("S6  a storage failure surfaces as an error", True, True)
finally:
    learning_db.complete_onboarding = real_complete

check(
    "S6  a failed save leaves onboarding outstanding",
    learning_db.get_onboarding_state(fail_id)["onboarding_completed"],
    False,
)
check("S6  a failed save seeded no SQLite mastery", mastery_rows(fail_id), {})

recovered = main.set_proficiency(main.ProficiencyRequest(proficiency="advanced"), fail_account)
check("S6  the retry completes onboarding", recovered["completed"], True)
check("S6  the retry seeds every lesson exactly once", recovered["skills_seeded"], len(LESSON_IDS))
recovered_rows = mastery_rows(fail_id)
advanced_easy = {
    str(lesson["id"]) for lesson in LESSONS if lesson["level"] == "beginner"
}
check(
    "S6  the retry's easy-tier values are the documented 0.80",
    {key for key, row in recovered_rows.items() if abs(row["mastery"] - 0.80) < 1e-9},
    advanced_easy,
)
check_true(
    "S6  every seeded mastery is within [0.0, 1.0]",
    all(
        0.0 <= row["mastery"] <= 1.0
        for uid in (fail_id, norm_id, repeat_id, seed_id)
        for row in mastery_rows(uid).values()
    ),
    "out-of-range value found",
)

try:
    as_user("not.a.real.token")
    check("S6  a forged token is rejected", "no exception", "401")
except Exception as exc:  # FastAPI raises HTTPException here
    # HTTPException keeps its message in `.detail`, not in str(exc).
    text = f"{getattr(exc, 'detail', '')} {exc}".lower()
    check_true(
        "S6  a forged token is rejected",
        "invalid" in text or "expired" in text or "not authenticated" in text,
        f"raised: {text!r}",
    )


# ══════════════════════════════════════════════════════════════════════════
section("S7  Login page — role picker removed, default role preserved")
# ══════════════════════════════════════════════════════════════════════════

page_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend", "src", "app", "page.tsx",
)
with open(page_path, encoding="utf-8") as handle:
    page = handle.read()
check_true("S7  the Student/Educator <select> is gone", "<select" not in page, "select still present")
check_true("S7  the 'Educator' option is gone", "Learning Path: Educator" not in page)
check("S7  signup still sends the existing default role", page.count('SIGNUP_ROLE = "student"'), 1)
check_true(
    "S7  the auth context still receives a role argument",
    "signup(username, password, SIGNUP_ROLE)" in page,
    "signup call changed",
)
check("S7  the backend role allowlist is unchanged", set(VALID_ROLES), {"student", "teacher", "admin"})
check("S7  a new account is created as a student", main.auth.users["zz_newbie"]["role"], "student")

layout_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend", "src", "app", "layout.tsx",
)
with open(layout_path, encoding="utf-8") as handle:
    layout = handle.read()
check_true("S7  the onboarding dialog is mounted inside AuthProvider", "<ProficiencyOnboarding />" in layout)


# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 74}")
print(f"  PASSED: {PASS}   FAILED: {FAIL}")
if FAILURES:
    print("  Failures:")
    for item in FAILURES:
        print(f"    - {item}")
print("=" * 74)

shutil.rmtree(SANDBOX, ignore_errors=True)
sys.exit(1 if FAIL else 0)
