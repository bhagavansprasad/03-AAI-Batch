from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict, Optional, Any
from lg_utility import save_graph_as_png
import os
from fastmcp import Client
import asyncio


class GitAgentState(TypedDict):
    pr_details:str
    file_list : list
    diff : str
    client: Optional[Any]


def git_read_agent_state_init_node(state: GitAgentState ):
    print(f"[GIT] In git_agent_state_init_node -> state: {state}") 
    state['pr_details'] = None
    state['file_list'] = []
    state['diff'] = None
    state['client'] = None   
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
    tools = await client.list_tools()
    print("Available tools:")
    
    for i, t in enumerate(tools, 1):
        print(f"{i}. {t.name}")
        print(f"{t.description or '(no description)'}\n")

    print("Tool Descriptions\n")
    for tool in tools:
        print(f"{tool.model_dump_json(indent=4)}")

    return state

def git_fetch_file_agent_node(state: GitAgentState ):
    print(f"[GIT] In git_fetch_file_agent_node -> state: {state}")
    return state


def git_fetch_file_diffs_agent_node(state: GitAgentState ):
    print(f"[GIT] git_fetch_file_diffs_agent_node -> state: {state}")
    return state


def graph_Builder():
    git_read_graph = StateGraph(GitAgentState)

    git_read_graph.add_node("GIT_READ_INIT", git_read_agent_state_init_node)
    git_read_graph.add_node("CONNECT_MCP", git_connection_mcp_agent_node)
    git_read_graph.add_node("FETCH_PR", git_fetch_pr_agent_node)
    git_read_graph.add_node("FETCH_FILES", git_fetch_file_agent_node)
    git_read_graph.add_node("EXTRACT_DIFFS", git_fetch_file_diffs_agent_node)

    git_read_graph.add_edge(START, "GIT_READ_INIT")
    git_read_graph.add_edge("GIT_READ_INIT", "CONNECT_MCP")
    git_read_graph.add_edge("CONNECT_MCP", "FETCH_PR")
    git_read_graph.add_edge("FETCH_PR", "FETCH_FILES")
    git_read_graph.add_edge("FETCH_FILES", "EXTRACT_DIFFS")
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

