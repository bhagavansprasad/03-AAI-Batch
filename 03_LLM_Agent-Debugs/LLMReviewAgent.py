from langgraph.graph import START, END, StateGraph
from typing import Union, TypedDict, Optional, Dict, Any
from lg_utility import save_graph_as_png
import json
import re
from lg_utility import pretty_print_json_list
import google.generativeai as genai
import os
from llm_agent_prompts import create_analysis_prompt
from debug_utils import (
    log_node_enter, log_node_exit, log_step, log_ok, log_warn,
    log_error, log_state, log_llm_result, log_json, NodeTimer
)

AGENT = "LLM-REVIEW"

class LLMReviewAgentState(TypedDict):
    file_list:      list
    difference:     list
    comments:       str
    bugs:           list
    test_suggetions: list


# ─── NODE 1 ──────────────────────────────────────────────────────────────────
def llm_review_analyze_init_node(state: LLMReviewAgentState):
    log_node_enter(AGENT, "LLM_INIT", "reset output fields")

    state['bugs']           = []
    state['comments']       = None
    state['test_suggetions'] = []

    log_step(AGENT, f"file_list has {len(state.get('file_list', []))} file(s)")
    log_step(AGENT, f"difference has {len(state.get('difference', []))} patch(es)")
    for i, fname in enumerate(state.get("file_list", []), 1):
        log_step(AGENT, f"  File {i}: {fname}")

    log_node_exit(AGENT, "LLM_INIT")
    return state


# ─── NODE 2 ──────────────────────────────────────────────────────────────────
def llm_review_analyze_code_agent_node(state: LLMReviewAgentState) -> LLMReviewAgentState:
    log_node_enter(AGENT, "ANALYZE_CODE", "send diffs to Gemini for analysis")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log_error(AGENT, "GEMINI_API_KEY env var is not set!")
    else:
        log_step(AGENT, f"GEMINI_API_KEY loaded  ({len(api_key)} chars)")

    genai.configure(api_key=api_key)
    model_name = "gemini-2.0-flash"
    log_step(AGENT, f"Using model: {model_name}")

    # Build diffs list from parallel file_list / difference arrays
    diffs = []
    for fname, patch in zip(state.get("file_list", []), state.get("difference", [])):
        ext = fname.split(".")[-1] if "." in fname else "unknown"
        diffs.append({
            "filename":  fname,
            "language":  ext,
            "additions": patch.count("\n+"),
            "deletions": patch.count("\n-"),
            "patch":     patch,
        })

    log_step(AGENT, f"Built {len(diffs)} diff struct(s) for prompt")

    full_prompt = create_analysis_prompt(diffs)
    log_step(AGENT, f"Prompt length: {len(full_prompt)} chars")

    model    = genai.GenerativeModel(model_name)
    log_step(AGENT, "Sending request to Gemini …")
    response = model.generate_content(full_prompt)
    response_text = response.text.strip()

    log_step(AGENT, f"Raw LLM response length: {len(response_text)} chars")
    print(f"\n         ── LLM Raw Response (first 400 chars) ──")
    print(f"         {response_text[:400]}")
    print(f"         ────────────────────────────────────────\n")

    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

    if json_match:
        try:
            analysis = json.loads(json_match.group(0))
            state["llm_analysis"] = analysis
            log_llm_result(AGENT, analysis)
            log_ok(AGENT, f"JSON parsed successfully — {len(analysis.get('bugs', []))} bug(s) found")
        except json.JSONDecodeError as e:
            log_error(AGENT, f"JSON decode failed: {e}")
            state["llm_analysis"] = {"bugs": [], "summary": response_text}
    else:
        log_warn(AGENT, "No JSON object found in LLM response — storing raw text as summary")
        state["llm_analysis"] = {"bugs": [], "summary": response_text}

    log_node_exit(AGENT, "ANALYZE_CODE")
    print(json.dumps(analysis, sort_keys=True, indent=4))
    return state


# ─── NODE 3 ──────────────────────────────────────────────────────────────────
def llm_review_genrate_review_agent_node(state: LLMReviewAgentState):
    log_node_enter(AGENT, "GENERATE_REVIEW", "produce PR review comment text")

    review_comments = "Comment1 comment2 commnet3"   # placeholder
    state['comments'] = review_comments

    log_step(AGENT, f"Generated review comment ({len(review_comments)} chars)")
    log_step(AGENT, f"Preview: {review_comments[:120]}")
    log_ok(AGENT, "Review comment ready")

    log_node_exit(AGENT, "GENERATE_REVIEW")
    return state


# ─── NODE 4 ──────────────────────────────────────────────────────────────────
def llm_review_identify_bug_agent_node(state: LLMReviewAgentState):
    log_node_enter(AGENT, "IDENTIFY_BUG", "extract bug list from analysis")

    # Placeholder — replace with real extraction from state["llm_analysis"]
    bugs = ['bug1', 'bug2', 'bug3']
    state['bugs'] = bugs

    log_step(AGENT, f"Bugs identified: {len(bugs)}")
    for i, b in enumerate(bugs, 1):
        log_step(AGENT, f"  Bug {i}: {b}")

    log_ok(AGENT, f"{len(bugs)} bug(s) written to state")
    log_node_exit(AGENT, "IDENTIFY_BUG")
    return state


# ─── NODE 5 ──────────────────────────────────────────────────────────────────
def llm_review_suggest_test_agent_node(state: LLMReviewAgentState):
    log_node_enter(AGENT, "SUGGEST_TEST", "generate test suggestions for each bug")

    # Placeholder — replace with real test generation
    test_suggetions = ['test1', 'test2', 'test3']
    state['test_suggetions'] = test_suggetions

    log_step(AGENT, f"Test suggestions generated: {len(test_suggetions)}")
    for i, t in enumerate(test_suggetions, 1):
        log_step(AGENT, f"  Test {i}: {t}")

    log_ok(AGENT, f"{len(test_suggetions)} test suggestion(s) written to state")

    # Final summary of all LLM outputs
    log_state(AGENT, {
        "bugs":           state["bugs"],
        "comments":       state["comments"],
        "test_suggetions": state["test_suggetions"],
    }, label="LLM Agent final outputs")

    log_node_exit(AGENT, "SUGGEST_TEST")
    return state


# ─── Graph ───────────────────────────────────────────────────────────────────
def graph_Builder():
    llm_review_graph = StateGraph(LLMReviewAgentState)

    llm_review_graph.add_node("LLM_INIT",       llm_review_analyze_init_node)
    llm_review_graph.add_node("ANALYZE_CODE",   llm_review_analyze_code_agent_node)
    llm_review_graph.add_node("GENERATE_REVIEW", llm_review_genrate_review_agent_node)
    llm_review_graph.add_node("IDENTIFY_BUG",   llm_review_identify_bug_agent_node)
    llm_review_graph.add_node("SUGGEST_TEST",   llm_review_suggest_test_agent_node)

    llm_review_graph.add_edge(START,             "LLM_INIT")
    llm_review_graph.add_edge("LLM_INIT",        "ANALYZE_CODE")
    llm_review_graph.add_edge("ANALYZE_CODE",    "GENERATE_REVIEW")
    llm_review_graph.add_edge("GENERATE_REVIEW", "IDENTIFY_BUG")
    llm_review_graph.add_edge("IDENTIFY_BUG",    "SUGGEST_TEST")
    llm_review_graph.add_edge("SUGGEST_TEST",    END)

    graph = llm_review_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph


llm_review_graph = graph_Builder()


def main():
    data = {'file_list': ['b1.py', 'a1.py'], 'difference': "Hello word"}
    llm_review_graph.invoke(data)

if __name__ == "__main__":
    main()
