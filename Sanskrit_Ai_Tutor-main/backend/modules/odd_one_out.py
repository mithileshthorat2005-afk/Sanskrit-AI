"""
Odd One Out – Sanskrit Vocabulary Game Engine
Identify the word that doesn't belong to the category.
"""

import random
from typing import Dict, List

QUESTIONS: List[Dict] = [
    {
        "category": "Animals (पशवः)",
        "options": [
            {"sanskrit": "गजः", "english": "Elephant"},
            {"sanskrit": "अश्वः", "english": "Horse"},
            {"sanskrit": "सिंहः", "english": "Lion"},
            {"sanskrit": "पुष्पम्", "english": "Flower"},
        ],
        "correct_index": 3,
        "correct_word": "पुष्पम्",
    },
    {
        "category": "Colors (वर्णाः)",
        "options": [
            {"sanskrit": "रक्तः", "english": "Red"},
            {"sanskrit": "नीलः", "english": "Blue"},
            {"sanskrit": "नदी", "english": "River"},
            {"sanskrit": "पीतः", "english": "Yellow"},
        ],
        "correct_index": 2,
        "correct_word": "नदी",
    },
    {
        "category": "Body Parts (अङ्गानि)",
        "options": [
            {"sanskrit": "हस्तः", "english": "Hand"},
            {"sanskrit": "वृक्षः", "english": "Tree"},
            {"sanskrit": "नेत्रम्", "english": "Eye"},
            {"sanskrit": "पादः", "english": "Foot"},
        ],
        "correct_index": 1,
        "correct_word": "वृक्षः",
    },
    {
        "category": "Elements (तत्त्वानि)",
        "options": [
            {"sanskrit": "अग्निः", "english": "Fire"},
            {"sanskrit": "जलम्", "english": "Water"},
            {"sanskrit": "वायुः", "english": "Wind"},
            {"sanskrit": "गृहम्", "english": "House"},
        ],
        "correct_index": 3,
        "correct_word": "गृहम्",
    },
    {
        "category": "Celestial (खगोलीयम्)",
        "options": [
            {"sanskrit": "फलम्", "english": "Fruit"},
            {"sanskrit": "सूर्यः", "english": "Sun"},
            {"sanskrit": "चन्द्रः", "english": "Moon"},
            {"sanskrit": "ताराः", "english": "Star"},
        ],
        "correct_index": 0,
        "correct_word": "फलम्",
    },
    {
        "category": "Nature (प्रकृतिः)",
        "options": [
            {"sanskrit": "नदी", "english": "River"},
            {"sanskrit": "पर्वतः", "english": "Mountain"},
            {"sanskrit": "वनम्", "english": "Forest"},
            {"sanskrit": "रथः", "english": "Chariot"},
        ],
        "correct_index": 3,
        "correct_word": "रथः",
    },
    {
        "category": "Family (कुटुम्बम्)",
        "options": [
            {"sanskrit": "माता", "english": "Mother"},
            {"sanskrit": "पिता", "english": "Father"},
            {"sanskrit": "आकाशः", "english": "Sky"},
            {"sanskrit": "पुत्रः", "english": "Son"},
        ],
        "correct_index": 2,
        "correct_word": "आकाशः",
    },
    {
        "category": "Numbers (सङ्ख्याः)",
        "options": [
            {"sanskrit": "एकम्", "english": "One"},
            {"sanskrit": "द्वे", "english": "Two"},
            {"sanskrit": "त्रीणि", "english": "Three"},
            {"sanskrit": "धर्मः", "english": "Duty"},
        ],
        "correct_index": 3,
        "correct_word": "धर्मः",
    },
]


def get_random_question(exclude_category: str = "") -> Dict:
    """Return a random question, optionally excluding a category."""
    candidates = [q for q in QUESTIONS if q["category"] != exclude_category]
    if not candidates:
        candidates = QUESTIONS
    q = random.choice(candidates)
    return {
        "category": q["category"],
        "options": q["options"],
        "correct_index": q["correct_index"],
        "correct_word": q["correct_word"],
    }


def check_answer(question_data: Dict, user_choice: int) -> Dict:
    """
    Validate the user's answer for one turn.

    Args:
        question_data: The question dict (category, options, correct_index, correct_word).
        user_choice:   The 1-based index chosen by the user (1–4).

    Returns:
        A dict with message, is_correct, correct_word, and next_question.
    """
    correct_index = question_data["correct_index"]
    correct_word = question_data["correct_word"]
    correct_english = question_data["options"][correct_index]["english"]

    is_correct = (user_choice - 1) == correct_index

    if is_correct:
        msg = f"Correct! 🎉 {correct_word} ({correct_english}) is the odd one out."
    else:
        msg = f"Not quite! The odd one out was {correct_word} ({correct_english})."

    next_q = get_random_question(exclude_category=question_data["category"])

    return {
        "message": msg,
        "is_correct": is_correct,
        "correct_word": correct_word,
        "correct_index": correct_index,
        "next_question": next_q,
    }
