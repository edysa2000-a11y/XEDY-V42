import re

with open('dump.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Find the block starting with <div id="tab-tick" and ending appropriately
match = re.search(r'(<div id=\\"tab-tick\\".*?AUTO-SCALP.*?</div>\s*</div>\s*</div>\s*</div>)', text, re.DOTALL)
if match:
    with open('found_html.txt', 'w', encoding='utf-8') as out:
        out.write(match.group(1).replace('\\"', '"').replace('\\n', '\n'))
    print("Found HTML!")

