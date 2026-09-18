import json

transcript_path = r'C:\Users\ACER\.gemini\antigravity\brain\ff078144-78bd-4046-8cee-d799be7bfb8a\.system_generated\logs\transcript_full.jsonl'

with open('recovered_blocks.txt', 'w', encoding='utf-8') as out:
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            if 'tool_calls' in data:
                for tool in data['tool_calls']:
                    if tool['function']['name'] in ['multi_replace_file_content', 'replace_file_content']:
                        args = json.loads(tool['function']['arguments'])
                        chunks = args.get('ReplacementChunks', [])
                        if not chunks and 'ReplacementContent' in args:
                            chunks = [args]
                        for chunk in chunks:
                            content = chunk.get('ReplacementContent', '')
                            if 'tab-tick' in content or 'tab-narasi' in content or 'scalpTickHistory' in content:
                                out.write("=== RECOVERED CHUNK ===\n")
                                out.write(content + "\n")
