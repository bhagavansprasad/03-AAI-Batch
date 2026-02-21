from langgraph.graph import START, END, StateGraph
from typing import Union, TypedDict, Optional, Dict, Any
from lg_utility import save_graph_as_png
from GitReadAgent import git_read_graph
from LLMReviewAgent import llm_review_graph
from JiraTicketAgent import jira_Ticket_graph
from GitWriteAgent import git_Write_graph
import json
import asyncio
from lg_utility import pretty_print_json_list
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, log_phase, log_pipeline_start,
    log_pipeline_end, log_diff_table, NodeTimer
)

AGENT = "ORCH"

class OrchestraterData(TypedDict):
    pr_details:         str
    owner:              str
    repo:               str
    pull_number:        int
    git_read_result:    Optional[Dict[str, Any]]
    diffs:              list
    bugs:               list
    llm_review_result:  Optional[Dict[str, Any]]
    jira_ticket_details: Optional[Dict[str, Any]]
    git_write_result:   bool


# ─── Sub-graph invokers ───────────────────────────────────────────────────────

async def invoke_git_graph(pr_url: str):
    log_step(AGENT, f"Invoking GIT-READ sub-graph  →  PR: {pr_url}")
    data = {'pr_details': pr_url}
    git_return_value = await git_read_graph.ainvoke(data)

    changed = git_return_value['changed_files']
    diffs   = git_return_value['diffs']
    log_ok(AGENT, f"GIT-READ returned  changed_files={len(changed)}  diffs={len(diffs)}")
    for d in diffs:
        log_step(AGENT, f"  ↳ {d['filename']}  [{d['language']}]  +{d['additions']}/-{d['deletions']}")

    return {"changed_files": changed, "diffs": diffs}


def invoke_llm_graph(file_list: list, difference: list):
    log_step(AGENT, f"Invoking LLM-REVIEW sub-graph  →  files={len(file_list)}")
    for i, f in enumerate(file_list, 1):
        log_step(AGENT, f"  File {i}: {f}")

    data = {'file_list': file_list, 'difference': difference}
    llm_return_value = llm_review_graph.invoke(data)

    llm_bugs            = llm_return_value['bugs']
    llm_comments        = llm_return_value['comments']
    llm_test_suggetions = llm_return_value['test_suggetions']

    log_ok(AGENT, f"LLM-REVIEW returned  bugs={len(llm_bugs)}  "
                  f"tests={len(llm_test_suggetions)}  comment_len={len(str(llm_comments))}")

    return {
        "file_list":       file_list,
        "bugs":            llm_bugs,
        "comments":        llm_comments,
        "test_suggetions": llm_test_suggetions,
    }


async def invoke_jira_graph(owner: str, repo: str, pull_number: int, bugs: list):
    log_step(AGENT, f"Invoking JIRA sub-graph  →  bugs={len(bugs)}")
    for i, b in enumerate(bugs, 1):
        log_step(AGENT, f"  Bug {i}: [{b.get('severity','?').upper()}] {b.get('type','?')} — {b.get('description','')[:60]}")

    data = {
        'owner':       owner,
        'repo':        repo,
        'pull_number': pull_number,
        'bugs':        bugs,
    }
    jira_return_value = await jira_Ticket_graph.ainvoke(data)
    tickets_created   = jira_return_value.get('tickets_created', [])
    log_ok(AGENT, f"JIRA returned  tickets_created={len(tickets_created)}")
    for t in tickets_created:
        log_step(AGENT, f"  {t['ticket_key']}  [{t['severity'].upper()}]  {t['ticket_url']}")
    return tickets_created


# ─── NODE 1 ──────────────────────────────────────────────────────────────────
def orchestrator_init_node(state: OrchestraterData):
    log_pipeline_start(state.get("pr_details", "(no PR URL)"))
    log_node_enter(AGENT, "ORCHESTRATOR_INIT", "reset all orchestrator fields")

    state['owner']               = None
    state['repo']                = None
    state['pull_number']         = 0
    state['git_read_result']     = {}
    state['llm_review_result']   = {}
    state['bugs']                = []
    state['jira_ticket_details'] = {}
    state['git_write_result']    = False

    log_step(AGENT, f"PR to review: {state.get('pr_details')}")
    log_ok(AGENT, "Orchestrator state initialised")
    log_node_exit(AGENT, "ORCHESTRATOR_INIT")
    return state


# ─── NODE 2 ──────────────────────────────────────────────────────────────────
async def git_read_agent_node(state: OrchestraterData):
    log_phase("1 of 4  —  GIT READ")
    log_node_enter(AGENT, "GIT_READ_AGENT", "fetch PR files & diffs from GitHub")

    pr_url = state['pr_details']
    log_step(AGENT, f"PR URL: {pr_url}")

    git_result = await invoke_git_graph(pr_url)
    state["git_read_result"] = git_result

    diffs = git_result.get("diffs", [])
    log_diff_table(AGENT, diffs)
    log_ok(AGENT, f"GIT_READ_AGENT complete — {len(diffs)} diff(s) stored in state")

    log_node_exit(AGENT, "GIT_READ_AGENT")
    return state


# ─── NODE 3 ──────────────────────────────────────────────────────────────────
def llm_agent_node(state: OrchestraterData):
    log_phase("2 of 4  —  LLM REVIEW")
    log_node_enter(AGENT, "LLM_REVIEW_AGENT", "run code analysis & bug identification")

    diffs = state["git_read_result"].get("diffs", [])
    log_step(AGENT, f"Passing {len(diffs)} diff(s) to LLM sub-graph")

    flist   = []
    patches = []
    for d in diffs:
        flist.append(d["filename"])
        patches.append(d["patch"])
        log_step(AGENT, f"  ↳ {d['filename']}  patch_len={len(d['patch'])}")

    if not flist:
        log_warn(AGENT, "No files to pass to LLM — diffs list is empty")

    state['llm_review_result'] = invoke_llm_graph(flist, patches)

    result = state['llm_review_result']
    log_state(AGENT, {
        "bugs":           result.get("bugs", []),
        "test_count":     len(result.get("test_suggetions", [])),
        "comment_len":    len(str(result.get("comments", ""))),
    }, label="LLM_REVIEW_AGENT outputs")

    log_node_exit(AGENT, "LLM_REVIEW_AGENT")
    return state


# ─── NODE 4 ──────────────────────────────────────────────────────────────────
async def jira_agent_node(state: OrchestraterData):
    log_phase("3 of 4  —  JIRA TICKETS")
    log_node_enter(AGENT, "JIRA_AGENT", "create Jira tickets for identified bugs")

    bugs = state["llm_review_result"].get('bugs', [])
    log_step(AGENT, f"Bugs received from LLM agent: {len(bugs)}")

    if not bugs:
        log_warn(AGENT, "No bugs found — skipping Jira ticket creation")
        log_node_exit(AGENT, "JIRA_AGENT")
        return state

    # Parse owner/repo from the PR URL so the Jira agent has full context
    from GitReadAgent import parse_github_pr_url
    try:
        owner, repo, pull_number = parse_github_pr_url(state['pr_details'])
    except Exception as e:
        log_error(AGENT, f"Could not parse PR URL: {e} — skipping Jira")
        log_node_exit(AGENT, "JIRA_AGENT")
        return state

    log_step(AGENT, f"owner={owner}  repo={repo}  PR#{pull_number}")

    tickets = await invoke_jira_graph(owner, repo, pull_number, bugs)
    state['jira_ticket_details'] = tickets

    log_ok(AGENT, f"Jira phase complete — {len(tickets)} ticket(s) created")
    log_node_exit(AGENT, "JIRA_AGENT")
    return state


# ─── NODE 5 ──────────────────────────────────────────────────────────────────
def git_write_agent_node(state: OrchestraterData):
    log_phase("4 of 4  —  GIT WRITE")
    log_node_enter(AGENT, "GIT_WRITE_AGENT", "post comments, commit tests, tag PR")

    # ⚠️  Currently a pass-through — implement write operations here
    log_warn(AGENT, "GIT_WRITE_AGENT is currently DISABLED (pass-through)")
    log_step(AGENT, "Inputs available in state when enabled:")
    log_step(AGENT, f"  llm_review_result  bugs     : {state.get('llm_review_result', {}).get('bugs', [])}")
    log_step(AGENT, f"  llm_review_result  tests    : {state.get('llm_review_result', {}).get('test_suggetions', [])}")
    log_step(AGENT, f"  jira_ticket_details          : {state.get('jira_ticket_details', {})}")

    log_pipeline_end(state)
    log_node_exit(AGENT, "GIT_WRITE_AGENT")
    return state


# ─── Graph ───────────────────────────────────────────────────────────────────
def graph_Builder():
    Ograph = StateGraph(OrchestraterData)

    Ograph.add_node("ORCHESTRATOR_INIT", orchestrator_init_node)  # sync
    Ograph.add_node("GIT_READ_AGENT",    git_read_agent_node)     # async
    Ograph.add_node("LLM_REVIEW_AGENT",  llm_agent_node)          # sync
    Ograph.add_node("JIRA_AGENT",        jira_agent_node)         # async
    Ograph.add_node("GIT_WRITE_AGENT",   git_write_agent_node)    # sync

    Ograph.add_edge(START,               "ORCHESTRATOR_INIT")
    Ograph.add_edge("ORCHESTRATOR_INIT", "GIT_READ_AGENT")
    Ograph.add_edge("GIT_READ_AGENT",    "LLM_REVIEW_AGENT")
    Ograph.add_edge("LLM_REVIEW_AGENT",  "JIRA_AGENT")
    Ograph.add_edge("JIRA_AGENT",        "GIT_WRITE_AGENT")
    Ograph.add_edge("GIT_WRITE_AGENT",   END)

    graph = Ograph.compile()
    save_graph_as_png(graph, __file__)
    return graph


orchestrator_graph = graph_Builder()


async def main():
    data = {'pr_details': 'https://github.com/promptlyaig/issue-tracker/pull/1'}
    await orchestrator_graph.ainvoke(data)

if __name__ == "__main__":
    asyncio.run(main())
