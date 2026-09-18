import json

transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript_full.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        if 'id="tab-tick"' in line and 'AUTO-SCALP' in line:
            data = json.loads(line)
            if 'content' in data and data['content']:
                with open('recovered_tab_tick.txt', 'w', encoding='utf-8') as out:
                    out.write(data['content'])
                    print("Found in content!")
