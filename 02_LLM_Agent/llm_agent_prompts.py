"""
Prompts and instructions for LLM Review Agent
"""

# ============================================================================
# CODE ANALYSIS PROMPTS
# ============================================================================

CODE_ANALYSIS_SYSTEM_INSTRUCTION = """You are an expert code reviewer. Analyze the provided code diff and identify:
1. Potential bugs or issues
2. Code quality problems
3. Security vulnerabilities
4. Performance issues
5. Best practice violations

Respond ONLY with valid JSON in this exact format:
{
    "bugs": [
        {
            "severity": "high/medium/low",
            "type": "bug_type",
            "description": "what's wrong",
            "location": "filename:line",
            "suggestion": "how to fix"
        }
    ],
    "code_quality_issues": ["issue1", "issue2"],
    "security_issues": ["issue1", "issue2"],
    "summary": "overall assessment"
}

DO NOT include any text outside the JSON structure."""


def format_diffs_for_analysis(diffs: list) -> str:
    """Format diffs into text for LLM analysis"""
    diffs_text = ""
    for diff in diffs:
        diffs_text += f"\n\n=== File: {diff['filename']} ===\n"
        diffs_text += f"Language: {diff['language']}\n"
        diffs_text += f"Changes: +{diff['additions']}/-{diff['deletions']}\n"
        diffs_text += f"\nDiff:\n{diff['patch'][:2000]}\n"  # Limit to 2000 chars
    return diffs_text


def create_analysis_prompt(diffs: list) -> str:
    """Create full analysis prompt"""
    diffs_text = format_diffs_for_analysis(diffs)
    return f"{CODE_ANALYSIS_SYSTEM_INSTRUCTION}\n\nAnalyze this code change:\n{diffs_text}"


# ============================================================================
# REVIEW COMMENT GENERATION PROMPTS
# ============================================================================

REVIEW_COMMENT_TEMPLATE = """Generate a professional PR review comment based on this analysis:

{analysis}

Format as markdown for GitHub PR comments."""


# ============================================================================
# TEST GENERATION PROMPTS
# ============================================================================

TEST_GENERATION_PROMPT = """Based on the code changes and identified issues, generate unit tests.

Code changes:
{diffs}

Issues found:
{bugs}

Generate comprehensive unit tests covering:
1. Happy path scenarios
2. Edge cases
3. Error handling
4. Bug fixes

Return only the test code, no explanations."""

# ============================================================================
# REVIEW COMMENT GENERATION PROMPTS
# ============================================================================

REVIEW_COMMENT_GENERATION_PROMPT = """Based on the code analysis, generate a structured review comment.

Analysis:
{analysis}

Respond ONLY with valid JSON in this format:
{{
    "summary": "Brief overall assessment",
    "bugs": [
        {{
            "severity": "high/medium/low",
            "title": "Bug title",
            "description": "What's wrong",
            "suggestion": "How to fix"
        }}
    ],
    "quality_issues": ["issue1", "issue2"],
    "security_issues": ["issue1", "issue2"],
    "positive_feedback": ["good point 1", "good point 2"]
}}

DO NOT include markdown or any text outside JSON."""


# ============================================================================
# TEST GENERATION PROMPTS
# ============================================================================

TEST_GENERATION_STRUCTURED_PROMPT = """Generate unit tests for the identified bugs.

Code changes:
{diffs}

Bugs found:
{bugs}

Respond ONLY with valid JSON in this format:
{{
    "test_framework": "pytest/unittest",
    "test_cases": [
        {{
            "test_name": "test_function_name",
            "description": "What this test validates",
            "test_code": "Complete test function code",
            "covers_bug": "bug_type"
        }}
    ]
}}

DO NOT include markdown or explanations outside JSON."""