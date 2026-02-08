from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict
from lg_utility import save_graph_as_png


class GitAgentState(TypedDict):
    pr_details:str
    file_list : list
    diff : str



def git_read_agent_state_init_node(state: GitAgentState ):
    print(f"[GIT] In git_agent_state_init_node -> state: {state}") 
    state['pr_details'] = None
    state['file_list'] = []
    state['diff'] = None
    return state

def git_read_agent_node(state: GitAgentState ):
    print(f"[GIT] In git_read_agent_node -> state: {state}")
    state['file_list'] = ["a.py", "b.py"]
    state['diff'] = "hello world"
    return state

def git_connection_mcp_agent_node(state: GitAgentState ):
    print(f"[GIT] In git_connection_mcp_agent_node -> state: {state}")
    return state

def git_fetch_pr_agent_node(state: GitAgentState ):
    print(f"[GIT] In git_fetch_pr_agent_node -> state: {state}")
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
    git_read_graph.add_node("GIT_READ", git_read_agent_node)
    git_read_graph.add_node("CONNECT_MCP", git_connection_mcp_agent_node)
    git_read_graph.add_node("FETCH_PR", git_fetch_pr_agent_node)
    git_read_graph.add_node("FETCH_FILES", git_fetch_file_agent_node)
    git_read_graph.add_node("EXTRACT_DIFFS", git_fetch_file_diffs_agent_node)

    git_read_graph.add_edge(START, "GIT_READ_INIT")
    git_read_graph.add_edge("GIT_READ_INIT", "GIT_READ")
    git_read_graph.add_edge("GIT_READ", "CONNECT_MCP")
    git_read_graph.add_edge("CONNECT_MCP", "FETCH_PR")
    git_read_graph.add_edge("FETCH_PR", "FETCH_FILES")
    git_read_graph.add_edge("FETCH_FILES", "EXTRACT_DIFFS")
    git_read_graph.add_edge("EXTRACT_DIFFS", END)

    graph = git_read_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph

git_read_graph = graph_Builder()  

def main():
    #quotation = graph_Builder()   
    data = {'pr_details' : 'https://github.com/promptlyaig/issue-tracker/pull/1'}
    git_read_graph.invoke(data)

if __name__ == "__main__":
    main()

