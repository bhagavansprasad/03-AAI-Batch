"""
jira_utilities.py — Utility functions for Jira ticket creation
"""


def build_jira_ticket_summary(bug: dict) -> str:
    """
    Build Jira ticket summary from bug data.
    Returns a formatted summary string (description capped at 80 chars).
    """
    return f"[{bug['severity'].upper()}] {bug['type']}: {bug['description'][:80]}"


def build_jira_ticket_description(bug: dict, owner: str, repo: str, pull_number: int) -> str:
    """
    Build Jira ticket description from bug data and PR info.
    Returns a formatted markdown description for Jira.
    """
    return f"""**Bug found in PR #{pull_number}**

**Repository:** {owner}/{repo}
**Severity:** {bug['severity']}
**Type:** {bug['type']}
**Location:** {bug['location']}

**Description:**
{bug['description']}

**Suggestion:**
{bug['suggestion']}

**PR Link:** https://github.com/{owner}/{repo}/pull/{pull_number}
"""


def get_jira_priority(severity: str) -> str:
    """
    Map bug severity to Jira priority level.
    Falls back to 'Medium' for unknown severities.
    """
    priority_map = {
        "high":     "High",
        "medium":   "Medium",
        "low":      "Low",
        "critical": "Highest",
    }
    return priority_map.get(severity.lower(), "Medium")
