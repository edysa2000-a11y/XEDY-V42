import sys

app_path = r'C:\Antigravity\Project\XEDY Mission Control\frontend\js\app.js'
with open(app_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace unconditional innerHTML writes with smart updates
text = text.replace("if (openTbody) openTbody.innerHTML = positionsHtml;", "if (openTbody && openTbody.innerHTML !== positionsHtml) openTbody.innerHTML = positionsHtml;")
text = text.replace("if (historyTbody) historyTbody.innerHTML = historyHtml;", "if (historyTbody && historyTbody.innerHTML !== historyHtml) historyTbody.innerHTML = historyHtml;")
text = text.replace("smcObTbody.innerHTML = obHtml;", "if (smcObTbody.innerHTML !== obHtml) smcObTbody.innerHTML = obHtml;")
text = text.replace("if (newsTbody) newsTbody.innerHTML = newsHtml;", "if (newsTbody && newsTbody.innerHTML !== newsHtml) newsTbody.innerHTML = newsHtml;")

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(text)
print("Fixed innerHTML flickering in v39_data!")
