import json
transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript_full.jsonl'
narasi = ''
tick = ''
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if 'tool_calls' in data:
            for tool in data['tool_calls']:
                if tool.get('name') in ['multi_replace_file_content', 'replace_file_content']:
                    args = tool.get('args', {})
                    chunks = args.get('ReplacementChunks', [])
                    if not chunks and 'ReplacementContent' in args:
                        chunks = [args]
                    for chunk in chunks:
                        content = chunk.get('ReplacementContent', '')
                        if 'id="tab-narasi"' in content:
                            narasi = content
                        if 'id="tab-tick"' in content and 'Scalper\\'s Terminal' in content:
                            tick = content

with open('narasi_block.txt', 'w', encoding='utf-8') as out:
    out.write(narasi)
with open('tick_block.txt', 'w', encoding='utf-8') as out:
    out.write(tick)
print("Done!")
