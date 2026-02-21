from langgraph.graph import START, END, StateGraph
from typing import Union, TypedDict, Optional, Any, List, Dict
from lg_utility import save_graph_as_png
import os
from fastmcp import Client
import asyncio
from urllib.parse import urlparse
import re
import json
from lg_utility import pretty_print_json_list
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, log_diff_table, NodeTimer
)

AGENT = "GIT-READ"

class GitAgentState(TypedDict):
    pr_details: str
    owner: str
    repo: str
    pull_number: int
    changed_files: list
    diffs: str
    has_valid_files: bool
    client: Optional[Any]


async def call_mcp_tool(client, tool_name: str, arguments: dict = None) -> dict:
    """Helper to call MCP tools"""
    log_step(AGENT, f"Calling MCP tool: {tool_name}  args={arguments}")
    result = await client.call_tool(tool_name, arguments)
    content_text = result.content[0].text
    log_step(AGENT, f"MCP raw response length: {len(content_text)} chars")
    return json.loads(content_text) if content_text else {}


def parse_github_pr_url(url: str):
    log_step(AGENT, f"Parsing PR URL: {url}")
    parsed = urlparse(url.strip().rstrip("/"))

    if parsed.netloc.lower() != "github.com":
        raise ValueError("Not a GitHub URL")

    parts = parsed.path.strip("/").split("/")

    if len(parts) < 4 or parts[2] != "pull":
        raise ValueError("Not a GitHub Pull Request URL")

    owner = parts[0]
    repo  = parts[1]

    match = re.match(r"\d+", parts[3])
    if not match:
        raise ValueError("Invalid pull request number")

    pull_number = int(match.group())
    log_ok(AGENT, f"Parsed  →  owner={owner}  repo={repo}  PR#{pull_number}")
    return owner, repo, pull_number


# ─── NODE 1 ──────────────────────────────────────────────────────────────────
def git_read_agent_state_init_node(state: GitAgentState):
    log_node_enter(AGENT, "GIT_READ_INIT", "parse PR URL & reset state")

    state['owner']         = None
    state['repo']          = None
    state['pull_number']   = 0
    state['changed_files'] = []
    state['diffs']         = None
    state['has_valid_files'] = False
    state['client']        = None

    log_step(AGENT, f"Input pr_details: {state['pr_details']}")
    owner, repo, pull_number = parse_github_pr_url(state["pr_details"])

    state['owner']       = owner
    state['repo']        = repo
    state['pull_number'] = pull_number

    log_state(AGENT, {
        "owner":       owner,
        "repo":        repo,
        "pull_number": pull_number,
    }, label="Initialised state")

    log_node_exit(AGENT, "GIT_READ_INIT")
    return state


# ─── NODE 2 ──────────────────────────────────────────────────────────────────
async def git_connection_mcp_agent_node(state: GitAgentState):
    log_node_enter(AGENT, "CONNECT_MCP", "open FastMCP client")

    GITHUB_MCP_SERVER_URL = os.getenv("GITHUB_MCP_SERVER_URL")
    log_step(AGENT, f"GITHUB_MCP_SERVER_URL = {GITHUB_MCP_SERVER_URL or '(NOT SET — check .env!)'}")

    if not GITHUB_MCP_SERVER_URL:
        log_error(AGENT, "GITHUB_MCP_SERVER_URL env var is missing")

    client = Client(GITHUB_MCP_SERVER_URL)
    await client.__aenter__()
    state["client"] = client

    log_ok(AGENT, "MCP client connected successfully")
    log_node_exit(AGENT, "CONNECT_MCP")
    return state


# ─── NODE 3 ──────────────────────────────────────────────────────────────────
async def git_fetch_pr_agent_node(state: GitAgentState):
    log_node_enter(AGENT, "FETCH_PR", f"owner={state['owner']}  repo={state['repo']}  PR#{state['pull_number']}")

    tool_name = "GITHUB_LIST_PULL_REQUESTS_FILES"
    args = {
        "owner":       state["owner"],
        "repo":        state["repo"],
        "pull_number": state["pull_number"],
    }
    log_step(AGENT, f"Tool: {tool_name}")
    log_step(AGENT, f"Args: {args}")

    response = await call_mcp_tool(state['client'], tool_name, args)

    files = response["data"]["details"]
    log_step(AGENT, f"MCP returned {len(files)} file record(s)")

    state["changed_files"] = []
    for file in files:
        entry = {
            "filename":  file["filename"],
            "status":    file["status"],
            "additions": file["additions"],
            "deletions": file["deletions"],
            "changes":   file["changes"],
            "patch":     file.get("patch", ""),
        }
        state["changed_files"].append(entry)
        log_step(AGENT, f"  {entry['status']:8s}  {entry['filename']}  "
                        f"+{entry['additions']}/-{entry['deletions']}")

    log_ok(AGENT, f"Fetched {len(state['changed_files'])} changed file(s)")
    log_node_exit(AGENT, "FETCH_PR")
    return state


# ─── NODE 4 ──────────────────────────────────────────────────────────────────
async def extract_diffs_node(state: GitAgentState) -> GitAgentState:
    log_node_enter(AGENT, "EXTRACT_DIFFS", "structure diffs for LLM")

    state["diffs"] = []
    skipped = 0

    for file in state["changed_files"]:
        if not file.get("patch"):
            log_warn(AGENT, f"No patch for {file['filename']} (status={file['status']}) — skipping")
            skipped += 1
            continue

        filename = file["filename"]
        ext = filename.split(".")[-1] if "." in filename else "unknown"

        structured_diff = {
            "filename":  filename,
            "status":    file["status"],
            "language":  ext,
            "additions": file["additions"],
            "deletions": file["deletions"],
            "patch":     file["patch"],
        }
        state["diffs"].append(structured_diff)
        log_step(AGENT, f"Structured diff for {filename}  [{ext}]  patch_len={len(file['patch'])}")

    state["has_valid_files"] = len(state["diffs"]) > 0

    log_diff_table(AGENT, state["diffs"])

    if skipped:
        log_warn(AGENT, f"{skipped} file(s) had no patch and were skipped")

    log_ok(AGENT, f"has_valid_files={state['has_valid_files']}  →  {len(state['diffs'])} diff(s) ready")
    log_node_exit(AGENT, "EXTRACT_DIFFS")
    return state


# ─── Graph ───────────────────────────────────────────────────────────────────
def graph_Builder():
    git_read_graph = StateGraph(GitAgentState)

    git_read_graph.add_node("GIT_READ_INIT", git_read_agent_state_init_node)
    git_read_graph.add_node("CONNECT_MCP",   git_connection_mcp_agent_node)
    git_read_graph.add_node("FETCH_PR",      git_fetch_pr_agent_node)
    git_read_graph.add_node("EXTRACT_DIFFS", extract_diffs_node)

    git_read_graph.add_edge(START,           "GIT_READ_INIT")
    git_read_graph.add_edge("GIT_READ_INIT", "CONNECT_MCP")
    git_read_graph.add_edge("CONNECT_MCP",   "FETCH_PR")
    git_read_graph.add_edge("FETCH_PR",      "EXTRACT_DIFFS")
    git_read_graph.add_edge("EXTRACT_DIFFS", END)

    graph = git_read_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph


git_read_graph = graph_Builder()


async def main():
    data = {'pr_details': 'https://github.com/promptlyaig/issue-tracker/pull/1'}
    await git_read_graph.ainvoke(data)

if __name__ == "__main__":
    asyncio.run(main())
