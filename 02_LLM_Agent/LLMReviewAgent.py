from langgraph.graph import START, END, StateGraph
from typing import Union,TypedDict,Optional,Dict,Any
from lg_utility import save_graph_as_png
import json
from lg_utility import pretty_print_json_list
import google.generativeai as genai
import os
from llm_agent_prompts import create_analysis_prompt


class LLMReviewAgentState(TypedDict):
    file_list:list
    difference:list
    comments:str
    bugs : list
    test_suggetions : list
    # owner: str
    # repo: str
    # bugs :str
    # pull_number: int
    # git_read_result : Optional[Dict[str, Any]]
    # llm_review_result : Optional[Dict[str, Any]]
    # jira_ticket_details : Optional[Dict[str, Any]]
    # diff : Optional[Dict[str, Any]]
    # jira_ticket : list
    #comments : list

    #git_write_result : bool

def llm_review_analyze_init_node(state: LLMReviewAgentState ):
    print ("in llm_init_node")
    # print(f"state :{state}")
    state['bugs'] = []
    # state['pull_number'] = 0
    # state['git_read_result'] = {}
    # state['llm_review_result'] = {}
    # state['jira_ticket_details'] = {}
    # state['diff'] = {}
    # state['jira_ticket'] = []  
    state['comments'] = None
    state['test_suggetions'] = []
    return state

    
def llm_review_analyze_code_agent_node(state: LLMReviewAgentState) -> LLMReviewAgentState:
    """Analyze code diffs with LLM"""
    print("\n[NODE 1] Analyzing code with LLM...")
    pretty_print_json_list(state)
    
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    full_prompt = create_analysis_prompt(state["diffs"])
    
    response = model.generate_content(full_prompt)
    response_text = response.text.strip()
    
    # DEBUG: Print raw LLM response
    print(f"\n[DEBUG] LLM Raw Response:\n{response_text[:500]}...\n")
    
    # Parse JSON response
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    
    if json_match:
        try:
            analysis = json.loads(json_match.group(0))
            state["llm_analysis"] = analysis
            
            # DEBUG: Print parsed analysis
            print(f"[DEBUG] Parsed Analysis:")
            print(f"  Bugs: {len(analysis.get('bugs', []))}")
            print(f"  Quality Issues: {len(analysis.get('code_quality_issues', []))}")
            print(f"  Security Issues: {len(analysis.get('security_issues', []))}")
            print(f"  Summary: {analysis.get('summary', 'N/A')[:100]}...")
            
            print(f"\n✅ Analysis complete - {len(analysis.get('bugs', []))} bugs found")
        except json.JSONDecodeError:
            print("⚠️  Failed to parse LLM response as JSON")
            state["llm_analysis"] = {"bugs": [], "summary": response_text}
    else:
        print("⚠️  No JSON found in LLM response")
        state["llm_analysis"] = {"bugs": [], "summary": response_text}
    
    return state


def llm_review_genrate_review_agent_node(state: LLMReviewAgentState ):
    review_comments = "Comment1 comment2 commnet3"
    state['comments'] = review_comments
    # print(f"[LLM] In llm_review_genrate_review_agent_node -> state: {state}") 
    return state

def llm_review_identify_bug_agent_node(state: LLMReviewAgentState ):
    bugs = ['bug1','bug2','bug3']
    state['bugs'] = bugs
    # print(f"[LLM] In llm_review_identify_bug_agent_node -> state: {state}") 
    return state


def llm_review_suggest_test_agent_node(state: LLMReviewAgentState ):
    test_suggetions = ['test1','test2','test3']
    state['test_suggetions'] = test_suggetions
    # print(f"[LLM] In llm_review_suggest_test_agent_node -> state: {state}") 
    return state


def graph_Builder():
    llm_review_graph = StateGraph(LLMReviewAgentState)

    llm_review_graph.add_node("LLM_INIT", llm_review_analyze_init_node)
    llm_review_graph.add_node("ANALYZE_CODE", llm_review_analyze_code_agent_node)
    llm_review_graph.add_node("GENERATE_REVIEW", llm_review_genrate_review_agent_node)
    llm_review_graph.add_node("IDENTIFY_BUG", llm_review_identify_bug_agent_node)
    llm_review_graph.add_node("SUGGEST_TEST", llm_review_suggest_test_agent_node)

    llm_review_graph.add_edge(START, "LLM_INIT")
    llm_review_graph.add_edge("LLM_INIT", "ANALYZE_CODE")
    llm_review_graph.add_edge("ANALYZE_CODE", "GENERATE_REVIEW")
    llm_review_graph.add_edge("GENERATE_REVIEW", "IDENTIFY_BUG")
    llm_review_graph.add_edge("IDENTIFY_BUG", "SUGGEST_TEST")
    llm_review_graph.add_edge("SUGGEST_TEST", END)

    graph = llm_review_graph.compile()
    save_graph_as_png(graph, __file__)
    return graph

llm_review_graph = graph_Builder()  

def main():
    #quotation = graph_Builder()   
    data = {'file_list' : ['b1.py','a1.py'],'difference':"Hello word"}
    llm_review_graph.invoke(data)

if __name__ == "__main__":
    main()

