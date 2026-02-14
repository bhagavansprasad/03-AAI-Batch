from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict, Optional, Any, List, Dict
from lg_utility import save_graph_as_png
import os
from fastmcp import Client
import asyncio
from urllib.parse import urlparse
import re
import json
from lg_utility import pretty_print_json_list

class GitAgentState(TypedDict):
    pr_details:str
    owner: str
    repo: str
    pull_number: int
    changed_files : list
    diffs : str
    has_valid_files: bool
    client: Optional[Any]

async def call_mcp_tool(client, tool_name: str, arguments: dict = None) -> dict:
    """Helper to call MCP tools"""
    result = await client.call_tool(tool_name, arguments)
    content_text = result.content[0].text

    return json.loads(content_text) if content_text else {}

def parse_github_pr_url(url: str):
    print(url)
    parsed = urlparse(url.strip().rstrip("/"))

    if parsed.netloc.lower() != "github.com":
        raise ValueError("Not a GitHub URL")

    parts = parsed.path.strip("/").split("/")

    if len(parts) < 4 or parts[2] != "pull":
        raise ValueError("Not a GitHub Pull Request URL")

    owner = parts[0]
    repo = parts[1]

    # Extract numeric PR number safely
    match = re.match(r"\d+", parts[3])
    if not match:
        raise ValueError("Invalid pull request number")

    pull_number = int(match.group())

    return owner, repo, pull_number

def git_read_agent_state_init_node(state: GitAgentState ):
    print(f"[GIT] In git_agent_state_init_node -> state: {state}") 
    state['owner'] = None
    state['repo'] = None
    state['pull_number'] = 0
    state['changed_files'] = []
    state['diffs'] = None
    state['has_valid_files'] = False    
    state['client'] = None   

    owner, repo, pull_number = parse_github_pr_url(state["pr_details"])

    state['owner'] = owner
    state['repo'] = repo
    state['pull_number'] = pull_number
    
    return state

async def git_connection_mcp_agent_node(state: GitAgentState):
    print(f"[GIT] In git_connection_mcp_agent_node -> state: {state}")

    GITHUB_MCP_SERVER_URL = os.getenv("GITHUB_MCP_SERVER_URL")
    client = Client(GITHUB_MCP_SERVER_URL)

    await client.__aenter__()
    
    state["client"] = client
    
    print(f"✅ Connected to MCP")
    
    return state

async def git_fetch_pr_agent_node(state: GitAgentState ):
    print(f"[GIT] In git_fetch_pr_agent_node -> state: {state}")

    client = state['client']

    tool_name = "GITHUB_LIST_PULL_REQUESTS_FILES"
    args = {
        "owner": state["owner"],
        "repo": state["repo"],
        "pull_number": state["pull_number"]
    }
    print("@" * 30)
    print (f"==========Args :{args}============")
    
    response = await call_mcp_tool(state['client'], tool_name, args)
    
    # Extract file details
    files = response["data"]["details"]
    
    state["changed_files"] = []
    for file in files:
        state["changed_files"].append({
            "filename": file["filename"],
            "status": file["status"],
            "additions": file["additions"],
            "deletions": file["deletions"],
            "changes": file["changes"],
            "patch": file.get("patch", "")
        })
    
    print(f"✅ Found {len(state['changed_files'])} changed files")
    # pretty_print_json_list(state['changed_files'])
    print("@" * 30)
    
    return state

async def extract_diffs_node(state: GitAgentState) -> GitAgentState:
    """Extract and structure diff data from changed files"""
    print(f"\n[NODE 3] Extracting and structuring diffs...")

    state["diffs"] = []
    
    for file in state["changed_files"]:
        # Only process files with patches (ignore deleted/binary files)
        if not file.get("patch"):
            continue
        
        # Detect language from file extension
        filename = file["filename"]
        ext = filename.split(".")[-1] if "." in filename else "unknown"
        
        structured_diff = {
            "filename": filename,
            "status": file["status"],
            "language": ext,
            "additions": file["additions"],
            "deletions": file["deletions"],
            "patch": file["patch"]  # Full diff for LLM review
        }
        
        state["diffs"].append(structured_diff)
    
    # Set flag for routing
    state["has_valid_files"] = len(state["diffs"]) > 0
    
    print(f"✅ Extracted {len(state['diffs'])} structured diffs")
    
    return state

def graph_Builder():
    git_read_graph = StateGraph(GitAgentState)

    git_read_graph.add_node("GIT_READ_INIT", git_read_agent_state_init_node)
    git_read_graph.add_node("CONNECT_MCP", git_connection_mcp_agent_node)
    git_read_graph.add_node("FETCH_PR", git_fetch_pr_agent_node)
    git_read_graph.add_node("EXTRACT_DIFFS", extract_diffs_node)

    git_read_graph.add_edge(START, "GIT_READ_INIT")
    git_read_graph.add_edge("GIT_READ_INIT", "CONNECT_MCP")
    git_read_graph.add_edge("CONNECT_MCP", "FETCH_PR")
    git_read_graph.add_edge("FETCH_PR", "EXTRACT_DIFFS")
    git_read_graph.add_edge("EXTRACT_DIFFS", END)

    graph = git_read_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph

git_read_graph = graph_Builder()  

async def main():
    data = {'pr_details' : 'https://github.com/promptlyaig/issue-tracker/pull/1'}
    await git_read_graph.ainvoke(data)

if __name__ == "__main__":
    asyncio.run(main())

