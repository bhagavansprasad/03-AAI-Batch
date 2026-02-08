from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict,Optional,Dict,Any
from lg_utility import save_graph_as_png
import json


class LLMReviewAgentState(TypedDict):
    file_list:list
    difference:str
    comments:str
    bugs : list
    test_suggetions : list
    # owner: str
    # repo: str
    # bugs :str
    # pull_number: int
    # git_read_result : Optional[Dict[str, Any]]
    # llm_review_result : Optional[Dict[str, Any]]
    # jira_ticket_details : Optional[Dict[str, Any]]
    # diff : Optional[Dict[str, Any]]
    # jira_ticket : list
    #comments : list

    #git_write_result : bool

def llm_review_analyze_init_node(state: LLMReviewAgentState ):
    print ("in llm_init_node")
    print(f"state :{state}")
    state['bugs'] = []
    # state['pull_number'] = 0
    # state['git_read_result'] = {}
    # state['llm_review_result'] = {}
    # state['jira_ticket_details'] = {}
    # state['diff'] = {}
    # state['jira_ticket'] = []  
    state['comments'] = None
    state['test_suggetions'] = []
    return state



def llm_review_analyze_code_agent_node(state: LLMReviewAgentState ):
    print(f"[LLM] In llm_review_analyze_code_agent_node -> state: {state}") 
    return state


def llm_review_genrate_review_agent_node(state: LLMReviewAgentState ):
    review_comments = "Comment1 comment2 commnet3"
    state['comments'] = review_comments
    print(f"[LLM] In llm_review_genrate_review_agent_node -> state: {state}") 
    return state

def llm_review_identify_bug_agent_node(state: LLMReviewAgentState ):
    bugs = ['bug1','bug2','bug3']
    state['bugs'] = bugs
    print(f"[LLM] In llm_review_identify_bug_agent_node -> state: {state}") 
    return state


def llm_review_suggest_test_agent_node(state: LLMReviewAgentState ):
    test_suggetions = ['test1','test2','test3']
    state['test_suggetions'] = test_suggetions
    print(f"[LLM] In llm_review_suggest_test_agent_node -> state: {state}") 
    return state


def graph_Builder():
    llm_review_graph = StateGraph(LLMReviewAgentState)

    llm_review_graph.add_node("LLM_INIT", llm_review_analyze_init_node)
    llm_review_graph.add_node("ANALYZE_CODE", llm_review_analyze_code_agent_node)
    llm_review_graph.add_node("GENERATE_REVIEW", llm_review_genrate_review_agent_node)
    llm_review_graph.add_node("IDENTIFY_BUG", llm_review_identify_bug_agent_node)
    llm_review_graph.add_node("SUGGEST_TEST", llm_review_suggest_test_agent_node)

    llm_review_graph.add_edge(START, "LLM_INIT")
    llm_review_graph.add_edge("LLM_INIT", "ANALYZE_CODE")
    llm_review_graph.add_edge("ANALYZE_CODE", "GENERATE_REVIEW")
    llm_review_graph.add_edge("GENERATE_REVIEW", "IDENTIFY_BUG")
    llm_review_graph.add_edge("IDENTIFY_BUG", "SUGGEST_TEST")
    llm_review_graph.add_edge("SUGGEST_TEST", END)

    graph = llm_review_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph

llm_review_graph = graph_Builder()  

def main():
    #quotation = graph_Builder()   
    data = {'file_list' : ['b1.py','a1.py'],'difference':"Hello word"}
    llm_review_graph.invoke(data)

if __name__ == "__main__":
    main()

