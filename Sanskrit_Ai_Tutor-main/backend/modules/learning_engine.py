"""
Adaptive learning engine for SanskritaAI
Simple rule-based recommendation system for prototype
"""

import json
import random
import os
from typing import Dict, List, Any

class AdaptiveLearning:
    def __init__(self, lessons_file='data/lessons.json'):
        self.lessons_file = lessons_file
        self.lessons = self.load_lessons()
    
    def load_lessons(self):
        """Load lessons from JSON file with better error handling"""
        try:
            if os.path.exists(self.lessons_file):
                with open(self.lessons_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        data = json.loads(content)
                        if 'lessons' in data and data['lessons']:
                            print(f"Loaded {len(data['lessons'])} lessons from file")
                            return data['lessons']
                        else:
                            print("Lessons file has no lessons data")
                    else:
                        print("Lessons file is empty")
            else:
                print(f"Lessons file not found at {self.lessons_file}")
        
        except json.JSONDecodeError as e:
            print(f"Error parsing lessons JSON: {e}")
        except Exception as e:
            print(f"Unexpected error loading lessons: {e}")
        
        # Return default lessons if anything fails
        print("Using default lessons")
        return self.get_default_lessons()
    
    def get_default_lessons(self):
        """Default lessons for prototype"""
        return [
            {
                "id": 1,
                "title": "Introduction to Sanskrit",
                "description": "Learn the basics of Sanskrit alphabet and pronunciation",
                "level": "beginner",
                "duration": 15,
                "content": "Sanskrit is one of the oldest languages in the world...",
                "prerequisites": [],
                "difficulty": 3,
                "quiz": []
            },
            {
                "id": 2,
                "title": "Basic Sentence Structure",
                "description": "Learn Subject-Object-Verb order in Sanskrit",
                "level": "beginner",
                "duration": 20,
                "content": "Sanskrit typically follows SOV word order...",
                "prerequisites": [1],
                "difficulty": 4,
                "quiz": []
            },
            {
                "id": 3,
                "title": "Noun Cases (Vibhakti)",
                "description": "Learn the 7 cases in Sanskrit grammar",
                "level": "intermediate",
                "duration": 25,
                "content": "Sanskrit has 7 grammatical cases...",
                "prerequisites": [1, 2],
                "difficulty": 7,
                "quiz": []
            }
        ]
    
    def get_recommendation(self, user: Dict) -> Dict:
        """Get personalized lesson recommendation"""
        
        user_level = user.get('level', 'beginner')
        completed = user.get('completed', [])
        
        # Filter lessons by level and prerequisites
        available_lessons = []
        for lesson in self.lessons:
            if lesson['level'] == user_level:
                # Check if prerequisites are met
                prereq_met = all(prereq in completed for prereq in lesson.get('prerequisites', []))
                if prereq_met or not lesson.get('prerequisites'):
                    available_lessons.append(lesson)
        
        # If no lessons at current level, try easier level
        if not available_lessons and user_level != 'beginner':
            for lesson in self.lessons:
                if lesson['level'] == 'beginner' and lesson['id'] not in completed:
                    available_lessons.append(lesson)
        
        # Return random lesson from available (or first one)
        if available_lessons:
            return random.choice(available_lessons)
        elif self.lessons:
            return self.lessons[0]
        else:
            return self.get_default_lessons()[0]
    
    def calculate_proficiency(self, user_performance: Dict) -> float:
        """Calculate user proficiency score (0-100)"""
        total_score = 0
        total_weight = 0
        
        for lesson_id, performance in user_performance.items():
            score = performance.get('score', 0)
            weight = performance.get('weight', 1)
            total_score += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return min(100, total_score / total_weight)
        return 0
    
    def update_learning_path(self, user_id: str, lesson_id: int, score: float):
        """Update user's learning path based on performance"""
        # In production, this would update ML model
        # For prototype, just log the activity
        return {
            "user_id": user_id,
            "lesson_id": lesson_id,
            "score": score,
            "recommendation": "Continue to next lesson" if score >= 70 else "Review current lesson"
        }
