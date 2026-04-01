import os
import ast
from collections import defaultdict
import shutil
import datetime

AGENTS_DIR = "/Users/sunjie/Documents/AI/perAll/agents"
BACKUP_DIR = "/Users/sunjie/Documents/AI/perAll/.agents_backup_" + datetime.datetime.now().strftime("%Y%m%d")

def get_python_files(directory):
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith('.py') and not f.startswith('test_'):
                files.append(os.path.join(root, f))
    return files

def analyze_imports(files):
    imports = defaultdict(list)
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[alias.name].append(file)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports[node.module].append(file)
        except Exception:
            pass
    return imports

def calculate_scores(files, imports):
    scores = {}
    for f in files:
        score = 50 # Base score (business value proxy)

        rel_path = os.path.relpath(f, AGENTS_DIR)
        module_name = "agents." + rel_path.replace('/', '.').replace('.py', '')
        if module_name.endswith('.__init__'):
            module_name = module_name[:-9]

        inbound = 0
        for imp, paths in imports.items():
            if imp == module_name or imp.startswith(module_name + "."):
                inbound += len(paths) * 10
        score += inbound

        if 'core/' in rel_path or 'api/' in rel_path or 'graph/' in rel_path:
            score += 30
        if 'tests/' in rel_path:
            score += 20

        if rel_path in ['main.py', '__init__.py']:
            score += 50

        scores[f] = score
    return scores

def main():
    files = get_python_files(AGENTS_DIR)
    imports = analyze_imports(files)
    scores = calculate_scores(files, imports)

    threshold = 60
    to_delete = []
    retained = []

    for f, score in scores.items():
        if score < threshold:
            to_delete.append((f, score))
        else:
            retained.append((f, score))

    print("=== File Importance Scores ===")
    for f, s in sorted(scores.items(), key=lambda x: x[1]):
        print(f"{os.path.relpath(f, AGENTS_DIR)}: {s}")

    print(f"\nFiles below threshold ({threshold}):")
    for f, s in to_delete:
        print(f" - {os.path.relpath(f, AGENTS_DIR)} (Score: {s})")

    if to_delete:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        for f, _ in to_delete:
            rel_path = os.path.relpath(f, AGENTS_DIR)
            backup_path = os.path.join(BACKUP_DIR, rel_path)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(f, backup_path)
            os.remove(f)
        print(f"\nMoved {len(to_delete)} files to {BACKUP_DIR}")

if __name__ == '__main__':
    main()
