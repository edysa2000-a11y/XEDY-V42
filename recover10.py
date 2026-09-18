import json
import os

transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript_full.jsonl'

# Read files
index_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\index.html'
app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'

with open(index_path, 'r', encoding='utf-8') as f:
    index_content = f.read()
with open(app_path, 'r', encoding='utf-8') as f:
    app_content = f.read()

files = {index_path: index_content, app_path: app_content}

def apply_replacement(text, target, replacement):
    if target in text:
        return text.replace(target, replacement, 1)
    else:
        print(f"TARGET NOT FOUND! Skipping...\nTarget snippet: {target[:50]}...")
        return text

tool_calls_to_apply = []

with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'tool_calls' in data:
                for tool in data['tool_calls']:
                    if tool.get('name') in ['multi_replace_file_content', 'replace_file_content']:
                        args = tool.get('args', {})
                        target_file = args.get('TargetFile', '')
                        if target_file.endswith('index.html') or target_file.endswith('app.js'):
                            tool_calls_to_apply.append(args)
        except Exception:
            pass

print(f"Found {len(tool_calls_to_apply)} edits. Applying...")

# Skip the ones where I intentionally removed the tick dashboard, since I want to RESTORE it?
# Wait, the user asked to "Hapus Tab ini" (Delete tick_dashboard).
# Did I delete it? Yes.
# But then they said "kembalikan Tampilan Web dan Code semua ini" meaning they want it back.
# Wait, if I just do nothing and they want it back, I don't need to apply anything!
# But wait... the "AI Market Narrative" tab was ADDED by me in this session?
# No! "AI Market Narrative" was already there in the user's view, wait, let's see what edits I made!
