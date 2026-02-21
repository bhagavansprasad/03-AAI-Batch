from langgraph.graph import START, END, StateGraph
from typing import Union, TypedDict
from lg_utility import save_graph_as_png
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, NodeTimer
)

AGENT = "JIRA"

class JiraAgentState(TypedDict):
    pr_details:  str
    bugs:        list
    jira_client: str
    jira_tickets: list


# ─── NODE 1 ──────────────────────────────────────────────────────────────────
def jira_init_agent_node(state: JiraAgentState):
    log_node_enter(AGENT, "JIRA_INIT", "reset ticket list")

    state['jira_tickets'] = []

    bugs = state.get("bugs", [])
    log_step(AGENT, f"Input: pr_details={state.get('pr_details', 'N/A')}")
    log_step(AGENT, f"Input: {len(bugs)} bug(s) received")
    for i, b in enumerate(bugs, 1):
        log_step(AGENT, f"  Bug {i}: {b}")

    log_node_exit(AGENT, "JIRA_INIT")
    return state


# ─── NODE 2 ──────────────────────────────────────────────────────────────────
def jira_Ticket_agent_node(state: JiraAgentState):
    log_node_enter(AGENT, "JIRA_TICKETS", "prepare ticket payloads")

    bugs = state.get("bugs", [])
    log_step(AGENT, f"Will create tickets for {len(bugs)} bug(s)")

    if not bugs:
        log_warn(AGENT, "Bug list is empty — no tickets will be created")

    log_node_exit(AGENT, "JIRA_TICKETS")
    return state


# ─── NODE 3 ──────────────────────────────────────────────────────────────────
def jira_connect_agent_node(state: JiraAgentState):
    log_node_enter(AGENT, "CONNECT_JIRA", "establish Jira connection")

    jira_url = "https://your-org.atlassian.net"   # replace with env var
    log_step(AGENT, f"Connecting to Jira at: {jira_url}")
    log_step(AGENT, "Auth: using API token from env (JIRA_API_TOKEN)")

    # TODO: real connection logic here
    log_ok(AGENT, "Jira connection established (placeholder)")

    log_node_exit(AGENT, "CONNECT_JIRA")
    return state


# ─── NODE 4 ──────────────────────────────────────────────────────────────────
def jira_create_tickets_agent_node(state: JiraAgentState):
    log_node_enter(AGENT, "CREATE_TICKETS", "post tickets to Jira")

    bugs = state.get("bugs", [])
    log_step(AGENT, f"Creating {len(bugs)} ticket(s) …")

    # Placeholder tickets
    tickets = ["http/Jira/111", "http/Jira/222", "http/Jira/333"]
    state['jira_tickets'] = tickets

    for i, (bug, ticket) in enumerate(zip(bugs, tickets), 1):
        log_step(AGENT, f"  Ticket {i}: {ticket}  ←  {bug}")

    if len(tickets) < len(bugs):
        log_warn(AGENT, f"Only {len(tickets)} ticket(s) created for {len(bugs)} bug(s)")

    log_ok(AGENT, f"{len(tickets)} Jira ticket(s) created")

    log_state(AGENT, {
        "pr_details":   state.get("pr_details"),
        "bugs_in":      bugs,
        "jira_tickets": tickets,
    }, label="JIRA final state")

    log_node_exit(AGENT, "CREATE_TICKETS")
    return state


# ─── Graph ───────────────────────────────────────────────────────────────────
def graph_Builder():
    jira_Ticket_graph = StateGraph(JiraAgentState)

    jira_Ticket_graph.add_node("JIRA_INIT",      jira_init_agent_node)
    jira_Ticket_graph.add_node("JIRA_TICKETS",   jira_Ticket_agent_node)
    jira_Ticket_graph.add_node("CONNECT_JIRA",   jira_connect_agent_node)
    jira_Ticket_graph.add_node("CREATE_TICKETS", jira_create_tickets_agent_node)

    jira_Ticket_graph.add_edge(START,            "JIRA_INIT")
    jira_Ticket_graph.add_edge("JIRA_INIT",      "JIRA_TICKETS")
    jira_Ticket_graph.add_edge("JIRA_TICKETS",   "CONNECT_JIRA")
    jira_Ticket_graph.add_edge("CONNECT_JIRA",   "CREATE_TICKETS")
    jira_Ticket_graph.add_edge("CREATE_TICKETS", END)

    graph = jira_Ticket_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph


jira_Ticket_graph = graph_Builder()


def main():
    data = {
        'pr_details': 'https://github.com/promptlyaig/issue-tracker/pull/1',
        'bugs': ['bug1', 'bug2', 'Bug3'],
    }
    jira_Ticket_graph.invoke(data)

if __name__ == "__main__":
    main()
