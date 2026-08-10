import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Restore tab-executive nav link and make it active
nav_replacement = """            <ul class="nav flex-column nav-pills" id="sidebar-nav">
                <li class="nav-item"><a class="nav-link active" data-target="tab-executive" href="#">🏠 Executive Dashboard</a></li>
                <li class="nav-item"><a class="nav-link" data-target="tab-xau-os" href="#">🤖 XAU AI GOLD OS</a></li>"""

content = re.sub(r'            <ul class="nav flex-column nav-pills" id="sidebar-nav">\n                <li class="nav-item"><a class="nav-link" data-target="tab-xau-os" href="#">🤖 XAU AI GOLD OS</a></li>', nav_replacement, content)

# 2. Make tab-moneyflow visible in nav
content = content.replace('<li class="nav-item d-none"><a class="nav-link" data-target="tab-moneyflow" href="#">💸 Money Flow Transmission</a></li>', '<li class="nav-item"><a class="nav-link" data-target="tab-moneyflow" href="#" style="color: #00ffaa;">💸 Money Flow V39</a></li>')

# 3. Remove tab-v39-overview nav link
content = re.sub(r'                <li class="nav-item"><a class="nav-link active" data-target="tab-v39-overview" href=".*?>🌟 V39 Ultimate Overview</a></li>\n', '', content)

# 4. Find tab-v39-overview div and extract it
start_v39 = content.find('<!-- V39 13-PANEL MEGA DASHBOARD (FULLSCREEN NO-SCROLL) -->')
end_v39 = content.find('<!-- V39 ULTIMATE OVERVIEW TAB -->')
# wait, my previous script had:
# content = content.replace('            <div id="tab-logs" class="spa-tab d-none">', v39_grid + '\n            <div id="tab-logs" class="spa-tab d-none">')
# so the end of the injected block is right before `<div id="tab-logs"`

end_v39 = content.find('<div id="tab-logs"', start_v39)
v39_grid_html = content[start_v39:end_v39]

# Delete v39_grid from its current position
content = content[:start_v39] + content[end_v39:]

# Change the id in v39_grid_html to tab-moneyflow and add d-none
v39_grid_html = v39_grid_html.replace('id="tab-v39-overview"', 'id="tab-moneyflow"')
v39_grid_html = v39_grid_html.replace('class="spa-tab h-100 w-100"', 'class="spa-tab d-none h-100 w-100"')

# Now replace the old tab-moneyflow div
start_moneyflow = content.find('<div id="tab-moneyflow"')
if start_moneyflow != -1:
    end_moneyflow = content.find('<div id="tab-', start_moneyflow + 20)
    # Replace old moneyflow with new grid
    content = content[:start_moneyflow] + v39_grid_html + content[end_moneyflow:]
else:
    # If not found, just append it before tab-forecast or something
    start_forecast = content.find('<div id="tab-forecast"')
    content = content[:start_forecast] + v39_grid_html + content[start_forecast:]

# 5. Make tab-executive visible again
content = content.replace('<div id="tab-executive" class="spa-tab d-none">', '<div id="tab-executive" class="spa-tab">')

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched to restore Executive Dashboard and overwrite Money Flow tab.")

