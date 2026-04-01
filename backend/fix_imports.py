import os
import re

AGENTS_DIR = "/Users/sunjie/Documents/AI/perAll/agents"
BACKEND_DIR = "/Users/sunjie/Documents/AI/perAll/backend"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original_content = content
    
    # 1. tools -> agents.tools
    content = re.sub(r'from agents\.core\.tools(\.[a-zA-Z0-9_]+)? import', r'from agents.tools\1 import', content)
    content = re.sub(r'import agents\.core\.tools(\.[a-zA-Z0-9_]+)?', r'import agents.tools\1', content)
    
    # 2. utils -> agents.utils
    content = re.sub(r'from agents\.core\.utils(\.[a-zA-Z0-9_]+)? import', r'from agents.utils\1 import', content)
    content = re.sub(r'import agents\.core\.utils(\.[a-zA-Z0-9_]+)?', r'import agents.utils\1', content)
    content = re.sub(r'from agents\.core\.utils import', r'from agents.utils.utils import', content)
    
    # 3. state -> agents.core.state
    content = re.sub(r'from agents\.graph\.state import', r'from agents.core.state import', content)
    
    # 4. instances -> agents.agents
    content = re.sub(r'from agents\.instances\.([a-zA-Z0-9_]+) import', r'from agents.agents.\1 import', content)
    content = re.sub(r'import agents\.instances\.([a-zA-Z0-9_]+)', r'import agents.agents.\1', content)
    
    # 5. core/tools/registry.py -> core/registry.py (特殊情况处理，如果是直接import registry)
    content = re.sub(r'from agents\.tools\.registry import', r'from agents.core.registry import', content)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {filepath}")

for root, dirs, files in os.walk(AGENTS_DIR):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))
            
for root, dirs, files in os.walk(BACKEND_DIR):
    for f in files:
        if f.endswith('.py'):
            process_file(os.path.join(root, f))

print("Import fix completed.")
