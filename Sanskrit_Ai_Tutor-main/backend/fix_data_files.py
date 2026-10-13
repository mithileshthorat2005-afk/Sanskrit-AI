import json
import os
from datetime import datetime

print("🔧 Fixing all data files...\n")

# Create data directory
os.makedirs('data', exist_ok=True)

# 1. Fix users.json
print("1️⃣ Fixing users.json...")
users_data = {
    "admin": {
        "password": "hashed_admin123",
        "role": "admin",
        "created_at": datetime.now().isoformat(),
        "level": "advanced",
        "completed": 10,
        "streak_days": 5
    },
    "demo": {
        "password": "hashed_demo123",
        "role": "student",
        "created_at": datetime.now().isoformat(),
        "level": "beginner",
        "completed": 2,
        "streak_days": 3
    }
}

with open('data/users.json', 'w', encoding='utf-8') as f:
    json.dump(users_data, f, indent=2, ensure_ascii=False)
print("   ✅ users.json created/updated")

# 2. Check lessons.json
print("\n2️⃣ Checking lessons.json...")
if os.path.exists('data/lessons.json'):
    with open('data/lessons.json', 'r', encoding='utf-8') as f:
        lessons = json.load(f)
    print(f"   ✅ lessons.json exists with {len(lessons.get('lessons', []))} lessons")
else:
    print("   ⚠️ lessons.json not found, but that's okay for now")

# 3. Create sanskrit_sentences.json
print("\n3️⃣ Creating sanskrit_sentences.json...")
sentences_data = {
    "sentences": [
        {
            "id": 1,
            "sanskrit": "रामः वनं गच्छति।",
            "devanagari": "रामः वनं गच्छति।",
            "translation": "Rama goes to the forest.",
            "words": ["रामः", "वनं", "गच्छति"],
            "pattern": "Subject Object Verb",
            "difficulty": "beginner",
            "tags": ["action", "movement"],
            "created_at": datetime.now().isoformat()
        }
    ],
    "patterns": [
        {
            "pattern": "Subject Object Verb",
            "template": "{subject} {object} {verb}।",
            "examples": ["रामः वनं गच्छति।"]
        }
    ]
}

with open('data/sanskrit_sentences.json', 'w', encoding='utf-8') as f:
    json.dump(sentences_data, f, indent=2, ensure_ascii=False)
print("   ✅ sanskrit_sentences.json created")

# 4. Verify all files
print("\n4️⃣ Verifying all files...")
files_to_check = ['users.json', 'lessons.json', 'sanskrit_sentences.json']
all_good = True

for file in files_to_check:
    file_path = f'data/{file}'
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"   ✅ {file}: {size} bytes - Valid JSON")
        except json.JSONDecodeError as e:
            print(f"   ❌ {file}: Invalid JSON - {e}")
            all_good = False
    else:
        print(f"   ⚠️ {file}: Not found")
        all_good = False

print("\n📊 Summary:")
if all_good:
    print("✅ All data files are fixed and valid!")
else:
    print("⚠️ Some files are still missing or invalid")

print("\n🚀 You can now run: streamlit run app.py")