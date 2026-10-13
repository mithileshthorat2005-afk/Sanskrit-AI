"""
Bayesian Knowledge Tracing (BKT) Engine for SanskritAI
Tracks student mastery per skill/lesson using a Hidden Markov Model.
"""

import math
import json
import os
from typing import Dict, Optional, List, Tuple

# ─── Default BKT Parameters ────────────────────────────────
DEFAULT_PARAMS = {
    # p(L0) - Initial probability of knowing the skill
    "l0": {
        "beginner": 0.25,    # Difficulty 1-4
        "intermediate": 0.10, # Difficulty 5-7
        "advanced": 0.05,     # Difficulty 8-10
    },
    # p(T) - Probability of learning from each attempt
    "t": 0.15,
    # p(G) - Probability of guessing correctly
    "g": 0.25,
    # p(S) - Probability of slipping (knowing but answering wrong)
    "s": 0.10,
}

class BKTEngine:
    def __init__(self, data_file: str = "data/bkt_progress.json"):
        self.data_file = data_file
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Create data file if it doesn't exist."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def _load(self) -> Dict:
        """Load all BKT data from JSON."""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self, data: Dict):
        """Save BKT data to JSON."""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_skill_params(self, skill_id: int, difficulty: int = 3) -> Dict:
        """
        Get BKT parameters for a skill.
        difficulty: 1-10 scale, used to set initial mastery (l0).
        """
        # Determine level from difficulty
        if difficulty <= 4:
            level = "beginner"
        elif difficulty <= 7:
            level = "intermediate"
        else:
            level = "advanced"

        return {
            "l0": DEFAULT_PARAMS["l0"][level],
            "t": DEFAULT_PARAMS["t"],
            "g": DEFAULT_PARAMS["g"],
            "s": DEFAULT_PARAMS["s"],
        }

    def update_mastery(self, current_mastery: float, is_correct: bool, params: Dict) -> float:
        """
        Update the mastery probability using Bayes theorem (HMM update).
        
        The BKT update formula:
        
        Let:
            p(L_n) = current mastery probability before the attempt
            p(T)  = learning rate
            p(G)  = guess probability
            p(S)  = slip probability
        
        Step 1: Compute probability of correct answer:
            p(correct) = p(L_n) * (1 - p(S)) + (1 - p(L_n)) * p(G)
        
        Step 2: Apply Bayes theorem to get posterior mastery after observing correctness:
            
            If correct:
                p(L_n | correct) = [p(L_n) * (1 - p(S))] / p(correct)
            
            If incorrect:
                p(L_n | incorrect) = [p(L_n) * p(S)] / (1 - p(correct))
        
        Step 3: Apply learning transition to get new mastery for next attempt:
            p(L_{n+1}) = p(L_n | observation) + (1 - p(L_n | observation)) * p(T)
        
        Returns updated mastery probability (0-1).
        """
        L = current_mastery
        t = params["t"]
        g = params["g"]
        s = params["s"]

        # Clamp current mastery to valid range
        L = max(0.0, min(1.0, L))

        # Step 1: Probability of getting correct answer
        p_correct = L * (1 - s) + (1 - L) * g

        # Step 2: Posterior probability of knowing after the attempt
        if is_correct:
            # Observed correct: it could be because they know it (not slip) or guessed
            if p_correct > 0:
                posterior = (L * (1 - s)) / p_correct
            else:
                posterior = L  # fallback
        else:
            # Observed incorrect: could be because they don't know it (not guess) or slipped
            p_incorrect = 1 - p_correct
            if p_incorrect > 0:
                posterior = (L * s) / p_incorrect
            else:
                posterior = L  # fallback

        # Clamp posterior
        posterior = max(0.0, min(1.0, posterior))

        # Step 3: Apply learning transition (they might learn from this attempt)
        new_mastery = posterior + (1 - posterior) * t

        # Clamp final result
        return max(0.0, min(1.0, new_mastery))

    def get_user_skill_data(self, username: str, skill_id: int) -> Dict:
        """Get the current mastery and attempt count for a specific skill."""
        data = self._load()
        user_data = data.get(username, {})
        skills = user_data.get("skills", {})
        skill_key = str(skill_id)
        if skill_key in skills:
            return skills[skill_key]
        return {
            "mastery": 0.0,  # Will be set on first attempt
            "attempts": 0,
            "correct": 0,
        }

    def record_attempt(self, username: str, skill_id: int, is_correct: bool, difficulty: int = 3) -> Dict:
        """
        Record a student's attempt on a skill, update mastery, and return new mastery.
        """
        data = self._load()
        user_data = data.get(username, {})
        skills = user_data.get("skills", {})
        skill_key = str(skill_id)

        # Get current data or initialize
        if skill_key not in skills:
            skills[skill_key] = {
                "mastery": 0.0,
                "attempts": 0,
                "correct": 0,
            }

        current = skills[skill_key]
        current_mastery = current["mastery"]

        # If this is the first attempt, initialize mastery with l0
        if current["attempts"] == 0:
            params = self.get_skill_params(skill_id, difficulty)
            current_mastery = params["l0"]
            current["mastery"] = current_mastery

        # Get params for update (use stored or default)
        params = self.get_skill_params(skill_id, difficulty)

        # Update mastery using BKT
        new_mastery = self.update_mastery(current_mastery, is_correct, params)

        # Update records
        current["mastery"] = new_mastery
        current["attempts"] += 1
        if is_correct:
            current["correct"] += 1

        # Save back
        skills[skill_key] = current
        user_data["skills"] = skills
        data[username] = user_data
        self._save(data)

        return {
            "skill_id": skill_id,
            "mastery": new_mastery,
            "attempts": current["attempts"],
            "correct": current["correct"],
        }

    def get_mastery_for_skills(self, username: str, skill_ids: List[int]) -> Dict[int, float]:
        """Get mastery probabilities for multiple skills."""
        data = self._load()
        user_data = data.get(username, {})
        skills = user_data.get("skills", {})
        result = {}
        for sid in skill_ids:
            skill_key = str(sid)
            if skill_key in skills:
                result[sid] = skills[skill_key].get("mastery", 0.0)
            else:
                result[sid] = 0.0  # Not yet attempted, but we could return l0
        return result

    def get_recommendation(self, username: str, all_lessons: List[Dict]) -> Optional[Dict]:
        """
        Recommend the next best lesson based on BKT mastery and prerequisites.
        
        Strategy:
        1. For each lesson, check if all prerequisites have mastery >= 0.7
        2. Among eligible lessons, prioritize those with the LOWEST mastery
           (i.e., the weakest skill that the student is ready to learn)
        3. If all mastered, recommend the lesson with the lowest mastery overall
        """
        if not all_lessons:
            return None

        data = self._load()
        user_data = data.get(username, {})
        skills = user_data.get("skills", {})

        # Build mastery map from BKT data
        mastery_map = {}
        for skill_key, skill_data in skills.items():
            mastery_map[int(skill_key)] = skill_data.get("mastery", 0.0)

        eligible = []
        for lesson in all_lessons:
            lesson_id = lesson.get("id")
            prereqs = lesson.get("prerequisites", [])

            # Check if all prerequisites are mastered (mastery >= 0.7)
            prereqs_met = True
            for prereq in prereqs:
                mastery = mastery_map.get(prereq, 0.0)
                if mastery < 0.7:
                    prereqs_met = False
                    break

            if not prereqs_met:
                continue

            # Get mastery for this lesson (default to 0.0 if never attempted)
            mastery = mastery_map.get(lesson_id, 0.0)
            eligible.append({
                "lesson": lesson,
                "mastery": mastery,
                "attempts": skills.get(str(lesson_id), {}).get("attempts", 0),
            })

        if not eligible:
            # If no eligible lessons, return the lesson with lowest mastery
            # (to encourage practice even if prerequisites aren't fully met)
            best = min(all_lessons, key=lambda l: mastery_map.get(l.get("id", 0), 0.0))
            return best

        # Sort eligible by mastery ascending (lowest mastery first)
        eligible.sort(key=lambda x: x["mastery"])
        return eligible[0]["lesson"]

    def get_user_summary(self, username: str) -> Dict:
        """Get a summary of the user's BKT progress."""
        data = self._load()
        user_data = data.get(username, {})
        skills = user_data.get("skills", {})
        total_skills = len(skills)
        mastered = sum(1 for s in skills.values() if s.get("mastery", 0.0) >= 0.7)
        avg_mastery = sum(s.get("mastery", 0.0) for s in skills.values()) / total_skills if total_skills > 0 else 0.0

        return {
            "total_skills": total_skills,
            "mastered_skills": mastered,
            "average_mastery": avg_mastery,
            "skills": skills,
        }
