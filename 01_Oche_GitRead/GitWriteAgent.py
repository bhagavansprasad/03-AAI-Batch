from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict,Optional,Dict,Any
from lg_utility import save_graph_as_png


class GitAgentState(TypedDict):
    owner:str
    repo:str
    pull_number :int
    bugs :list
    jira_client : str
    tickets_created :str
    git_read_result : Optional[Dict[str, Any]]
    llm_review_result : Optional[Dict[str, Any]]
    jira_ticket_details : Optional[Dict[str, Any]]
    diff : Optional[Dict[str, Any]]
    test_suggetions : Optional[Dict[str, Any]]

def git_Write_init_node(state: GitAgentState ):
    print ("in git_write_init_node")
    print(f"state :{state}")
    state['owner'] = None
    state['repo'] = None
    state['bugs'] = []
    state['pull_number'] = 0
    state['git_read_result'] = {}
    state['llm_review_result'] = {}
    state['jira_ticket_details'] = {}
    state['diff'] = {}
    state['test_suggetions'] = {}
    return state


def git_Write_agent_node(state: GitAgentState ):
    print(f"[GIT WRITE] In git_Write_agent_node -> state: {state}") 


def git_post_comment_agent_node(state: GitAgentState ):
    print(f"[GIT WRITE] In git_post_comment_agent_node -> state: {state}") 

def git_commit_test_agent_node(state: GitAgentState ):
    print(f"[GIT WRITE] In git_commit_test_agent_node -> state: {state}") 


def git_tag_pr_agent_node(state: GitAgentState ):
    print(f"[GIT WRITE] In git_tag_pr_agent_node -> state: {state}") 


def graph_Builder():
    git_Write_graph = StateGraph(GitAgentState)

    git_Write_graph.add_node("GIT_INIT", git_Write_init_node)
    git_Write_graph.add_node("GIT_WRITE", git_Write_agent_node)
    git_Write_graph.add_node("POST_COMMENTS", git_post_comment_agent_node)
    git_Write_graph.add_node("COMMIT_TESTS", git_commit_test_agent_node)
    git_Write_graph.add_node("TAG_PR", git_tag_pr_agent_node)

    git_Write_graph.add_edge(START, "GIT_INIT")
    git_Write_graph.add_edge("GIT_INIT", "GIT_WRITE")
    git_Write_graph.add_edge("GIT_WRITE", "POST_COMMENTS")
    git_Write_graph.add_edge("POST_COMMENTS", "COMMIT_TESTS")
    git_Write_graph.add_edge("COMMIT_TESTS", "TAG_PR")
    git_Write_graph.add_edge("TAG_PR", END)

    graph = git_Write_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph

git_Write_graph = graph_Builder()  

def main():
    #quotation = graph_Builder()   
    data = {'data' : 'vikas'}
    git_Write_graph.invoke(data)

if __name__ == "__main__":
    main()

