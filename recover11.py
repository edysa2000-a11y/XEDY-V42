import json
transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript_full.jsonl'
count = 0
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        count += 1
        
        if count > len(open(transcript_path, 'r', encoding='utf-8').readlines()) - 100:
            data = json.loads(line)
            if 'tool_calls' in data:
                for tool in data['tool_calls']:
                    if tool.get('name') in ['multi_replace_file_content', 'replace_file_content']:
                        args = tool.get('args', {})
                        print(tool.get('name'), args.get('TargetFile'))
