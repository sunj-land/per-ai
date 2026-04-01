import os
import re

AGENTS_DIR = "/Users/sunjie/Documents/AI/perAll/agents"
BACKEND_DIR = "/Users/sunjie/Documents/AI/perAll/backend"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original_content = content
    
    # 修复 utils 导入
    content = re.sub(r'from agents\.utils import', r'from agents.utils.utils import', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed utils import: {filepath}")

for root, dirs, files in os.walk(AGENTS_DIR):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))
            
for root, dirs, files in os.walk(BACKEND_DIR):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))

print("Utils import fix completed.")
