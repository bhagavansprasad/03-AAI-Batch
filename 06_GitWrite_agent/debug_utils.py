"""
debug_utils.py — Print-based debug helpers for the Multi-Agent PR Review System
"""

import time
import json
from datetime import datetime
from typing import Any, Dict, Optional

# ── ANSI colours ─────────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"

def _ts():
    return f"{DIM}{datetime.now().strftime('%H:%M:%S.%f')[:-3]}{RESET}"

def _tag(agent, color=CYAN):
    return f"{color}{BOLD}[{agent}]{RESET}"

# ─────────────────────────────────────────────────────────────────────────────
# Node banners
# ─────────────────────────────────────────────────────────────────────────────

def log_node_enter(agent: str, node: str, note: str = ""):
    note_str = f"  {DIM}({note}){RESET}" if note else ""
    print(f"\n{_ts()} {_tag(agent, CYAN)} {BOLD}▶ ENTER {node}{RESET}{note_str}")
    print(f"         {DIM}{'─'*55}{RESET}")

def log_node_exit(agent: str, node: str, elapsed_ms: float = None):
    timing = f"  {DIM}⏱  {elapsed_ms:.0f}ms{RESET}" if elapsed_ms else ""
    print(f"{_ts()} {_tag(agent, GREEN)} {BOLD}◀ EXIT  {node}{RESET}{timing}")
    print(f"         {DIM}{'─'*55}{RESET}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Inline log lines
# ─────────────────────────────────────────────────────────────────────────────

def log_step(agent: str, msg: str):
    print(f"{_ts()} {_tag(agent, CYAN)}  ➜  {msg}")

def log_ok(agent: str, msg: str):
    print(f"{_ts()} {_tag(agent, GREEN)}  ✅  {GREEN}{msg}{RESET}")

def log_warn(agent: str, msg: str):
    print(f"{_ts()} {_tag(agent, YELLOW)}  ⚠️   {YELLOW}{msg}{RESET}")

def log_error(agent: str, msg: str):
    print(f"{_ts()} {_tag(agent, RED)}  ❌  {RED}{msg}{RESET}")

def log_info(agent: str, msg: str):
    print(f"{_ts()} {_tag(agent, BLUE)}  ℹ️   {msg}")

# ─────────────────────────────────────────────────────────────────────────────
# State snapshot (trimmed — skips large/binary fields)
# ─────────────────────────────────────────────────────────────────────────────

_LARGE_KEYS = {"client", "patch", "diffs", "changed_files", "git_read_result",
               "llm_review_result", "jira_ticket_details"}

def log_state(agent: str, state: Dict, label: str = "State"):
    print(f"{_ts()} {_tag(agent, MAGENTA)}  📋  {BOLD}{label}{RESET}")
    for k, v in state.items():
        if k in _LARGE_KEYS:
            if isinstance(v, list):
                display = f"[list · {len(v)} items]"
            elif isinstance(v, dict):
                display = f"{{dict · {len(v)} keys}}"
            else:
                display = "(large — hidden)"
        elif isinstance(v, str) and len(v) > 120:
            display = v[:120] + " …"
        elif isinstance(v, list):
            display = f"{v[:3]}{'…' if len(v) > 3 else ''} ({len(v)} items)"
        else:
            display = v
        print(f"         {DIM}│{RESET}  {BOLD}{k}{RESET}: {display}")

# ─────────────────────────────────────────────────────────────────────────────
# Specialised printers
# ─────────────────────────────────────────────────────────────────────────────

def log_diff_table(agent: str, diffs: list):
    if not diffs:
        log_warn(agent, "No diffs found")
        return
    print(f"{_ts()} {_tag(agent, CYAN)}  📂  Diff summary — {len(diffs)} file(s):")
    for i, d in enumerate(diffs, 1):
        fname  = d.get("filename", "?")
        lang   = d.get("language", "?")
        status = d.get("status", "?")
        adds   = d.get("additions", 0)
        dels   = d.get("deletions", 0)
        print(f"         {DIM}│{RESET}  {i:>2}. {BOLD}{fname}{RESET}  "
              f"[{lang}]  {GREEN}+{adds}{RESET} {RED}-{dels}{RESET}  status={status}")

def log_llm_result(agent: str, analysis: dict):
    bugs     = analysis.get("bugs", [])
    quality  = analysis.get("code_quality_issues", [])
    security = analysis.get("security_issues", [])
    summary  = analysis.get("summary", "N/A")
    print(f"{_ts()} {_tag(agent, MAGENTA)}  🤖  LLM Analysis:")
    print(f"         {DIM}│{RESET}  Bugs       : {RED}{len(bugs)}{RESET}")
    print(f"         {DIM}│{RESET}  Quality    : {YELLOW}{len(quality)}{RESET}")
    print(f"         {DIM}│{RESET}  Security   : {YELLOW}{len(security)}{RESET}")
    print(f"         {DIM}│{RESET}  Summary    : {summary[:150]}")
    for i, bug in enumerate(bugs[:5], 1):
        sev = bug.get("severity", "?").upper()
        col = RED if sev == "HIGH" else YELLOW if sev == "MEDIUM" else DIM
        desc = bug.get("description", "")[:80]
        print(f"         {DIM}│{RESET}    Bug {i}: {col}{sev}{RESET} — {desc}")

def log_json(agent: str, label: str, data: Any, max_chars: int = 300):
    raw = json.dumps(data, indent=2, default=str)
    if len(raw) > max_chars:
        raw = raw[:max_chars] + "\n  … (truncated)"
    print(f"{_ts()} {_tag(agent, BLUE)}  📄  {BOLD}{label}{RESET}")
    for line in raw.splitlines():
        print(f"         {DIM}│{RESET}  {line}")

# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator-level banners
# ─────────────────────────────────────────────────────────────────────────────

def log_pipeline_start(pr_url: str):
    w = 65
    print("\n" + f"{BOLD}{CYAN}{'═'*w}{RESET}")
    print(f"{BOLD}{CYAN}  🚀  PR REVIEW PIPELINE  —  STARTING{RESET}")
    print(f"  PR  : {pr_url}")
    print(f"  At  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{BOLD}{CYAN}{'═'*w}{RESET}\n")

def log_phase(name: str):
    print(f"\n{BOLD}{MAGENTA}{'─'*65}{RESET}")
    print(f"{BOLD}{MAGENTA}  ● PHASE : {name}{RESET}")
    print(f"{BOLD}{MAGENTA}{'─'*65}{RESET}\n")

def log_pipeline_end(state: Dict):
    w = 65
    print(f"\n{BOLD}{GREEN}{'═'*w}{RESET}")
    print(f"{BOLD}{GREEN}  🏁  PIPELINE COMPLETE{RESET}")
    diffs = state.get("git_read_result", {}).get("diffs", [])
    bugs  = state.get("llm_review_result", {}).get("bugs", [])
    jira  = state.get("jira_ticket_details", [])
    print(f"  Files reviewed : {len(diffs)}")
    print(f"  Bugs found     : {len(bugs)}")
    print(f"  Jira tickets   : {len(jira) if isinstance(jira, list) else '?'}")
    print(f"{BOLD}{GREEN}{'═'*w}{RESET}\n")

# ─────────────────────────────────────────────────────────────────────────────
# Timer context manager
# ─────────────────────────────────────────────────────────────────────────────

class NodeTimer:
    """
    with NodeTimer("GIT", "FETCH_PR") as t:
        ...
    # auto-prints enter/exit with elapsed time
    """
    def __init__(self, agent: str, node: str, note: str = ""):
        self.agent = agent
        self.node  = node
        self.note  = note
        self.elapsed_ms = 0.0

    def __enter__(self):
        self._t0 = time.perf_counter()
        log_node_enter(self.agent, self.node, self.note)
        return self

    def __exit__(self, *_):
        self.elapsed_ms = (time.perf_counter() - self._t0) * 1000
        log_node_exit(self.agent, self.node, self.elapsed_ms)
