import re

html_path = "frontend/index.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Fix Child 1 (Panels 1 & 2)
content = content.replace(
    '<!-- TOP LEFT: PANELS 1 & 2 -->\n                    <div style="display: flex; flex-direction: column; gap: 0.5rem;">',
    '<!-- TOP LEFT: PANELS 1 & 2 -->\n                    <div style="grid-column: 1 / 2; grid-row: 1 / 2; display: flex; flex-direction: column; gap: 0.5rem;">'
)

# Fix Child 2 (Panel 3)
content = content.replace(
    '<!-- TOP RIGHT: PANEL 3 (Scorecard) -->\n                    <div class="bg-dark-panel rounded border border-secondary p-2" style="grid-row: 1 / 3;">',
    '<!-- TOP RIGHT: PANEL 3 (Scorecard) -->\n                    <div class="bg-dark-panel rounded border border-secondary p-2" style="grid-column: 2 / 3; grid-row: 1 / 3;">'
)

# Fix Child 3 (Panels 4, 5, 6, 7)
content = content.replace(
    '<!-- MIDDLE LEFT: PANELS 4, 5, 6, 7 -->\n                    <div style="display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 0.5rem;">',
    '<!-- MIDDLE LEFT: PANELS 4, 5, 6, 7 -->\n                    <div style="grid-column: 1 / 2; grid-row: 2 / 3; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 0.5rem;">'
)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Grid layout fixed.")
