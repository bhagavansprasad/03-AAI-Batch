from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict,Optional,Dict,Any
from lg_utility import save_graph_as_png
from GitReadAgent import git_read_graph
from LLMReviewAgent import llm_review_graph
from JiraTicketAgent import jira_Ticket_graph
from GitWriteAgent import git_Write_graph
import json
import asyncio


async def invoke_git_graph(pr_url:str):
    data = {'pr_details' : pr_url}
    git_return_value = await git_read_graph.ainvoke(data)
    #print(git_return_value)
    return {'file_list':git_return_value['file_list'], 'diff':git_return_value['diff']} 

def invoke_llm_graph(file_list:list,difference:str):
    data = {'file_list' : file_list,'difference':difference}
    llm_return_value = llm_review_graph.invoke(data)
    print(llm_return_value)
    file_list = llm_return_value['file_list']
    llm_bugs = llm_return_value['bugs']
    llm_comments = llm_return_value['comments']
    llm_test_suggetions = llm_return_value['test_suggetions']
    return { "file_list":file_list, 'bugs':llm_bugs,"comments":llm_comments,"test_suggetions":llm_test_suggetions}


def invoke_jira_graph(pr_details:str,bugs:list):
    data = {'pr_details':pr_details,'bugs':bugs}
    jira_Ticket_graph_value = jira_Ticket_graph.invoke(data)
    print(jira_Ticket_graph_value)
    jira_tickets = jira_Ticket_graph_value['jira_tickets']
    return jira_tickets
  

def invoke_git_agent_write_graph(jira_ticket:str,review_comments:list, unit_tests:list):
    return None



class OrchestraterData(TypedDict):
    pr_details : str
    owner: str
    repo: str
    pull_number: int
    git_read_result : Optional[Dict[str, Any]]
    bugs :list[str]
    llm_review_result : Optional[Dict[str, Any]]
    jira_ticket_details : Optional[Dict[str, Any]]
    git_write_result : bool


def orchestrator_init_node(state: OrchestraterData ):
    print ("in orchestrator_init_node")
    print(f"state :{state}")
    state['owner'] = None
    state['repo'] = None
    state['pull_number'] = 0
    state['git_read_result'] = {}
    state['llm_review_result'] = {}
    state['bugs']=[]
    state['jira_ticket_details'] = {}
    state['git_write_result'] = False
    return state

async def git_read_agent_node(state: OrchestraterData ):
    print(f"[ORCH] In git_read_agent_node -> state: {state}")
    state["git_read_result"] = await invoke_git_graph(state['pr_details'])
    return state

def llm_agent_node(state: OrchestraterData ):
    #print(f"[ORCH] In llm_agent_node -> state: {state}")
    file_list = state["git_read_result"]['file_list']
    difference = state["git_read_result"]['diff']
    state['llm_review_result']=  invoke_llm_graph(file_list,difference)
    print(f"[ORCH] Out llm_agent_node -> state: {state['llm_review_result']}")
    return state

def jira_agent_node(state: OrchestraterData ):
    #print(f"[ORCH] In Jira_agent_node -> state: {state}")
    pr_details = state['pr_details'] 
    bugs = state["llm_review_result"]['bugs']
    state['jira_ticket_details'] = invoke_jira_graph(pr_details,bugs)
    print(f"[ORCH] In Final Node Jira_agent_node -> state: {state}")
    # print(f"[ORCH] Out Jira_agent_node -> state: {state['jira_tickets']}")
    return state

def git_write_agent_node(state: OrchestraterData ):
    return state

def graph_Builder():
    Ograph = StateGraph(OrchestraterData)

    Ograph.add_node("ORCHESTRATOR_INIT", orchestrator_init_node) # sync
    Ograph.add_node("GIT_READ_AGENT", git_read_agent_node)       # async
    Ograph.add_node("LLM_REVIEW_AGENT", llm_agent_node)          # sync   
    Ograph.add_node("JIRA_AGENT", jira_agent_node)               # async
    Ograph.add_node("GIT_WRITE_AGENT", git_write_agent_node)     # async

    Ograph.add_edge(START, "ORCHESTRATOR_INIT")
    Ograph.add_edge('ORCHESTRATOR_INIT', "GIT_READ_AGENT")
    Ograph.add_edge("GIT_READ_AGENT", "LLM_REVIEW_AGENT")
    Ograph.add_edge("LLM_REVIEW_AGENT", "JIRA_AGENT")
    Ograph.add_edge("JIRA_AGENT", "GIT_WRITE_AGENT")
    Ograph.add_edge("GIT_WRITE_AGENT", END)

    graph = Ograph.compile()
    save_graph_as_png(graph, __file__)
    return graph

orchestrator_graph = graph_Builder()  

async def main():
    #quotation = graph_Builder()   
    data = {'pr_details' : 'https://github.com/promptlyaig/issue-tracker/pull/1'}
    
    final_state = await orchestrator_graph.ainvoke(data)
    
    tstr = json.dumps(final_state,  sort_keys=True, indent=4)
    print(tstr)

if __name__ == "__main__":
    asyncio.run(main())

