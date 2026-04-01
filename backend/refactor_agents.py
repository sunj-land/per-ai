import os
import shutil

AGENTS_DIR = "/Users/sunjie/Documents/AI/perAll/agents"
GRAPHS_DIR = os.path.join(AGENTS_DIR, "graphs")
NEW_AGENTS_DIR = os.path.join(AGENTS_DIR, "agents")

def migrate_agent(agent_file):
    base_name = os.path.basename(agent_file).replace('.py', '')
    if base_name == '__init__':
        return

    target_dir = os.path.join(NEW_AGENTS_DIR, base_name)
    os.makedirs(target_dir, exist_ok=True)

    # 移动为 graph.py
    target_graph = os.path.join(target_dir, 'graph.py')
    shutil.move(agent_file, target_graph)

    # 创建 __init__.py 暴露 graph 对象
    init_content = f"""from .graph import *
"""
    with open(os.path.join(target_dir, '__init__.py'), 'w') as f:
        f.write(init_content)

    # 创建空的 tools.py 和 prompt.py
    with open(os.path.join(target_dir, 'tools.py'), 'w') as f:
        f.write("# Tools for " + base_name + "\n")

    with open(os.path.join(target_dir, 'prompt.py'), 'w') as f:
        f.write("# Prompts for " + base_name + "\n")

if os.path.exists(GRAPHS_DIR):
    for f in os.listdir(GRAPHS_DIR):
        if f.endswith('.py'):
            migrate_agent(os.path.join(GRAPHS_DIR, f))

print("Agent migration completed.")
