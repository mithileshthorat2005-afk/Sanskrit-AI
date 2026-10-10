# SanskritAI Data Flow Reference

This document describes the current runtime data flow. File names are included at every ownership boundary so a function can be traced from the browser to storage.

## 1. Runtime topology

```text
Browser page/component
  -> frontend/src/lib/api.ts: apiRequest()
  -> HTTP request to backend/main.py
  -> backend/main.py route handler
  -> backend/modules/*.py service function
  -> backend/data/*.json or backend/data/sanskrit_ai.sqlite3
  -> JSON response
  -> React state
  -> rendered page
```

Frontend default API URL: `http://localhost:8005`, from `frontend/src/lib/api.ts:API_BASE_URL`.

Backend default origin: `http://localhost:3000`, from `backend/main.py:frontend_origin`.

The main persistent database is `backend/data/sanskrit_ai.sqlite3`. SQLite schema and writes are owned by `backend/modules/sqlite_repository.py:SCHEMA` and `SQLiteRepository`.

## 2. Application startup

### `backend/main.py`

- `FastAPI(...)`: creates the API application.
- `CORSMiddleware`: permits the configured frontend origin to call the API.
- `MockDB(data_dir=...)` from `backend/modules/database.py`: loads lesson and content files.
- `AdaptiveLearning(lessons_file=...)` from `backend/modules/learning_engine.py`: loads the legacy lesson source. The configured `backend/data/lessons.json` is currently missing, so this object uses default lessons.
- `SanskritNLP()` from `backend/modules/nlp_processor.py`: loads NLP data and optional AI configuration.
- `Authenticator(users_file=...)` from `backend/modules/auth.py`: loads `backend/data/users.json`.
- `SQLiteRepository(database_path=...)` from `backend/modules/sqlite_repository.py`: uses `SQLITE_DB_PATH` when set, otherwise `backend/data/sanskrit_ai.sqlite3`.
- `learning_db.initialize()`: creates SQLite tables and indexes.
- `learning_db.migrate_users(auth.users)`: copies users from `backend/data/users.json` into SQLite without overwriting existing SQLite rows.
- `SanskritTranslator(...)` from `backend/modules/translator.py`: loads `backend/data/sanskrit_words.csv` and `backend/data/sanskrit_sentences.json`.
- `if __name__ == '__main__'`: starts Uvicorn on port 8005 by default (overridable with `PORT`).

Startup therefore reads JSON/CSV content, initializes SQLite, migrates authentication users, and builds in-memory service objects before the first request.

## 3. Authentication flow

### Browser login: `frontend/src/app/page.tsx`

- `Home()`: owns login/register form state.
- `useEffect(...)`: reads `localStorage.user`; an existing user is redirected to `/dashboard`.
- `handleSubmit(event)`: calls `frontend/src/lib/api.ts:api.auth.login()` for login or `api.auth.signup()` for registration.
- Successful login stores `access_token` and a reduced `user` object in browser local storage, then routes to `/dashboard`.
- Registration calls the backend, switches the form to login, and displays the success message.

### API wrapper: `frontend/src/lib/api.ts`

- `apiRequest(endpoint, options)`: builds the URL, reads `localStorage.access_token`, adds `Authorization: Bearer <token>`, sends JSON, parses the response, and throws for non-2xx responses.
- On HTTP 401, `apiRequest()` removes both local-storage session values and redirects to `/`.
- `api.auth.login(credentials)`: POST `/auth/login`; returns the token and user data.
- `api.auth.signup(data)`: POST `/auth/signup`; creates a user.
- `api.auth.logout()`: POST `/auth/logout`; revokes the token server-side.

### Server authentication: `backend/main.py` and `backend/modules/auth.py`

- `login(req)` in `backend/main.py`: calls `Authenticator.login()`, then `Authenticator.create_access_token()`, and returns user data plus token.
- `Authenticator.load_users()`: reads `backend/data/users.json`; malformed or missing data becomes an empty/default user map.
- `Authenticator.create_default_users()`: returns an empty user map.
- `Authenticator.save_users(users)`: writes the authentication user map back to `backend/data/users.json`.
- `Authenticator.hash_password(password)`: hashes passwords with bcrypt.
- `Authenticator.verify_password(stored_password, provided_password)`: checks bcrypt hashes and rejects invalid records.
- `Authenticator.login(username, password)`: validates credentials; legacy `hashed_` values are upgraded and saved to JSON.
- `Authenticator.create_access_token(username)`: creates a signed, one-day token using `AUTH_TOKEN_SECRET`, or a process-local development secret.
- `Authenticator.verify_access_token(token)`: validates signature, expiry, revocation, and user existence.
- `Authenticator.revoke_access_token(token)`: adds the token digest to the process-local revoked-token set.
- `Authenticator.token_is_revoked(token)`: checks that in-memory revoked-token set.
- `Authenticator._token_secret()`: reads `AUTH_TOKEN_SECRET`; production requires it.
- `Authenticator.signup(username, password, role)`: hashes and saves a new student user to `backend/data/users.json`.
- `signup(req)` in `backend/main.py`: calls `auth.signup()` and then `learning_db.migrate_users()`.
- `_authenticated_username(request)` in `backend/main.py`: extracts and verifies the Bearer token; missing or invalid tokens produce HTTP 401.
- `_resolve_user(username, request)` in `backend/main.py`: confirms the username exists, confirms the token identity matches, and converts the username to the SQLite user ID.
- `logout(request)` in `backend/main.py`: revokes the submitted Bearer token.

Important: auth JSON is the source loaded at startup, while progress operations use the SQLite user ID.

## 4. Content and lesson flow

### Content source: `backend/modules/database.py`

- `MockDB.__init__(data_dir)`: stores the data directory and loads lessons/vocabulary.
- `MockDB.load_lessons()`: reads lesson JSON files from `backend/data`; returns a fallback structure when unavailable.
- `MockDB.load_vocabulary()`: reads vocabulary CSV/JSON data.
- `MockDB.load_all_lessons()`: returns the normalized lesson catalog used by API routes.
- `MockDB.get_greetings()`: reads greetings content, principally `backend/data/sanskritGreetings.json`.
- `MockDB.get_numbers()`: reads number content from `backend/data/sanskritNumbers.json`.
- `MockDB.get_self_intro()`: reads self-introduction content from `backend/data/sanskritSelfIntro.json`.
- `MockDB.get_pronouns()`: reads `backend/data/sanskritPronouns.json`.
- `MockDB.get_verbs()`: reads `backend/data/sanskritVerbs.json`.
- `MockDB.get_nouns()`: reads `backend/data/sanskritNouns.json`.
- `MockDB.get_family()`: reads `backend/data/sanskritFamily.json`.
- `MockDB.get_question_words()`: reads `backend/data/sanskritQuestionWords.json`.
- `MockDB.get_time_and_days()`: reads `backend/data/sanskritTimeAndDays.json`.
- `MockDB.get_daily_questions()`: reads `backend/data/dailyQuestions.json`.
- `MockDB.get_snake_ladder_words()`: reads `backend/data/snakeLadderWords.json`.
- `MockDB.get_odd_one_out_words()`: reads `backend/data/oddOneOutWords.json`.
- `MockDB.get_user_progress(username)`: reads legacy user progress data.
- `MockDB.get_recent_activities(username)`: derives legacy activity data from user progress.

### Lesson service: `backend/modules/learning_engine.py`

- `AdaptiveLearning.__init__(lessons_file)`: stores the lesson file and calls `load_lessons()`.
- `AdaptiveLearning.load_lessons()`: reads the configured lesson JSON; if absent, calls `get_default_lessons()`.
- `AdaptiveLearning.get_default_lessons()`: returns built-in lesson definitions.
- `AdaptiveLearning.get_recommendation(user)`: filters lessons by user level and prerequisites.
- `AdaptiveLearning.calculate_proficiency(user_performance)`: converts performance values into a proficiency score.
- `AdaptiveLearning.update_learning_path(user_id, lesson_id, score)`: updates the legacy learning-path representation.

### Lesson routes: `backend/main.py`

- `get_lessons(level)`: calls `db.load_all_lessons()`, optionally filters by level, and returns `{success,data,count}`.
- `get_lesson(lesson_id)`: searches `learning_engine.lessons` and returns one lesson or HTTP 404.
- `get_greetings_lesson()`, `get_numbers_lesson()`, `get_self_intro_lesson()`, `get_pronouns()`, `get_verbs()`, `get_nouns()`, `get_family()`, `get_question_words()`, `get_time_and_days()`: delegate directly to the matching `MockDB` content function.
- `get_daily_questions()`: opens `backend/data/dailyQuestions.json` and returns parsed JSON.
- `get_all_lessons()`: returns `db.load_all_lessons()` for `/api/lessons/all`.
- `get_lesson_by_id(lesson_id)`: searches the catalog returned by `db.load_all_lessons()`.

### Lesson browser: `frontend/src/app/lessons/page.tsx`

- `normalizeProgress(raw)`: converts API progress variants into `{completed_lessons, concept_mastery}`.
- `isLessonAvailable(lesson, completed)`: checks all prerequisite IDs.
- `getMissingPrerequisites(lesson, completed)`: returns unmet prerequisite IDs.
- `getLevelColor(level)`: maps a lesson level to presentation classes.
- `LessonsPage()`: reads the stored user and owns lesson-list state.
- Internal `fetchData()`: concurrently calls `api.lessons.getAll()` and `api.bkt.getProgress()`; results populate lesson and progress state.
- `groupedLessons`: derives module groups from the lesson catalog.
- `nextLesson`: derives the first incomplete lesson whose prerequisites are satisfied.
- Clicking a lesson routes to `/lessons/<id>`.

### Lesson detail: `frontend/src/app/lessons/[id]/page.tsx`

- `normalizeProgress(raw)`: normalizes the backend progress response.
- `isLessonAvailable(lesson, completed)`: checks prerequisite completion.
- `LessonDetailPage()`: owns selected lesson, quiz, completion, and progress state.
- Internal `fetchData()`: concurrently calls `api.lessons.getAll()`, `api.lessons.getById()`, and `api.bkt.getProgress()`.
- `handleAnswer(questionId, optionIndex)`: writes one answer into React state.
- `goToQuestion(index)`: clamps quiz navigation to valid question indexes.
- `submitQuiz()`: calls `api.bkt.submitQuiz()` and marks the quiz submitted.
- `markComplete()`: calls `api.bkt.markLessonComplete()`, updates local progress, and routes to the next available lesson.

## 5. SQLite persistence and dashboard flow

### Database owner: `backend/modules/sqlite_repository.py`

- `SQLiteRepository.__init__(database_path)`: stores the database filename.
- `SQLiteRepository.connect()`: creates a SQLite connection, enables foreign keys, commits successful work, rolls back errors, and closes the connection.
- `SQLiteRepository.initialize()`: executes `SCHEMA`, creating `users`, `lesson_completions`, `quiz_attempts`, `grammar_attempts`, `daily_activity`, and `xp_transactions`.
- `SQLiteRepository.migrate_users(users)`: inserts missing users from `backend/data/users.json`; it is idempotent.
- `SQLiteRepository.get_user_id(username)`: maps an auth username to `users.id`.
- `_normalize_utc_date(value, field_name)`: validates and normalizes dates to UTC ISO dates.
- `record_learning_day(...)`: inserts one daily activity row per user/date; duplicate days are ignored.
- `get_active_dates(user_id)`: reads distinct active dates from `daily_activity`.
- `get_streak_summary(user_id, as_of_utc_date)`: calculates current streak, longest streak, and active-day count.
- `complete_lesson(user_id, lesson_id, source)`: inserts a unique row into `lesson_completions`.
- `get_completed_lesson_ids(user_id)`: reads completed lesson IDs.
- `get_next_lesson_recommendation(user_id, lessons)`: combines completed SQLite lesson IDs with lesson metadata and returns the next available lesson.
- Nested `lesson_order_key(lesson)`: provides curriculum ordering for recommendations.
- `get_dashboard_summary(user_id, lessons)`: aggregates completion count, quiz count/average, grammar count, streak values, recommendation, and recent activity.
- `record_quiz_attempt(...)`: inserts a quiz attempt into `quiz_attempts` and returns the attempt result.
- `record_grammar_activity(...)`: serializes analysis JSON and inserts it into `grammar_attempts`.
- `list_grammar_activities(user_id, limit)`: reads recent grammar rows.
- `list_users()`: reads SQLite users for administrative use.

### Progress routes: `backend/main.py`

- `get_progress(username, request)`: resolves the authenticated SQLite user ID and returns completed lesson IDs.
- `get_activities(username, request)`: resolves the user and returns `get_dashboard_summary(...)["recent_activity"]`.
- `get_dashboard_stats(username, request)`: returns the SQLite summary statistics.
- `get_dashboard(username, request)`: returns the complete dashboard summary.
- `get_streak_summary(username, request)`: returns SQLite streak data.
- `get_recommendation(username, request)`: returns the next lesson recommendation.
- `mark_lesson_complete(username, payload, request)`: validates the lesson, calls `complete_lesson()`, and records a daily activity row when a new completion is created.
- `submit_quiz(username, req, request)`: validates answers, calculates score, calls `record_quiz_attempt()`, and records a learning day.

### Dashboard UI: `frontend/src/app/dashboard/page.tsx`

- `Dashboard()`: checks the browser session and owns dashboard state.
- Internal `fetchData()`: calls `api.user.getDashboard(username)`.
- The rendered statistics, recent activity, and recommendation all come from the returned `DashboardResponse`; no dashboard values are hard-coded.

### Insights UI: `frontend/src/app/progress/page.tsx`

- `Progress()`: checks both `localStorage.user` and `localStorage.access_token`.
- Internal `fetchProgress()`: calls `api.user.getDashboard(username)`, matching Dashboard.
- `completionPercent`: derives completed lessons / total lessons.
- The page derives curriculum, quiz, grammar, streak, and recommendation displays from the dashboard response. Reading, writing, speaking, and prosody visual values are presentation-derived because SQLite currently stores no separate skill-mastery table.

## 6. Grammar flow

### Backend: `backend/main.py` and `backend/modules/nlp_processor.py`

- `check_grammar(req, request)`: authenticates the user, calls `SanskritNLP.analyze_text()`, and persists successful analysis through `record_grammar_activity()` plus `record_learning_day()`.
- `SanskritNLP.__init__()`: loads vocabulary/rules and detects optional AI configuration.
- `SanskritNLP.tokenize(text)`: converts text into tokens.
- `SanskritNLP.analyze_text(text, mode, use_ai)`: chooses local analysis or `analyze_with_grok()`.
- `SanskritNLP.analyze_with_grok(text)`: calls the external AI provider and falls back to local behavior on failure.
- `SanskritNLP.mock_translate(text)`: produces a local fallback translation.
- `SanskritNLP.translate_sanskrit_to_english(text)`: calls an external translation service and uses the mock fallback if unavailable.
- `SanskritNLP.check_grammar(text)`: returns local grammar issues.
- `SanskritNLP.get_word_details(word)`: looks up vocabulary details.

### Frontend: `frontend/src/app/grammar/page.tsx`

- `Grammar()`: owns input and analysis state.
- `handleCheck()`: calls `api.tools.checkGrammar(username, text, use_ai)` and renders the response.
- `frontend/src/components/SanskritInput.tsx`: captures Sanskrit text and delegates transliteration behavior when configured.

## 7. Translation and suggestions flow

### Backend: `backend/modules/translator.py`

- `SanskritTranslator.__init__(csv_path, sentences_path)`: loads dictionary, sentence data, and generated patterns.
- `load_main_db()`: reads the main CSV dictionary into a DataFrame.
- `load_data()`: loads/merges dictionary data.
- `load_sentences()`: reads sentence JSON.
- `generate_default_sentences()`: creates fallback sentence examples.
- `generate_patterns()`: creates sentence-generation patterns.
- `create_demo_data()`: creates fallback dictionary rows.
- `save_sentences(sentences_data)`: writes sentence data to JSON.
- `translate_with_deep_translator()`, `translate_with_mymemory()`, `translate_with_libretranslate()`: call external providers and return a result or `None`.
- `translate_with_ai(text, direction)`: calls the configured AI provider.
- `save_to_database(word_data)`: appends newly learned word data to the CSV and generates sentences.
- `generate_sentences_for_word(word_data)`: creates examples for a word.
- `English_to_sanskrit(English_word, use_api)`: searches local dictionary, optionally calls external/AI translation, and persists new data.
- `sanskrit_to_English(sanskrit_word, use_api)`: reverse-direction equivalent.
- `get_meaning(word)`: reads a meaning from local data.
- `auto_generate_sentences(count)`: generates multiple sentences.
- `get_random_sentence()`: returns one sentence.
- `get_database_stats()`: returns dictionary counts.

### Backend routes and frontend

- `translate_text(req)` in `backend/main.py`: delegates to `English_to_sanskrit()` or `sanskrit_to_English()`.
- `get_suggestions(prefix, limit)` in `backend/main.py`: searches translator data and may call Groq for additional suggestions.
- `Translation()` in `frontend/src/app/translation/page.tsx`: owns text, direction, result, and loading state.
- `handleTranslate()`: calls `api.tools.translate()`.
- `swapDirection()`: switches direction and clears incompatible text/result state.
- `useSanskritTransliteration(inputValue, onChange, enabled)` in `frontend/src/hooks/useSanskritTransliteration.ts`: keeps local input synchronized and converts ITRANS/IAST input.
- Internal `handleChange(newValue)`: applies fixed mappings, then Sanscript ITRANS/IAST conversion, and calls the supplied change handler.
- `WordSuggestions` in `frontend/src/components/WordSuggestions.tsx`: requests/display suggestions for translation input.

## 8. Games flow

### `backend/modules/snake_ladder.py`

- `pick_random_word(exclude_sanskrit)`: selects a vocabulary challenge.
- `process_turn(current_position, asked_word, user_answer)`: checks the answer, applies snake/ladder movement, and returns the next challenge/state.
- `start_new_game()`: creates an initial game position and word.

### `backend/modules/odd_one_out.py`

- `get_random_question(exclude_category)`: selects a question from odd-one-out data.
- `check_answer(question_data, user_choice)`: evaluates the one-based choice and returns correctness plus the next question.

### `backend/main.py` and frontend

- `game_start()`: calls `start_new_game()`.
- `game_turn(req)`: calls `process_turn()`.
- `odd_question()`: calls `get_random_question()`.
- `odd_answer(req)`: calls `check_answer()`.
- `GameMenu()` in `frontend/src/app/game/menu/page.tsx`: checks auth, stores `preferredGame`, and routes to `/game`.
- `Game()` in `frontend/src/app/game/page.tsx`: owns game state and calls the game API wrappers in `frontend/src/lib/api.ts`.

## 9. Shared UI and utility functions

- `RootLayout({children})` in `frontend/src/app/layout.tsx`: wraps every page with metadata, global CSS, fonts, and the document body.
- `cn(...inputs)` in `frontend/src/lib/utils.ts`: merges class names using `clsx` and `tailwind-merge`.
- `Sidebar({user})` in `frontend/src/components/Sidebar.tsx`: renders navigation, theme state, and logout. Logout removes local storage values and calls the API logout wrapper.
- `DailyStreak` in `frontend/src/components/DailyStreak.tsx`: loads and displays streak/challenge information.
- `DashboardHeader`, `DashboardPanels`, and lesson components in `frontend/src/components/dashboard/` and `frontend/src/components/lessons/`: receive page/API data through props and render lesson/dashboard subviews; they do not own the SQLite connection.

## 10. Data ownership summary

| Data | Current source of truth | Read/write owner |
|---|---|---|
| Login users | `backend/data/users.json`, migrated into SQLite users | `backend/modules/auth.py`, `backend/modules/sqlite_repository.py` |
| Passwords | `backend/data/users.json` and SQLite `users.password_hash` after migration | `backend/modules/auth.py` |
| Completed lessons | SQLite `lesson_completions` | `backend/modules/sqlite_repository.py` |
| Quiz attempts | SQLite `quiz_attempts` | `backend/modules/sqlite_repository.py` |
| Grammar activity | SQLite `grammar_attempts` | `backend/modules/sqlite_repository.py` |
| Daily streak/activity | SQLite `daily_activity` | `backend/modules/sqlite_repository.py` |
| XP transactions | SQLite `xp_transactions` schema exists; current route usage should be checked before relying on it | `backend/modules/sqlite_repository.py` |
| Lesson catalog | JSON files under `backend/data/lessons/` and `MockDB` normalization | `backend/modules/database.py` |
| Vocabulary | `backend/data/sanskrit_words.csv` and related files | `backend/modules/database.py`, `backend/modules/translator.py` |
| Generated sentences | `backend/data/sanskrit_sentences.json` | `backend/modules/translator.py` |
| Browser session | `localStorage.user` and `localStorage.access_token` | `frontend/src/app/page.tsx`, `frontend/src/lib/api.ts` |

## 11. Known gaps and fallback paths

- `backend/data/lessons.json` is missing, so `AdaptiveLearning` uses defaults; the active lesson catalog is supplied by `MockDB`.
- Authentication is split between JSON and SQLite migration rather than having one complete source of truth.
- Development token secrets are process-local. Restarting the backend invalidates existing development tokens, so users must log in again.
- The Insights page now matches Dashboard for live totals, but separate speaking/prosody mastery is not stored in SQLite; those display values are derived or zero.
- `frontend/src/app/admin/page.tsx` currently performs a local role check and displays management UI without backend admin data handlers.
- The frontend production build passes, but the repository still has broad ESLint errors from explicit `any`, unused imports, hook rules, and JSX escaping. These are code-quality issues rather than a production-build blocker.
