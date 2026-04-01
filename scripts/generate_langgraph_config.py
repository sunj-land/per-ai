import os
import json
import ast

# Config
ENTRIES_DIR = "agents/entries"
LANGGRAPH_JSON = "agents/langgraph.json"

def find_agent_files():
    # Recursively find *_agent.py in agents/
    files = []
    for root, _, filenames in os.walk("agents"):
        # Skip entries directory to avoid recursion or finding generated files if named *_agent_entry.py
        if "entries" in root:
            continue
            
        for filename in filenames:
            if filename.endswith("_agent.py"):
                files.append(os.path.join(root, filename))
    return files

def parse_agent_file(filepath):
    """Parse python file to find Agent class name and dependencies."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    tree = ast.parse(content)
    class_name = None
    dependencies = []
    
    # Try to find class matching filename convention
    filename = os.path.basename(filepath).replace("_agent.py", "")
    expected_name = "".join(x.title() for x in filename.split("_")) + "Agent"
    
    found_classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            found_classes.append(node)
            if node.name == expected_name:
                class_name = node.name
                break
    
    # Fallback: find any class ending with Agent
    if not class_name:
        for node in found_classes:
            if node.name.endswith("Agent") and node.name != "Agent": # Exclude base class if imported
                class_name = node.name
                break
                
    if class_name:
        # Check dependencies in the found class
        for node in found_classes:
            if node.name == class_name:
                 for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "DEPENDENCIES":
                                if isinstance(item.value, ast.List):
                                    for elt in item.value.elts:
                                        if isinstance(elt, ast.Constant):
                                            dependencies.append(elt.value)
                                        elif isinstance(elt, ast.Str): # Python < 3.8
                                            dependencies.append(elt.s)
                
    return class_name, dependencies

def generate_wrapper(filepath, class_name, entry_name):
    """Generate wrapper file in agents/entries/."""
    # Calculate relative import path
    # agents/instances/text_agent.py -> agents.instances.text_agent
    module_path = filepath.replace("/", ".").replace(".py", "")
    
    content = f"""# Auto-generated wrapper for {class_name}
from {module_path} import {class_name}

# Instantiate the agent
try:
    agent = {class_name}()
    # Expose the compiled graph
    graph = agent.workflow
except Exception as e:
    print(f"Failed to instantiate {class_name}: {{e}}")
    raise
"""
    entry_file = os.path.join(ENTRIES_DIR, f"{entry_name}.py")
    with open(entry_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated wrapper: {entry_file}")
    return f"agents.entries.{entry_name}:graph"

def update_langgraph_json(new_graphs):
    """Update langgraph.json with new graphs."""
    if os.path.exists(LANGGRAPH_JSON):
        with open(LANGGRAPH_JSON, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {"graphs": {}}
    else:
        data = {"graphs": {}}
    
    if "graphs" not in data:
        data["graphs"] = {}
        
    # Merge new graphs
    data["graphs"].update(new_graphs)
    
    # Write back with sorted keys
    with open(LANGGRAPH_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(f"Updated {LANGGRAPH_JSON}")

def main():
    files = find_agent_files()
    print(f"Found {len(files)} agent files.")
    
    new_graphs = {}
    
    for filepath in files:
        print(f"Processing {filepath}...")
        try:
            class_name, dependencies = parse_agent_file(filepath)
            if not class_name:
                print(f"Skipping {filepath}: No Agent class found.")
                continue
                
            # Entry name: text_agent -> text_agent_entry
            base_name = os.path.basename(filepath).replace(".py", "")
            entry_name = f"{base_name}_entry"
            
            entrypoint = generate_wrapper(filepath, class_name, entry_name)
            
            # Use base_name (e.g., text_agent) as graph key
            new_graphs[base_name] = entrypoint
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            
    update_langgraph_json(new_graphs)

if __name__ == "__main__":
    main()
