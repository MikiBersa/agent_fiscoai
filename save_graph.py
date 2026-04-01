import os
import sys
import asyncio

# Ensure project root is in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import the workflow
try:
    from src.graph.think.todo import todo_workflow
    
    # Generate the PNG bytes
    # Note: This requires pyppeteer or a similar library to be installed and working.
    png_bytes = todo_workflow.get_graph(xray=True).draw_mermaid_png()
    
    # Save to file
    output_path = os.path.join(root_dir, "todo_workflow.png")
    with open(output_path, "wb") as f:
        f.write(png_bytes)
    
    print(f"Success: Graph saved to {output_path}")
except Exception as e:
    print(f"Error: {e}")
    # If PNG fails, try to at least get the mermaid text
    try:
        mermaid_text = todo_workflow.get_graph(xray=True).draw_mermaid()
        print("Mermaid text generated as fallback:")
        print(mermaid_text)
    except:
        pass
