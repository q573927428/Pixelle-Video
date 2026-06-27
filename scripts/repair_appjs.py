import re

fp = 'f:\\qukuailian\\ai\\shipin\\Pixelle-Video\\modern_ui\\app.js'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: remove orphaned lines after this.ttsVoices
pattern = r"(this\.ttsVoices = voices\.voices \|\| \[\];)\s*\n\s+this\.quickForm\.frame_template[\s\S]*?\n\s+\}\s*\n\s+\}\s*\n\s+\}"
replacement = r"\1"
content = re.sub(pattern, replacement, content)

# Fix 2: fix indentation of 'computed:' at line 91
content = content.replace('        computed:', '      computed:')

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed successfully")
