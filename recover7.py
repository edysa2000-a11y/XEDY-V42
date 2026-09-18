import json

transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript_full.jsonl'
best_index = ""

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        
        # Check tool responses
        if 'content' in data and data['content']:
            c = data['content']
            if 'File Path: ile:///c:/Antigravity/Project/XEDY%20Mission%20Control/frontend/index.html' in c:
                if 'id="tab-tick"' in c and 'AUTO-SCALP' in c:
                    best_index = c

with open('best_index.txt', 'w', encoding='utf-8') as out:
    out.write(best_index)

