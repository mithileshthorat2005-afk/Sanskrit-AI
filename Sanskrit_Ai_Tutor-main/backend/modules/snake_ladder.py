"""
Snake & Ladder Sanskrit Translation Game Engine
A gamified vocabulary builder for SanskritAI
"""

import random
from typing import Dict

# Core dictionary
SANSKRIT_DICTIONARY = [
    {"sanskrit": "अग्निः",   "english": "fire",      "hint": "Element of transformation"},
    {"sanskrit": "जलम्",    "english": "water",     "hint": "The essence of life"},
    {"sanskrit": "वायुः",    "english": "wind",      "hint": "Invisible yet powerful"},
    {"sanskrit": "पृथ्वी",   "english": "earth",     "hint": "She who supports all beings"},
    {"sanskrit": "आकाशः",   "english": "sky",       "hint": "The boundless expanse above"},
    {"sanskrit": "सूर्यः",   "english": "sun",       "hint": "Giver of light and warmth"},
    {"sanskrit": "चन्द्रः",  "english": "moon",      "hint": "Ruler of the night sky"},
    {"sanskrit": "नदी",     "english": "river",     "hint": "She who flows endlessly"},
    {"sanskrit": "वृक्षः",   "english": "tree",      "hint": "Silent guardian of the forest"},
    {"sanskrit": "पुष्पम्",  "english": "flower",    "hint": "Nature's delicate offering"},
    {"sanskrit": "फलम्",    "english": "fruit",     "hint": "Reward of patience"},
    {"sanskrit": "गृहम्",   "english": "house",     "hint": "Shelter and belonging"},
    {"sanskrit": "मार्गः",   "english": "path",      "hint": "The way forward"},
    {"sanskrit": "विद्या",   "english": "knowledge", "hint": "That which illuminates the mind"},
    {"sanskrit": "धर्मः",    "english": "duty",      "hint": "Righteous conduct"},
]

# Fixed Game Board Mapping (The World Map)
LADDERS = {
    2:  11,   # Early Spark
    4:  14,   # Focus -> Deep Learning
    9:  31,   # Practice -> Mastery
    16: 26,   # Requested Ascent
    20: 38,   # Consistency -> High Wisdom
    28: 47,   # Dedication -> Near Summit
    35: 45,   # Final Sprint
}

SNAKES = {
    12: 2,    # Distraction -> Setback
    17: 7,    # Doubt
    25: 11,   # Pride -> Fall
    32: 15,   # Confusion
    38: 24,   # Laziness -> Relearn
    44: 31,   # Ego -> Humility
    49: 38,   # The 'Heartbreak' snake near the finish
}

WIN_THRESHOLD = 50
MIN_POSITION  = 1


def pick_random_word(exclude_sanskrit: str = "") -> Dict:
    candidates = [w for w in SANSKRIT_DICTIONARY if w["sanskrit"] != exclude_sanskrit]
    return random.choice(candidates)


def process_turn(current_position: int, asked_word: str, user_answer: str) -> Dict:
    entry = next((w for w in SANSKRIT_DICTIONARY if w["sanskrit"] == asked_word), None)

    if entry is None:
        next_word = pick_random_word()
        return {
            "message": "Something went wrong. Here's a new word!",
            "position": current_position,
            "event": "error",
            "correct_answer": "",
            "next_word": {"sanskrit": next_word["sanskrit"], "hint": next_word["hint"]},
            "game_over": False,
        }

    correct_answer = entry["english"]
    is_correct = user_answer.strip().lower() == correct_answer.strip().lower()

    if is_correct:
        # Fixed movement: Correct answer = Move forward +5 positions
        advance = 5
        target_pos = current_position + advance
        
        # Check if landing on a ladder
        if target_pos in LADDERS:
            final_pos = LADDERS[target_pos]
            msg = f"✨ LADDER UP! 🪜 You climbed from {target_pos} to {final_pos}!"
            event = "ladder"
        else:
            final_pos = target_pos
            msg = f"Correct! You advanced to position {final_pos}."
            event = "correct"

        # Check win
        if final_pos >= WIN_THRESHOLD:
            return {
                "message": f"Correct! 🏆 VICTORY! You reached position {final_pos} and won the game!",
                "position": 1,
                "event": "win",
                "correct_answer": correct_answer,
                "next_word": {"sanskrit": pick_random_word()["sanskrit"], "hint": pick_random_word()["hint"]},
                "game_over": True,
            }

        next_word = pick_random_word(exclude_sanskrit=asked_word)
        return {
            "message": msg,
            "position": final_pos,
            "event": event,
            "correct_answer": correct_answer,
            "next_word": {"sanskrit": next_word["sanskrit"], "hint": next_word["hint"]},
            "game_over": False,
        }

    else:
        # Fixed movement: Wrong answer = Slide -3 positions
        target_pos = max(MIN_POSITION, current_position - 3)
        
        # Check if landing on a snake
        if target_pos in SNAKES:
            final_pos = SNAKES[target_pos]
            msg = f"🔥 SNAKE BITE! 🐍 You slid down from {target_pos} to {final_pos}. The answer was \"{correct_answer}\"."
            event = "snake"
        else:
            final_pos = target_pos
            msg = f"Oops, wrong! The answer was \"{correct_answer}\". You slid back to {final_pos}."
            event = "wrong"

        next_word = pick_random_word(exclude_sanskrit=asked_word)
        return {
            "message": msg,
            "position": final_pos,
            "event": event,
            "correct_answer": correct_answer,
            "next_word": {"sanskrit": next_word["sanskrit"], "hint": next_word["hint"]},
            "game_over": False,
        }


def start_new_game() -> Dict:
    first_word = pick_random_word()
    return {
        "message": "🎲 Welcome to the Sanskrit Arena! Start your journey at Position 1.",
        "position": 1,
        "next_word": {"sanskrit": first_word["sanskrit"], "hint": first_word["hint"]},
        "game_over": False,
    }
