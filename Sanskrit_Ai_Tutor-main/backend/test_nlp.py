from modules.nlp_processor import SanskritNLP

nlp = SanskritNLP()

# Test 1: Basic analysis
text = "रामः वनं गच्छति।"
result = nlp.analyze_text(text, use_ai=False)
print("Basic Analysis:", result['score'], result['translation'])

# Test 2: AI analysis (if key exists)
if nlp.api_key:
    result = nlp.analyze_text(text, use_ai=True)
    print("AI Analysis:", result['score'], result['translation'])
else:
    print("No AI key, skipping AI test")

# Test 3: Translation only
translation = nlp.translate_sanskrit_to_english("रामः वनं गच्छति।")
print("Translation:", translation)