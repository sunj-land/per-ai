import os
import re

AGENTS_DIR = "/Users/sunjie/Documents/AI/perAll/agents"
BACKEND_DIR = "/Users/sunjie/Documents/AI/perAll/backend"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original_content = content
    
    # 修复 agents.graph 导入
    content = re.sub(r'from agents\.graph\.runtime import', r'from agents.core.manager import', content)
    content = re.sub(r'from agents\.graph\.app import', r'from agents.core.app import', content)
    content = re.sub(r'from agents\.graph import', r'from agents.core import', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed graph import: {filepath}")

for root, dirs, files in os.walk(AGENTS_DIR):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))
            
for root, dirs, files in os.walk(BACKEND_DIR):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))

print("Graph import fix completed.")
