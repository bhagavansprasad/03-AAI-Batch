from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict
from lg_utility import save_graph_as_png


class JiraAgentState(TypedDict):
    pr_details:str
    bugs = list
    jira_client : str
    jira_tickets : list

def jira_init_agent_node(state: JiraAgentState ):
    print ("in jira_init_node")
    print(f"state :{state}")
    state['jira_tickets'] = []  
    return state

def jira_Ticket_agent_node(state: JiraAgentState ):
    print(f"[JIRA] In jira_Ticket_agent_node -> state: {state}") 
    return state

def jira_connect_agent_node(state: JiraAgentState ):
    print(f"[JIRA] In jira_connect_agent_node -> state: {state}") 
    return state

def jira_create_tickets_agent_node(state: JiraAgentState ):
    state['jira_tickets'] = ["http/Jira/111","http/Jira/222","http/Jira/333"]
    print(f"[JIRA] In jira_create_tickets_agent_node -> state: {state}") 
    return state



def graph_Builder():
    jira_Ticket_graph = StateGraph(JiraAgentState)

    jira_Ticket_graph.add_node("JIRA_INIT", jira_init_agent_node)
    jira_Ticket_graph.add_node("JIRA_TICKETS", jira_Ticket_agent_node)
    jira_Ticket_graph.add_node("CONNECT_JIRA", jira_connect_agent_node)
    jira_Ticket_graph.add_node("CREATE_TICKETS", jira_create_tickets_agent_node)
 

    jira_Ticket_graph.add_edge(START, "JIRA_INIT")
    jira_Ticket_graph.add_edge("JIRA_INIT", "JIRA_TICKETS")
    jira_Ticket_graph.add_edge("JIRA_TICKETS", "CONNECT_JIRA")
    jira_Ticket_graph.add_edge("CONNECT_JIRA", "CREATE_TICKETS")
    jira_Ticket_graph.add_edge("CREATE_TICKETS", END)

    graph = jira_Ticket_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph

jira_Ticket_graph = graph_Builder()  

def main():
    #quotation = graph_Builder()   
    data = {'pr_details':'https://github.com/promptlyaig/issue-tracker/pull/1','bugs':['bug1','bug2','Bug3']}
    jira_Ticket_graph.invoke(data)

if __name__ == "__main__":
    main()

