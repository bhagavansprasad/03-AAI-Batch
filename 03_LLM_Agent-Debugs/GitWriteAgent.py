from langgraph.graph import START, END, StateGraph
from typing import Union, TypedDict, Optional, Dict, Any
from lg_utility import save_graph_as_png
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, NodeTimer
)

AGENT = "GIT-WRITE"

class GitAgentState(TypedDict):
    owner:              str
    repo:               str
    pull_number:        int
    bugs:               list
    jira_client:        str
    tickets_created:    str
    git_read_result:    Optional[Dict[str, Any]]
    llm_review_result:  Optional[Dict[str, Any]]
    jira_ticket_details: Optional[Dict[str, Any]]
    diff:               Optional[Dict[str, Any]]
    test_suggetions:    Optional[Dict[str, Any]]


# ─── NODE 1 ──────────────────────────────────────────────────────────────────
def git_Write_init_node(state: GitAgentState):
    log_node_enter(AGENT, "GIT_INIT", "reset write-agent state")

    state['owner']              = None
    state['repo']               = None
    state['bugs']               = []
    state['pull_number']        = 0
    state['git_read_result']    = {}
    state['llm_review_result']  = {}
    state['jira_ticket_details'] = {}
    state['diff']               = {}
    state['test_suggetions']    = {}

    log_step(AGENT, "All output fields reset to empty defaults")
    log_node_exit(AGENT, "GIT_INIT")
    return state


# ─── NODE 2 ──────────────────────────────────────────────────────────────────
def git_Write_agent_node(state: GitAgentState):
    log_node_enter(AGENT, "GIT_WRITE", "prepare write payload for GitHub")

    owner  = state.get("owner")
    repo   = state.get("repo")
    pr_num = state.get("pull_number")

    log_step(AGENT, f"Target: github.com/{owner}/{repo}  PR#{pr_num}")
    log_step(AGENT, f"Bugs to address : {state.get('bugs', [])}")
    log_step(AGENT, f"Jira tickets    : {state.get('jira_ticket_details', {})}")

    # TODO: build actual write payloads here
    log_ok(AGENT, "Write payload prepared (placeholder)")

    log_node_exit(AGENT, "GIT_WRITE")
    return state


# ─── NODE 3 ──────────────────────────────────────────────────────────────────
def git_post_comment_agent_node(state: GitAgentState):
    log_node_enter(AGENT, "POST_COMMENTS", "post review comment to PR")

    llm_result = state.get("llm_review_result", {})
    comments   = llm_result.get("comments", "(none)")

    log_step(AGENT, f"Comment length : {len(str(comments))} chars")
    log_step(AGENT, f"Preview        : {str(comments)[:120]}")

    # TODO: call GitHub API to post comment
    log_ok(AGENT, "Review comment posted to PR (placeholder)")

    log_node_exit(AGENT, "POST_COMMENTS")
    return state


# ─── NODE 4 ──────────────────────────────────────────────────────────────────
def git_commit_test_agent_node(state: GitAgentState):
    log_node_enter(AGENT, "COMMIT_TESTS", "commit generated tests to branch")

    llm_result = state.get("llm_review_result", {})
    tests      = llm_result.get("test_suggetions", [])

    log_step(AGENT, f"Tests to commit: {len(tests)}")
    for i, t in enumerate(tests, 1):
        log_step(AGENT, f"  Test {i}: {t}")

    if not tests:
        log_warn(AGENT, "No tests to commit")

    # TODO: write test files and commit via GitHub API
    log_ok(AGENT, "Test files committed (placeholder)")

    log_node_exit(AGENT, "COMMIT_TESTS")
    return state


# ─── NODE 5 ──────────────────────────────────────────────────────────────────
def git_tag_pr_agent_node(state: GitAgentState):
    log_node_enter(AGENT, "TAG_PR", "apply labels / tags to the PR")

    bugs  = state.get("bugs", [])
    label = "reviewed-by-bot"

    log_step(AGENT, f"Bugs found: {len(bugs)}  →  label='{label}'")

    # TODO: call GitHub API to add label
    log_ok(AGENT, f"PR tagged with '{label}' (placeholder)")

    log_state(AGENT, {
        "owner":      state.get("owner"),
        "repo":       state.get("repo"),
        "PR#":        state.get("pull_number"),
        "bugs":       bugs,
        "tag_applied": label,
    }, label="GIT-WRITE final state")

    log_node_exit(AGENT, "TAG_PR")
    return state


# ─── Graph ───────────────────────────────────────────────────────────────────
def graph_Builder():
    git_Write_graph = StateGraph(GitAgentState)

    git_Write_graph.add_node("GIT_INIT",      git_Write_init_node)
    git_Write_graph.add_node("GIT_WRITE",     git_Write_agent_node)
    git_Write_graph.add_node("POST_COMMENTS", git_post_comment_agent_node)
    git_Write_graph.add_node("COMMIT_TESTS",  git_commit_test_agent_node)
    git_Write_graph.add_node("TAG_PR",        git_tag_pr_agent_node)

    git_Write_graph.add_edge(START,           "GIT_INIT")
    git_Write_graph.add_edge("GIT_INIT",      "GIT_WRITE")
    git_Write_graph.add_edge("GIT_WRITE",     "POST_COMMENTS")
    git_Write_graph.add_edge("POST_COMMENTS", "COMMIT_TESTS")
    git_Write_graph.add_edge("COMMIT_TESTS",  "TAG_PR")
    git_Write_graph.add_edge("TAG_PR",        END)

    graph = git_Write_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph


git_Write_graph = graph_Builder()


def main():
    data = {'data': 'vikas'}
    git_Write_graph.invoke(data)

if __name__ == "__main__":
    main()
