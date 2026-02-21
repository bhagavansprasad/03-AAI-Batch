import json
import asyncio
from typing import TypedDict, Optional, Dict, Any, List
from langgraph.graph import StateGraph, START, END
from lg_utility import save_graph_as_png
from GitReadAgent  import git_read_graph,  parse_github_pr_url
from LLMReviewAgent import llm_review_graph
from JiraTicketAgent import jira_Ticket_graph
from GitWriteAgent import git_Write_graph
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, log_phase, log_pipeline_start,
    log_pipeline_end, log_diff_table
)

AGENT = "ORCH"

# ============================================================================
# ORCHESTRATOR STATE
# ============================================================================

class OrchestraterData(TypedDict):
    pr_details:          str

    # ── GIT READ outputs ──────────────────────────────────────────────────────
    owner:               str
    repo:                str
    pull_number:         int
    changed_files:       List[Dict]
    diffs:               List[Dict]

    # ── LLM REVIEW outputs ────────────────────────────────────────────────────
    llm_review_result:   Optional[Dict[str, Any]]   # {bugs, comments, test_suggetions}

    # ── JIRA outputs ──────────────────────────────────────────────────────────
    jira_ticket_details: Optional[List[Dict]]

    # ── GIT WRITE outputs ─────────────────────────────────────────────────────
    comment_posted:      bool
    tests_committed:     bool
    pr_tagged:           bool


# ============================================================================
# SUB-GRAPH INVOKERS — one per agent, clean interface
# ============================================================================

async def invoke_git_read(pr_url: str) -> Dict:
    """Invoke GitReadAgent → returns changed_files and diffs."""
    log_step(AGENT, f"→ GIT-READ  PR: {pr_url}")
    result = await git_read_graph.ainvoke({"pr_details": pr_url})

    changed = result.get("changed_files", [])
    diffs   = result.get("diffs", [])
    log_ok(AGENT, f"GIT-READ done  changed_files={len(changed)}  diffs={len(diffs)}")
    for d in diffs:
        log_step(AGENT, f"  {d['filename']}  [{d['language']}]  +{d['additions']}/-{d['deletions']}")
    return {"changed_files": changed, "diffs": diffs,
            "owner": result.get("owner"), "repo": result.get("repo"),
            "pull_number": result.get("pull_number")}


def invoke_llm_review(file_list: list, patches: list) -> Dict:
    """Invoke LLMReviewAgent → returns bugs, comments, test_suggetions."""
    log_step(AGENT, f"→ LLM-REVIEW  files={len(file_list)}")
    result = llm_review_graph.invoke({"file_list": file_list, "difference": patches})

    bugs    = result.get("bugs", [])
    comments = result.get("comments", {})
    tests   = result.get("test_suggetions", {})
    log_ok(AGENT, f"LLM-REVIEW done  bugs={len(bugs)}  "
                  f"test_cases={len(tests.get('test_cases', []) if isinstance(tests, dict) else [])}  "
                  f"comment_keys={list(comments.keys()) if isinstance(comments, dict) else '?'}")
    return {"bugs": bugs, "comments": comments, "test_suggetions": tests}


async def invoke_jira(owner: str, repo: str, pull_number: int, bugs: list) -> List:
    """Invoke JiraTicketAgent → returns list of created ticket dicts."""
    log_step(AGENT, f"→ JIRA  bugs={len(bugs)}")
    for i, b in enumerate(bugs, 1):
        log_step(AGENT, f"  Bug {i}: [{b.get('severity','?').upper()}] {b.get('type','?')} — {b.get('description','')[:60]}")

    result  = await jira_Ticket_graph.ainvoke({
        "owner": owner, "repo": repo,
        "pull_number": pull_number, "bugs": bugs,
    })
    tickets = result.get("tickets_created", [])
    log_ok(AGENT, f"JIRA done  tickets={len(tickets)}")
    for t in tickets:
        log_step(AGENT, f"  {t['ticket_key']}  [{t['severity'].upper()}]  {t['ticket_url']}")
    return tickets


async def invoke_git_write(owner: str, repo: str, pull_number: int,
                           review_comments: dict, bugs: list,
                           test_suggetions: dict, jira_tickets: list) -> Dict:
    """Invoke GitWriteAgent → posts comment, commits tests, tags PR."""
    log_step(AGENT, f"→ GIT-WRITE  PR#{pull_number}  "
                    f"bugs={len(bugs)}  "
                    f"test_cases={len(test_suggetions.get('test_cases', []) if isinstance(test_suggetions, dict) else [])}  "
                    f"jira={len(jira_tickets)}")

    result = await git_Write_graph.ainvoke({
        "owner":               owner,
        "repo":                repo,
        "pull_number":         pull_number,
        "review_comments":     review_comments,
        "bugs":                bugs,
        "test_suggetions":     test_suggetions,
        "jira_ticket_details": jira_tickets,
    })
    log_ok(AGENT, f"GIT-WRITE done  "
                  f"comment_posted={result.get('comment_posted')}  "
                  f"tests_committed={result.get('tests_committed')}  "
                  f"pr_tagged={result.get('pr_tagged')}")
    return result


# ============================================================================
# ORCHESTRATOR NODES
# ============================================================================

# ─── NODE 1 — init ───────────────────────────────────────────────────────────
def orchestrator_init_node(state: OrchestraterData) -> OrchestraterData:
    log_pipeline_start(state.get("pr_details", "(no PR URL)"))
    log_node_enter(AGENT, "ORCHESTRATOR_INIT", "reset all fields")

    state["owner"]               = None
    state["repo"]                = None
    state["pull_number"]         = 0
    state["changed_files"]       = []
    state["diffs"]               = []
    state["llm_review_result"]   = {}
    state["jira_ticket_details"] = []
    state["comment_posted"]      = False
    state["tests_committed"]     = False
    state["pr_tagged"]           = False

    log_step(AGENT, f"PR: {state['pr_details']}")
    log_node_exit(AGENT, "ORCHESTRATOR_INIT")
    return state


# ─── NODE 2 — Git Read ───────────────────────────────────────────────────────
async def git_read_agent_node(state: OrchestraterData) -> OrchestraterData:
    log_phase("1 of 4  —  GIT READ")
    log_node_enter(AGENT, "GIT_READ_AGENT", "fetch PR files & diffs")

    read_result = await invoke_git_read(state["pr_details"])

    state["owner"]         = read_result["owner"]
    state["repo"]          = read_result["repo"]
    state["pull_number"]   = read_result["pull_number"]
    state["changed_files"] = read_result["changed_files"]
    state["diffs"]         = read_result["diffs"]

    log_diff_table(AGENT, state["diffs"])
    log_ok(AGENT, f"GIT_READ_AGENT complete — {len(state['diffs'])} diff(s)")
    log_node_exit(AGENT, "GIT_READ_AGENT")
    return state


# ─── NODE 3 — LLM Review ─────────────────────────────────────────────────────
def llm_agent_node(state: OrchestraterData) -> OrchestraterData:
    log_phase("2 of 4  —  LLM REVIEW")
    log_node_enter(AGENT, "LLM_REVIEW_AGENT", "analyze code, find bugs, generate tests")

    diffs = state.get("diffs", [])
    if not diffs:
        log_warn(AGENT, "No diffs — skipping LLM review")
        log_node_exit(AGENT, "LLM_REVIEW_AGENT")
        return state

    file_list = [d["filename"] for d in diffs]
    patches   = [d["patch"]    for d in diffs]
    for f, p in zip(file_list, patches):
        log_step(AGENT, f"  {f}  patch_len={len(p)}")

    state["llm_review_result"] = invoke_llm_review(file_list, patches)

    result = state["llm_review_result"]
    log_state(AGENT, {
        "bugs":        result.get("bugs", []),
        "test_cases":  len((result.get("test_suggetions") or {}).get("test_cases", [])),
        "has_comment": bool(result.get("comments")),
    }, label="LLM_REVIEW_AGENT outputs")

    log_node_exit(AGENT, "LLM_REVIEW_AGENT")
    return state


# ─── NODE 4 — Jira ───────────────────────────────────────────────────────────
async def jira_agent_node(state: OrchestraterData) -> OrchestraterData:
    log_phase("3 of 4  —  JIRA TICKETS")
    log_node_enter(AGENT, "JIRA_AGENT", "create Jira tickets for bugs")

    bugs = state.get("llm_review_result", {}).get("bugs", [])
    if not bugs:
        log_warn(AGENT, "No bugs — skipping Jira")
        log_node_exit(AGENT, "JIRA_AGENT")
        return state

    state["jira_ticket_details"] = await invoke_jira(
        state["owner"], state["repo"], state["pull_number"], bugs
    )

    log_ok(AGENT, f"Jira phase complete — {len(state['jira_ticket_details'])} ticket(s)")
    log_node_exit(AGENT, "JIRA_AGENT")
    return state


# ─── NODE 5 — Git Write ──────────────────────────────────────────────────────
async def git_write_agent_node(state: OrchestraterData) -> OrchestraterData:
    log_phase("4 of 4  —  GIT WRITE")
    log_node_enter(AGENT, "GIT_WRITE_AGENT", "post comment, commit tests, tag PR")

    llm      = state.get("llm_review_result", {})
    comments = llm.get("comments", {})
    bugs     = llm.get("bugs", [])
    tests    = llm.get("test_suggetions", {})
    tickets  = state.get("jira_ticket_details") or []

    write_result = await invoke_git_write(
        state["owner"], state["repo"], state["pull_number"],
        comments, bugs, tests, tickets
    )

    state["comment_posted"]  = write_result.get("comment_posted", False)
    state["tests_committed"] = write_result.get("tests_committed", False)
    state["pr_tagged"]       = write_result.get("pr_tagged", False)

    log_pipeline_end(state)
    log_node_exit(AGENT, "GIT_WRITE_AGENT")
    return state


# ============================================================================
# GRAPH
# ============================================================================

def graph_Builder():
    Ograph = StateGraph(OrchestraterData)

    Ograph.add_node("ORCHESTRATOR_INIT", orchestrator_init_node)  # sync
    Ograph.add_node("GIT_READ_AGENT",    git_read_agent_node)     # async
    Ograph.add_node("LLM_REVIEW_AGENT",  llm_agent_node)          # sync
    Ograph.add_node("JIRA_AGENT",        jira_agent_node)         # async
    Ograph.add_node("GIT_WRITE_AGENT",   git_write_agent_node)    # async

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


# ============================================================================
# MAIN
# ============================================================================

async def main():
    data = {"pr_details": "https://github.com/promptlyaig/issue-tracker/pull/1"}
    await orchestrator_graph.ainvoke(data)

if __name__ == "__main__":
    asyncio.run(main())
