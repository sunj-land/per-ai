import os
import json

agents_dir = "/Users/sunjie/Documents/AI/perAll/agents/agents"
graphs_dict = {}
entries_lines = []

for agent_name in os.listdir(agents_dir):
    agent_path = os.path.join(agents_dir, agent_name)
    if os.path.isdir(agent_path) and agent_name != "__pycache__":
        graph_file = os.path.join(agent_path, "graph.py")
        if os.path.exists(graph_file):
            class_name = None
            with open(graph_file, 'r') as f:
                for line in f:
                    if line.startswith("class ") and "(Agent):" in line:
                        class_name = line.split("class ")[1].split("(")[0].strip()
                        break
            if class_name:
                # Add to entries
                entries_lines.append(f"from agents.{agent_name}.graph import {class_name}")
                entries_lines.append(f"{agent_name}_graph = {class_name}().workflow\n")
                # Point langgraph.json to the instantiated graph
                graphs_dict[agent_name] = f"agents.entries:{agent_name}_graph"

# Write entries.py
entries_path = os.path.join(agents_dir, "entries.py")
with open(entries_path, 'w') as f:
    f.write("\n".join(entries_lines))

# Update langgraph.json
json_path = "/Users/sunjie/Documents/AI/perAll/agents/langgraph.json"
with open(json_path, 'r') as f:
    data = json.load(f)

data["graphs"] = graphs_dict
# Important: ensure dependencies allows execution from perAll root or correctly resolves.
# In local dev, langgraph dev sets sys.path[0] to the folder of langgraph.json if dependencies is "."
# We'll keep it as "." but the graphs path is "agents.agents..." which works if run from perAll.
data["dependencies"] = [".", ".."]

with open(json_path, 'w') as f:
    json.dump(data, f, indent=2)

print("entries.py and langgraph.json updated successfully.")
