import re
import os

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove nav items
content = re.sub(r'<li class="nav-item"><a class="nav-link" data-target="tab-trading" href="#">.*?</a></li>\n?', '', content)
content = re.sub(r'<li class="nav-item"><a class="nav-link" data-target="tab-automodel" href="#">.*?</a></li>\n?', '', content)

# 2. Remove the actual divs (extract block by counting divs or use a hacky way)
# Luckily, we can just find them and delete everything inside them until the next tab
# Let's see what is after them
tab_trading_start = content.find('<div id="tab-trading"')
tab_automodel_start = content.find('<div id="tab-automodel"')

if tab_trading_start != -1:
    tab_trading_end = content.find('<div id="tab-', tab_trading_start + 20)
    if tab_trading_end != -1:
        # We delete from start to end
        content = content[:tab_trading_start] + content[tab_trading_end:]

# Recalculate automodel since indices changed
tab_automodel_start = content.find('<div id="tab-automodel"')
if tab_automodel_start != -1:
    tab_automodel_end = content.find('<div id="tab-', tab_automodel_start + 20)
    if tab_automodel_end != -1:
        content = content[:tab_automodel_start] + content[tab_automodel_end:]

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

# Clean up app.js for active-ai-model-select references
js_path = "frontend/js/app.js"
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

# Just comment out or remove any block referencing active-ai-model-select
# Let's replace the whole string to avoid null reference error if it exists
js_content = js_content.replace('document.getElementById("active-ai-model-select")', 'null /* removed */')
js_content = js_content.replace('document.getElementById("btn-apply-model")', 'null /* removed */')

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print("UI cleanup done.")
