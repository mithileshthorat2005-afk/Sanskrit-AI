"""
Mock database for SanskritaAI prototype
Uses JSON files instead of real database
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class MockDB:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def _load_json_list(self, filename: str) -> List[Dict]:
        """Universal JSON loader — all lesson data methods delegate here."""
        file_path = os.path.join(self.data_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def get_lessons(self) -> List[Dict]:
        """Get all lessons"""
        lessons_file = os.path.join(self.data_dir, 'lessons.json')
        
        if os.path.exists(lessons_file):
            with open(lessons_file, 'r', encoding='utf-8') as f:
                return json.load(f)['lessons']
        
        # Return default lessons
        return [
            {
                "id": 1,
                "title": "Sanskrit Alphabet (Devanagari)",
                "level": "beginner",
                "duration": 10,
                "content": "Learn the 13 vowels and 33 consonants of Sanskrit...",
                "quiz": [
                    {
                        "id": 1,
                        "question": "How many vowels in Sanskrit?",
                        "options": ["10", "13", "15", "20"],
                        "answer": "13"
                    }
                ]
            },
            {
                "id": 2,
                "title": "Basic Greetings",
                "level": "beginner",
                "duration": 15,
                "content": "Learn common greetings: नमस्ते (Hello), सुप्रभातम् (Good morning)...",
                "quiz": [
                    {
                        "id": 1,
                        "question": "What does 'नमस्ते' mean?",
                        "options": ["Thank you", "Hello", "Goodbye", "Please"],
                        "answer": "Hello"
                    }
                ]
            }
        ]

    # ─── Lesson Data Accessors ─────────────────────────────
    # All use the shared _load_json_list helper for DRY code.

    def get_greetings(self) -> List[Dict]:
        """Get all greetings"""
        return self._load_json_list('sanskritGreetings.json')

    def get_numbers(self) -> List[Dict]:
        """Get number lesson data"""
        return self._load_json_list('sanskritNumbers.json')

    def get_self_intro(self) -> List[Dict]:
        """Get self introduction lesson data"""
        return self._load_json_list('sanskritSelfIntro.json')

    def get_pronouns(self) -> List[Dict]:
        """Get pronoun lesson data"""
        return self._load_json_list('sanskritPronouns.json')

    def get_verbs(self) -> List[Dict]:
        """Get verb lesson data"""
        return self._load_json_list('sanskritVerbs.json')

    def get_nouns(self) -> List[Dict]:
        """Get noun lesson data"""
        return self._load_json_list('sanskritNouns.json')

    def get_family(self) -> List[Dict]:
        """Get family lesson data"""
        return self._load_json_list('sanskritFamily.json')

    def get_question_words(self) -> List[Dict]:
        """Get question words lesson data"""
        return self._load_json_list('sanskritQuestionWords.json')

    def get_time_and_days(self) -> List[Dict]:
        """Get time and days lesson data"""
        return self._load_json_list('sanskritTimeAndDays.json')

    def get_vibhakti(self):
        """Get vibhakti data"""
        return self._load_json_list('sanskritVibhakti.json')

    def get_sandhi(self):
        """Get sandhi data"""
        return self._load_json_list('sanskritSandhi.json')

    def get_tenses(self):
        """Get verb tense data"""
        return self._load_json_list('sanskritTenses.json')

    def get_moods(self):
        """Get verb moods data (Imperative & Optative)"""
        return self._load_json_list('sanskritMoods.json')

    def get_pronouns_extended(self):
        """Get extended pronouns (dual & plural) data"""
        return self._load_json_list('sanskritPronounsExtended.json')

    def get_upasarga(self):
        """Get upasarga (verbal prefix) data"""
        return self._load_json_list('sanskritUpasarga.json')

    def get_voice(self):
        """Get active/passive voice data"""
        return self._load_json_list('sanskritVoice.json')

    def get_indeclinables(self):
        """Get indeclinables (avyaya) data"""
        return self._load_json_list('sanskritIndeclinables.json')

    def get_participles(self):
        """Get participles data"""
        return self._load_json_list('sanskritParticiples.json')

    def get_reading_composition(self):
        """Get reading and composition data"""
        return self._load_json_list('sanskritReadingComposition.json')

    def get_samasa1(self):
        """Get Samāsa (compounds) Part 1 data"""
        return self._load_json_list('sanskritSamasa1.json')

    def get_samasa2(self):
        return self._load_json_list('sanskritSamasa2.json')

    def get_participles2(self):
        return self._load_json_list('sanskritParticiples2.json')

    def get_stri_pratyaya(self):
        return self._load_json_list('sanskritStriPratyaya.json')

    def get_chandas(self):
        return self._load_json_list('sanskritChandas.json')
    
    def get_user_progress(self, username: str) -> Dict:
        """Get user progress"""
        progress_file = os.path.join(self.data_dir, f'{username}_progress.json')
        
        if os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                return json.load(f)
        
        # Default progress — total_lessons reflects actual curriculum size
        return {
            "username": username,
            "total_lessons": 20,
            "completed": 0,
            "in_progress": 2,
            "avg_score": 0,
            "streak_days": 0
        }
    
    def update_progress(self, username: str, lesson_id: int, status: str):
        """Update user progress"""
        progress_file = os.path.join(self.data_dir, f'{username}_progress.json')
        
        progress = self.get_user_progress(username)
        
        if status == 'completed':
            progress['completed'] = progress.get('completed', 0) + 1
        elif status == 'started':
            progress['in_progress'] = progress.get('in_progress', 0) + 1
        
        # Save progress
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        
        return progress
    
    def save_analysis(self, username: str, text: str, analysis: Dict):
        """Save grammar analysis"""
        analysis_file = os.path.join(self.data_dir, f'{username}_analyses.json')
        
        analyses = []
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r') as f:
                analyses = json.load(f)
        
        analyses.append({
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(analysis_file, 'w') as f:
            json.dump(analyses, f, indent=2)
    
    def get_recent_activities(self, username: str) -> List[Dict]:
        """Get recent user activities.

        This previously returned three hardcoded prototype rows regardless of
        the user, which the dashboard both displayed as real activity and
        counted as "words learned". There is no legacy activity store to read,
        so an empty list is returned; live activity comes from the SQLite
        dashboard summary via /activities.
        """
        return []
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (for admin)"""
        users_file = os.path.join(self.data_dir, 'users.json')
        
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users_data = json.load(f)
                users = []
                for username, data in users_data.items():
                    users.append({
                        "username": username,
                        "role": data.get("role", "student"),
                        "created_at": data.get("created_at", ""),
                        "level": data.get("level", "beginner")
                    })
                return users
        
        return []

    # ─── BKT Data Access ────────────────────────────────────────

    def get_bkt_engine(self):
        """Lazy load BKT engine (avoids circular import)."""
        from modules.bkt_engine import BKTEngine
        if not hasattr(self, '_bkt_engine'):
            self._bkt_engine = BKTEngine(data_file=os.path.join(self.data_dir, 'bkt_progress.json'))
        return self._bkt_engine

    def get_bkt_skill_data(self, username: str, skill_id: int) -> Dict:
        """Get BKT data for a specific skill."""
        engine = self.get_bkt_engine()
        return engine.get_user_skill_data(username, skill_id)

    def record_bkt_attempt(self, username: str, skill_id: int, is_correct: bool, difficulty: int = 3) -> Dict:
        """Record a BKT attempt and return updated mastery."""
        engine = self.get_bkt_engine()
        return engine.record_attempt(username, skill_id, is_correct, difficulty)

    def seed_bkt_mastery(self, username: str, mastery_by_skill: Dict[str, float]) -> int:
        """Seed starting mastery in the legacy JSON store (insert-if-absent).

        The SQLite `skill_mastery` table and this JSON file are the two halves
        of the existing persistence design: SQLite backs /dashboard, this file
        backs /bkt/mastery. Every BKT update writes both, so onboarding has to
        seed both too or the two read paths would disagree from the first
        attempt onwards.
        """
        engine = self.get_bkt_engine()
        return engine.seed_mastery(username, mastery_by_skill)

    def get_bkt_mastery_for_skills(self, username: str, skill_ids: List[int]) -> Dict[int, float]:
        """Get mastery for multiple skills."""
        engine = self.get_bkt_engine()
        return engine.get_mastery_for_skills(username, skill_ids)

    def get_bkt_attempts_for_skills(self, username: str, skill_ids: List[int]) -> Dict[int, int]:
        """Get graded-attempt counts for multiple skills (see bkt_engine)."""
        engine = self.get_bkt_engine()
        return engine.get_attempts_for_skills(username, skill_ids)

    def get_bkt_recommendation(self, username: str, lessons=None):
        """Get the recommended next lesson based on BKT.

        `lessons` should be passed by the caller (main.py) so this module
        never needs `from main import ...`, which breaks when the app is
        started as `uvicorn backend.main:app` (circular import).
        """
        if lessons is None:
            # Legacy fallback for direct MockDB consumers.
            try:
                from main import learning_engine
                lessons = learning_engine.lessons
            except Exception:
                lessons = self.get_lessons()
        return self.get_bkt_engine().get_recommendation(username, lessons)

    def get_bkt_summary(self, username: str) -> Dict:
        """Get BKT summary for the user."""
        engine = self.get_bkt_engine()
        return engine.get_user_summary(username)

