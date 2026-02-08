# src/37-Multiple-Agents-Orchestrator/lg_utility.py
import os
from langgraph.graph import MessagesState
from langchain_core.runnables.graph_mermaid import MermaidDrawMethod

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