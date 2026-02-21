import os
import re
import json
import asyncio
from urllib.parse import urlparse
from typing import TypedDict, Optional, Any, List, Dict
from langgraph.graph import StateGraph, START, END
from fastmcp import Client
from lg_utility import save_graph_as_png
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, log_diff_table
)

AGENT = "GIT-READ"

# ============================================================================
# STATE  — only what the read agent needs
# ============================================================================

class GitReadAgentState(TypedDict):
    # ── input ─────────────────────────────────────────────────────────────────
    pr_details:    str              # full GitHub PR URL

    # ── parsed from URL ───────────────────────────────────────────────────────
    owner:         str
    repo:          str
    pull_number:   int

    # ── outputs ───────────────────────────────────────────────────────────────
    changed_files: List[Dict]       # raw file records from GitHub
    diffs:         List[Dict]       # structured diffs ready for LLM
    has_valid_files: bool

    # ── internal ──────────────────────────────────────────────────────────────
    client:        Optional[Any]


# ============================================================================
# HELPERS
# ============================================================================

def parse_github_pr_url(url: str):
    """Parse owner, repo, pull_number from a GitHub PR URL."""
    log_step(AGENT, f"Parsing PR URL: {url}")
    parsed = urlparse(url.strip().rstrip("/"))

    if parsed.netloc.lower() != "github.com":
        raise ValueError("Not a GitHub URL")

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 4 or parts[2] != "pull":
        raise ValueError("Not a GitHub Pull Request URL")

    match = re.match(r"\d+", parts[3])
    if not match:
        raise ValueError("Invalid pull request number")

    owner       = parts[0]
    repo        = parts[1]
    pull_number = int(match.group())
    log_ok(AGENT, f"Parsed  →  owner={owner}  repo={repo}  PR#{pull_number}")
    return owner, repo, pull_number


async def call_mcp_tool(client, tool_name: str, arguments: dict) -> dict:
    """Call a GitHub MCP tool and return parsed JSON response."""
    log_step(AGENT, f"MCP call: {tool_name}  args={arguments}")
    result       = await client.call_tool(tool_name, arguments)
    content_text = result.content[0].text
    log_step(AGENT, f"MCP response length: {len(content_text)} chars")
    return json.loads(content_text) if content_text else {}


# ============================================================================
# NODES
# ============================================================================

# ─── NODE 1 — parse URL & init state ─────────────────────────────────────────
def git_read_init_node(state: GitReadAgentState) -> GitReadAgentState:
    log_node_enter(AGENT, "GIT_READ_INIT", "parse PR URL, reset all fields")

    state["owner"]           = None
    state["repo"]            = None
    state["pull_number"]     = 0
    state["changed_files"]   = []
    state["diffs"]           = []
    state["has_valid_files"] = False
    state["client"]          = None

    log_step(AGENT, f"Input: {state['pr_details']}")
    owner, repo, pull_number = parse_github_pr_url(state["pr_details"])

    state["owner"]       = owner
    state["repo"]        = repo
    state["pull_number"] = pull_number

    log_state(AGENT, {"owner": owner, "repo": repo, "pull_number": pull_number},
              label="Parsed PR info")
    log_node_exit(AGENT, "GIT_READ_INIT")
    return state


# ─── NODE 2 — connect to GitHub MCP ──────────────────────────────────────────
async def git_read_connect_mcp_node(state: GitReadAgentState) -> GitReadAgentState:
    log_node_enter(AGENT, "CONNECT_MCP", "open FastMCP client to GitHub server")

    mcp_url = os.getenv("GITHUB_MCP_SERVER_URL")
    log_step(AGENT, f"GITHUB_MCP_SERVER_URL = {mcp_url or '(NOT SET!)'}")

    if not mcp_url:
        log_error(AGENT, "GITHUB_MCP_SERVER_URL env var is missing — cannot read PR")
        log_node_exit(AGENT, "CONNECT_MCP")
        return state

    try:
        client = Client(mcp_url)
        await client.__aenter__()
        state["client"] = client
        log_ok(AGENT, "GitHub MCP client connected")
    except Exception as e:
        log_error(AGENT, f"Connection failed: {e}")

    log_node_exit(AGENT, "CONNECT_MCP")
    return state


# ─── NODE 3 — fetch changed files from GitHub ────────────────────────────────
async def git_fetch_pr_files_node(state: GitReadAgentState) -> GitReadAgentState:
    log_node_enter(AGENT, "FETCH_PR_FILES",
                   f"owner={state['owner']}  repo={state['repo']}  PR#{state['pull_number']}")

    client = state.get("client")
    if not client:
        log_warn(AGENT, "No MCP client — skipping file fetch")
        log_node_exit(AGENT, "FETCH_PR_FILES")
        return state

    response = await call_mcp_tool(client, "GITHUB_LIST_PULL_REQUESTS_FILES", {
        "owner":       state["owner"],
        "repo":        state["repo"],
        "pull_number": state["pull_number"],
    })

    files = response.get("data", {}).get("details", [])
    log_step(AGENT, f"GitHub returned {len(files)} file(s)")

    state["changed_files"] = []
    for f in files:
        entry = {
            "filename":  f["filename"],
            "status":    f["status"],
            "additions": f["additions"],
            "deletions": f["deletions"],
            "changes":   f["changes"],
            "patch":     f.get("patch", ""),
        }
        state["changed_files"].append(entry)
        log_step(AGENT, f"  {entry['status']:8s}  {entry['filename']}  "
                        f"+{entry['additions']}/-{entry['deletions']}")

    log_ok(AGENT, f"Fetched {len(state['changed_files'])} changed file(s)")
    log_node_exit(AGENT, "FETCH_PR_FILES")
    return state


# ─── NODE 4 — structure diffs for LLM ────────────────────────────────────────
async def git_extract_diffs_node(state: GitReadAgentState) -> GitReadAgentState:
    log_node_enter(AGENT, "EXTRACT_DIFFS", "build structured diff list for LLM agent")

    state["diffs"] = []
    skipped = 0

    for file in state["changed_files"]:
        if not file.get("patch"):
            log_warn(AGENT, f"  No patch for {file['filename']} ({file['status']}) — skipped")
            skipped += 1
            continue

        filename = file["filename"]
        ext      = filename.rsplit(".", 1)[-1] if "." in filename else "unknown"

        state["diffs"].append({
            "filename":  filename,
            "status":    file["status"],
            "language":  ext,
            "additions": file["additions"],
            "deletions": file["deletions"],
            "patch":     file["patch"],
        })
        log_step(AGENT, f"  Structured: {filename}  [{ext}]  patch_len={len(file['patch'])}")

    state["has_valid_files"] = len(state["diffs"]) > 0

    log_diff_table(AGENT, state["diffs"])
    if skipped:
        log_warn(AGENT, f"{skipped} file(s) skipped (no patch)")

    log_ok(AGENT, f"has_valid_files={state['has_valid_files']}  —  {len(state['diffs'])} diff(s) ready for LLM")
    log_node_exit(AGENT, "EXTRACT_DIFFS")
    return state


# ============================================================================
# GRAPH
# ============================================================================

def graph_Builder():
    graph = StateGraph(GitReadAgentState)

    graph.add_node("GIT_READ_INIT",   git_read_init_node)        # sync
    graph.add_node("CONNECT_MCP",     git_read_connect_mcp_node) # async
    graph.add_node("FETCH_PR_FILES",  git_fetch_pr_files_node)   # async
    graph.add_node("EXTRACT_DIFFS",   git_extract_diffs_node)    # async

    graph.add_edge(START,             "GIT_READ_INIT")
    graph.add_edge("GIT_READ_INIT",   "CONNECT_MCP")
    graph.add_edge("CONNECT_MCP",     "FETCH_PR_FILES")
    graph.add_edge("FETCH_PR_FILES",  "EXTRACT_DIFFS")
    graph.add_edge("EXTRACT_DIFFS",   END)

    compiled = graph.compile()
    save_graph_as_png(compiled, __file__)
    return compiled


git_read_graph = graph_Builder()


# ============================================================================
# MAIN — standalone test
# ============================================================================

async def main():
    data = {"pr_details": "https://github.com/promptlyaig/issue-tracker/pull/1"}
    result = await git_read_graph.ainvoke(data)
    print(f"\ndiffs={len(result['diffs'])}  has_valid_files={result['has_valid_files']}")

if __name__ == "__main__":
    asyncio.run(main())
