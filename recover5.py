import json
import re

with open('dump.txt', 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        content = ""
        if 'content' in data and data['content']:
            content = data['content']
        elif 'tool_calls' in data:
            for tool in data['tool_calls']:
                content += json.dumps(tool)
        
        # Look for the Scalper's Terminal HTML block
        if 'id="tab-tick"' in content and 'AUTO-SCALP' in content and 'index.html' in content:
            # write it out
            with open('found_html.txt', 'w', encoding='utf-8') as out:
                out.write(content)
            print("Wrote to found_html.txt")
