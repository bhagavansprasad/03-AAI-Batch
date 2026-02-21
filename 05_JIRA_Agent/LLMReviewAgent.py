from langgraph.graph import START, END, StateGraph
from typing import TypedDict, Optional, Dict, Any
from lg_utility import save_graph_as_png
import json
import re
import google.generativeai as genai
import os
from llm_agent_prompts import (
    create_combined_prompt,
    format_diffs_for_analysis,
)
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, log_llm_result, NodeTimer
)

AGENT      = "LLM-REVIEW"
MODEL_NAME = "gemini-2.0-flash"

# ============================================================================
# STATE
# ============================================================================

class LLMReviewAgentState(TypedDict):
    # ── inputs (from Git Agent via Orchestrator) ──────────────────────────────
    file_list:       list          # e.g. ["foo.py", "bar.py"]
    difference:      list          # parallel list of patch strings

    # ── outputs ───────────────────────────────────────────────────────────────
    comments:        Optional[Dict[str, Any]]   # structured review comment dict
    bugs:            Optional[list]              # list of bug dicts
    test_suggetions: Optional[Dict[str, Any]]   # test_framework + test_cases


# ============================================================================
# NODES
# ============================================================================

# ─── NODE 1 — init ───────────────────────────────────────────────────────────
def llm_review_init_node(state: LLMReviewAgentState):
    log_node_enter(AGENT, "LLM_INIT", "reset outputs, validate inputs")

    state['comments']       = None
    state['bugs']           = []
    state['test_suggetions'] = {}

    file_list  = state.get("file_list", [])
    difference = state.get("difference", [])

    log_step(AGENT, f"Files received  : {len(file_list)}")
    log_step(AGENT, f"Patches received: {len(difference)}")

    for i, fname in enumerate(file_list, 1):
        patch_len = len(difference[i - 1]) if i - 1 < len(difference) else 0
        log_step(AGENT, f"  File {i}: {fname}  (patch_len={patch_len} chars)")

    if len(file_list) != len(difference):
        log_warn(AGENT, f"file_list length ({len(file_list)}) != difference length ({len(difference)}) — zip will truncate")

    log_node_exit(AGENT, "LLM_INIT")
    return state


# ─── NODE 2 — single combined LLM call ───────────────────────────────────────
def llm_review_analyze_and_generate_node(state: LLMReviewAgentState):
    """
    Single Gemini call that returns all three outputs at once:
      review_comments  ->  state['comments']
      bugs_found       ->  state['bugs']
      test_suggestions ->  state['test_suggetions']
    """
    log_node_enter(AGENT, "ANALYZE_AND_GENERATE",
                   "one-shot Gemini call: review + bugs + tests")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log_error(AGENT, "GEMINI_API_KEY env var is not set!")
    else:
        log_step(AGENT, f"GEMINI_API_KEY loaded ({len(api_key)} chars)")

    # ── Build diffs from parallel file_list / difference arrays ──────────────
    diffs = []
    for fname, patch in zip(state.get("file_list", []), state.get("difference", [])):
        ext = fname.rsplit(".", 1)[-1] if "." in fname else "unknown"
        diffs.append({
            "filename":  fname,
            "language":  ext,
            "additions": patch.count("\n+"),
            "deletions": patch.count("\n-"),
            "patch":     patch,
        })

    log_step(AGENT, f"Diff structs built: {len(diffs)}")
    for d in diffs:
        log_step(AGENT, f"  -> {d['filename']}  [{d['language']}]  "
                        f"+{d['additions']}/-{d['deletions']}  patch_len={len(d['patch'])}")

    # ── Build & send prompt ───────────────────────────────────────────────────
    prompt = create_combined_prompt(diffs)
    log_step(AGENT, f"Combined prompt length: {len(prompt)} chars")
    log_step(AGENT, f"Using model: {MODEL_NAME}")
    log_step(AGENT, "Sending single request to Gemini ...")

    genai.configure(api_key=api_key)
    model         = genai.GenerativeModel(MODEL_NAME)
    response      = model.generate_content(prompt)
    response_text = response.text.strip()

    log_step(AGENT, f"Response received — {len(response_text)} chars")
    print(f"\n         ── Raw Gemini Response (first 600 chars) ──")
    print(f"         {response_text[:600]}")
    print(f"         ──────────────────────────────────────────\n")

    # ── Parse JSON ────────────────────────────────────────────────────────────
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

    if not json_match:
        log_error(AGENT, "No JSON object found in response — all outputs set to defaults")
        log_node_exit(AGENT, "ANALYZE_AND_GENERATE")
        return state

    try:
        result = json.loads(json_match.group(0))
    except json.JSONDecodeError as e:
        log_error(AGENT, f"JSON decode failed: {e} — all outputs set to defaults")
        log_node_exit(AGENT, "ANALYZE_AND_GENERATE")
        return state

    log_ok(AGENT, "JSON parsed successfully")

    # ── Unpack into state ─────────────────────────────────────────────────────

    # 1. review_comments -> state['comments']
    review = result.get("review_comments", {})
    state['comments'] = review
    log_step(AGENT, f"review_comments.summary        : {str(review.get('summary', ''))[:100]}")
    log_step(AGENT, f"review_comments.bugs           : {len(review.get('bugs', []))}")
    log_step(AGENT, f"review_comments.quality_issues : {len(review.get('quality_issues', []))}")
    log_step(AGENT, f"review_comments.security_issues: {len(review.get('security_issues', []))}")
    log_step(AGENT, f"review_comments.positive_feedback: {len(review.get('positive_feedback', []))}")

    # 2. bugs_found -> state['bugs']
    bugs = result.get("bugs_found", [])
    state['bugs'] = bugs
    log_step(AGENT, f"bugs_found: {len(bugs)} bug(s)")
    for i, bug in enumerate(bugs, 1):
        sev  = bug.get('severity', '?').upper()
        desc = bug.get('description', '')[:70]
        loc  = bug.get('location', '?')
        log_step(AGENT, f"  Bug {i}: [{sev}] {desc}  @ {loc}")

    # 3. test_suggestions -> state['test_suggetions']
    tests = result.get("test_suggestions", {})
    state['test_suggetions'] = tests
    test_cases = tests.get("test_cases", [])
    log_step(AGENT, f"test_suggestions.framework : {tests.get('test_framework', '?')}")
    log_step(AGENT, f"test_suggestions.test_cases: {len(test_cases)}")
    for i, tc in enumerate(test_cases, 1):
        log_step(AGENT, f"  Test {i}: {tc.get('test_name', '?')} — {tc.get('description', '')[:60]}")

    # ── Final state snapshot ──────────────────────────────────────────────────
    log_state(AGENT, {
        "comments_summary": str(review.get("summary", ""))[:80],
        "bugs_count":       len(bugs),
        "tests_count":      len(test_cases),
        "test_framework":   tests.get("test_framework", "?"),
    }, label="ANALYZE_AND_GENERATE — final outputs")

    log_ok(AGENT, "All outputs written to state in a single LLM call")
    log_node_exit(AGENT, "ANALYZE_AND_GENERATE")
    print(json.dumps(state, sort_keys=True, indent=4))
    return state


# ============================================================================
# GRAPH
# ============================================================================

def graph_Builder():
    llm_review_graph = StateGraph(LLMReviewAgentState)

    llm_review_graph.add_node("LLM_INIT",            llm_review_init_node)
    llm_review_graph.add_node("ANALYZE_AND_GENERATE", llm_review_analyze_and_generate_node)

    llm_review_graph.add_edge(START,                  "LLM_INIT")
    llm_review_graph.add_edge("LLM_INIT",             "ANALYZE_AND_GENERATE")
    llm_review_graph.add_edge("ANALYZE_AND_GENERATE", END)

    graph = llm_review_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph


llm_review_graph = graph_Builder()


# ============================================================================
# MAIN — standalone test
# ============================================================================

def main():
    data = {
        'file_list':  ['b1.py', 'a1.py'],
        'difference': [
            "@@ -1,5 +1,8 @@\n+import os\n def foo():\n-    x = 1/0\n+    x = int(os.getenv('VAL'))\n",
            "@@ -10,3 +10,6 @@\n+def bar(lst):\n+    return lst[99]\n",
        ]
    }
    llm_review_graph.invoke(data)

if __name__ == "__main__":
    main()
