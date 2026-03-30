import os
import sys

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.graph.think.todo import todo_workflow

def get_mermaid():
    try:
        mermaid_graph = todo_workflow.get_graph(xray=True).draw_mermaid()
        print(mermaid_graph)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    get_mermaid()
