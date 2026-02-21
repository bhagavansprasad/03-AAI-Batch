import os
import re
import asyncio
from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from fastmcp import Client
from lg_utility import save_graph_as_png
from jira_utilities import (
    build_jira_ticket_summary,
    build_jira_ticket_description,
    get_jira_priority,
)
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, NodeTimer
)

AGENT = "JIRA"

# ============================================================================
# STATE
# ============================================================================

class JiraAgentState(TypedDict):
    # ── inputs (from LLM Review Agent via Orchestrator) ───────────────────────
    owner:       str
    repo:        str
    pull_number: int
    bugs:        List[Dict[str, Any]]   # bug dicts from LLM agent

    # ── outputs ───────────────────────────────────────────────────────────────
    tickets_created: Optional[List[Dict[str, Any]]]  # created ticket details

    # ── internal ──────────────────────────────────────────────────────────────
    jira_client: Optional[Any]


# ============================================================================
# NODES
# ============================================================================

# ─── NODE 1 — init ───────────────────────────────────────────────────────────
async def jira_init_agent_node(state: JiraAgentState) -> JiraAgentState:
    log_node_enter(AGENT, "JIRA_INIT", "reset outputs, log incoming bugs")

    state["tickets_created"] = []
    state["jira_client"]     = None

    bugs = state.get("bugs", [])
    log_step(AGENT, f"Owner      : {state.get('owner')}")
    log_step(AGENT, f"Repo       : {state.get('repo')}")
    log_step(AGENT, f"PR#        : {state.get('pull_number')}")
    log_step(AGENT, f"Bugs in    : {len(bugs)}")
    for i, bug in enumerate(bugs, 1):
        sev  = bug.get('severity', '?').upper()
        btype = bug.get('type', '?')
        desc = bug.get('description', '')[:70]
        log_step(AGENT, f"  Bug {i}: [{sev}] {btype} — {desc}")

    log_node_exit(AGENT, "JIRA_INIT")
    return state


# ─── NODE 2 — connect MCP ────────────────────────────────────────────────────
async def jira_connect_mcp_node(state: JiraAgentState) -> JiraAgentState:
    log_node_enter(AGENT, "CONNECT_MCP", "open FastMCP client to Jira server")

    jira_url = os.getenv("JIRA_MCP_SERVER_URL", "http://127.0.0.1:3333/mcp")
    log_step(AGENT, f"JIRA_MCP_SERVER_URL = {jira_url}")

    try:
        client = Client(jira_url)
        await client.__aenter__()
        state["jira_client"] = client
        log_ok(AGENT, "Jira MCP client connected successfully")
    except Exception as e:
        log_error(AGENT, f"Failed to connect to Jira MCP: {e}")
        state["jira_client"] = None

    log_node_exit(AGENT, "CONNECT_MCP")
    return state


# ─── ROUTER — after CONNECT_MCP ──────────────────────────────────────────────
def should_create_tickets(state: JiraAgentState) -> str:
    """Route to CREATE_TICKETS or skip to END."""
    if not state.get("jira_client"):
        log_warn(AGENT, "Router: no Jira client — routing to SKIP")
        return "SKIP"
    if not state.get("bugs"):
        log_warn(AGENT, "Router: no bugs — routing to SKIP")
        return "SKIP"
    log_step(AGENT, f"Router: {len(state['bugs'])} bug(s) + live client — routing to CREATE")
    return "CREATE"


# ─── NODE 3 — create tickets ─────────────────────────────────────────────────
async def jira_create_tickets_node(state: JiraAgentState) -> JiraAgentState:
    log_node_enter(AGENT, "CREATE_TICKETS", "post one Jira ticket per bug via MCP")

    client      = state["jira_client"]
    bugs        = state.get("bugs", [])
    project_key = os.getenv("JIRA_PROJECT_KEY", "PROM")
    base_url    = os.getenv("JIRA_BASE_URL", "https://promptlyai.atlassian.net")

    log_step(AGENT, f"Jira project : {project_key}")
    log_step(AGENT, f"Jira base URL: {base_url}")
    log_step(AGENT, f"Bugs to process: {len(bugs)}")

    state["tickets_created"] = []

    for i, bug in enumerate(bugs, 1):
        btype = bug.get('type', 'unknown')
        sev   = bug.get('severity', 'medium')
        log_step(AGENT, f"  [{i}/{len(bugs)}] Creating ticket — type={btype}  severity={sev}")

        summary     = build_jira_ticket_summary(bug)
        description = build_jira_ticket_description(
            bug, state["owner"], state["repo"], state["pull_number"]
        )
        priority    = get_jira_priority(sev)

        log_step(AGENT, f"    summary  : {summary[:80]}")
        log_step(AGENT, f"    priority : {priority}")

        params = {
            "project_key": project_key,
            "summary":     summary,
            "description": description,
            "issuetype":   "Bug",
            "priority":    priority,
        }

        try:
            result        = await client.call_tool("CREATE_ISSUE", params)
            response_text = result.content[0].text
            log_step(AGENT, f"    Raw MCP response: {response_text[:200]}")

            ticket_match = re.search(r'([A-Z]+-\d+)', response_text)
            if ticket_match:
                ticket_key = ticket_match.group(1)
                ticket_url = f"{base_url}/browse/{ticket_key}"
                state["tickets_created"].append({
                    "bug_type":   btype,
                    "ticket_key": ticket_key,
                    "ticket_url": ticket_url,
                    "severity":   sev,
                })
                log_ok(AGENT, f"    Ticket created: {ticket_key}  →  {ticket_url}")
            else:
                log_warn(AGENT, f"    No ticket key found in response — skipping bug {i}")

        except Exception as e:
            log_error(AGENT, f"    MCP call failed for bug {i}: {e}")

    # ── summary ──────────────────────────────────────────────────────────────
    created = state["tickets_created"]
    log_ok(AGENT, f"{len(created)}/{len(bugs)} ticket(s) created successfully")

    if created:
        log_step(AGENT, "Ticket summary:")
        for t in created:
            log_step(AGENT, f"  {t['ticket_key']}  [{t['severity'].upper()}]  {t['bug_type']}")
            log_step(AGENT, f"    {t['ticket_url']}")

    log_state(AGENT, {
        "bugs_in":         len(bugs),
        "tickets_created": len(created),
        "ticket_keys":     [t["ticket_key"] for t in created],
    }, label="JIRA final state")

    log_node_exit(AGENT, "CREATE_TICKETS")
    return state


# ============================================================================
# GRAPH
# ============================================================================

def graph_Builder():
    jira_graph = StateGraph(JiraAgentState)

    jira_graph.add_node("JIRA_INIT",       jira_init_agent_node)
    jira_graph.add_node("CONNECT_MCP",     jira_connect_mcp_node)
    jira_graph.add_node("CREATE_TICKETS",  jira_create_tickets_node)

    jira_graph.add_edge(START,             "JIRA_INIT")
    jira_graph.add_edge("JIRA_INIT",       "CONNECT_MCP")

    # Conditional: only create tickets if connected AND bugs exist
    jira_graph.add_conditional_edges(
        "CONNECT_MCP",
        should_create_tickets,
        {
            "CREATE": "CREATE_TICKETS",
            "SKIP":   END,
        }
    )

    jira_graph.add_edge("CREATE_TICKETS", END)

    graph = jira_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph


jira_Ticket_graph = graph_Builder()


# ============================================================================
# MAIN — standalone test
# ============================================================================

async def _test():
    test_state = JiraAgentState(
        owner="promptlyaig",
        repo="issue-tracker",
        pull_number=1,
        bugs=[
            {
                "severity":    "high",
                "type":        "index_error",
                "description": "List index out of range in process_items()",
                "location":    "utils.py:42",
                "suggestion":  "Add bounds check before accessing list index",
            },
            {
                "severity":    "medium",
                "type":        "null_dereference",
                "description": "Potential None access on user.profile",
                "location":    "models.py:87",
                "suggestion":  "Add None guard before accessing .profile",
            },
        ]
    )

    result = await jira_Ticket_graph.ainvoke(test_state)

    print("\n" + "=" * 60)
    print("JIRA AGENT TEST COMPLETE")
    print("=" * 60)
    print(f"Tickets created: {len(result.get('tickets_created', []))}")
    for t in result.get("tickets_created", []):
        print(f"  {t['ticket_key']}  {t['ticket_url']}")
    print("=" * 60)


def main():
    asyncio.run(_test())

if __name__ == "__main__":
    main()
