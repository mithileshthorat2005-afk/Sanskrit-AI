content = open('modules/nlp_processor.py', 'r', encoding='utf-8').read()

# The bad section (with double curly braces in plain dict)
bad_block = '            data = {\n                "model": "grok-beta",\n                "messages": [\n                    {{"role": "system", "content": "You are an expert Sanskrit grammarian and linguist."}},\n                    {{"role": "user", "content": prompt}}\n                ],\n                "response_format": {{ "type": "json_object" }},\n                "temperature": 0\n            }'

good_block = '            payload = {\n                "model": "grok-beta",\n                "messages": [\n                    {"role": "system", "content": "You are an expert Sanskrit grammarian and linguist with deep knowledge of Paninian grammar, POS tagging, and morphological analysis."},\n                    {"role": "user", "content": prompt}\n                ],\n                "response_format": {"type": "json_object"},\n                "temperature": 0\n            }'

# Try normalizing line endings first
normalized = content.replace('\r\n', '\n')
bad_normalized = bad_block.replace('\r\n', '\n')

if bad_normalized in normalized:
    fixed = normalized.replace(bad_normalized, good_block)
    # Also fix the variable name in the requests.post call
    fixed = fixed.replace('json=data, timeout=30)', 'json=payload, timeout=30)')
    open('modules/nlp_processor.py', 'w', encoding='utf-8', newline='').write(fixed)
    print("SUCCESS: Fixed the double curly braces bug in the data dict!")
else:
    # Try byte-level search
    print("===CONTENT AROUND DATA DICT===")
    idx = content.find('"model": "grok-beta"')
    print(repr(content[idx-30:idx+200]))
