# src/37-Multiple-Agents-Orchestrator/lg_utility.py
import os
from langgraph.graph import MessagesState
from langchain_core.runnables.graph_mermaid import MermaidDrawMethod
from typing import Any, Dict, List, Union
import json

# def save_graph_as_png(graph, filename=None):
#     if filename is None:
#         filename = os.path.splitext(os.path.basename(__file__))[0]
    
#     # png_bytes = graph.get_graph().draw_mermaid_png()
#     png_bytes = graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.PYPPETEER)
#     with open(f"{filename}.png", "wb") as f:
#         f.write(png_bytes)

def save_graph_as_png(graph, filename="gsheet_agent_graph"):
    """
    Save the graph visualization as PNG
    """
    from langchain_core.runnables.graph_mermaid import MermaidDrawMethod
   
    try:
        png_bytes = graph.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.API
        )
        with open(f"{filename}.png", "wb") as f:
            f.write(png_bytes)
        print(f"\n📊 Graph saved as {filename}.png")
    except Exception as e:
        print(f"\n⚠️ Could not save graph image: {e}")
        try:
            mermaid_code = graph.get_graph().draw_mermaid()
            with open(f"{filename}_mermaid.txt", "w") as f:
                f.write(mermaid_code)
            print(f"   ✓ Saved mermaid code to {filename}_mermaid.txt")
            print(f"   Visualize at: https://mermaid.live/")
        except Exception as e2:
            print(f"   Could not save mermaid code: {e2}")

def pretty_print_json_list(data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> None:
    """
    Pretty print JSON data in a readable format.

    Accepts:
    - list of dicts
    - single dict

    Falls back to normal JSON pretty print for any other type.
    """

    def _print_item(index: int, item: Any):
        print(f"\n🔹 Object {index}")
        print(json.dumps(item, indent=4, ensure_ascii=False, default=str))

    # Case 1 → list
    if isinstance(data, list):
        for i, item in enumerate(data, start=1):
            _print_item(i, item)

    # Case 2 → single dict
    elif isinstance(data, dict):
        _print_item(1, data)

    # Case 3 → anything else (optional fallback)
    else:
        print(json.dumps(data, indent=4, ensure_ascii=False, default=str))
