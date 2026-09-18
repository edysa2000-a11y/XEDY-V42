import json

transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript.jsonl'

with open(transcript_path, 'r', encoding='utf-8') as f:
    for i in range(5):
        line = f.readline()
        print(json.loads(line).keys())
