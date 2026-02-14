# ReviewerAgent - Architecture Diagram

## High-Level Architecture

```mermaid
graph TB
    Start([Start: PR #X]) --> Orchestrator[Orchestrator]
    
    Orchestrator --> GitRead[Git Agent - READ]
    GitRead --> LLMReview[LLM Review Agent]
    LLMReview --> Jira[Jira Agent]
    Jira --> GitWrite[Git Agent - WRITE]
    GitWrite --> End([End: PR Updated])
    
    style Orchestrator fill:#ff9999,stroke:#333,stroke-width:4px
    style GitRead fill:#99ccff,stroke:#333,stroke-width:2px
    style LLMReview fill:#99ff99,stroke:#333,stroke-width:2px
    style Jira fill:#ffcc99,stroke:#333,stroke-width:2px
    style GitWrite fill:#99ccff,stroke:#333,stroke-width:2px
```

## Data Schema Flow

```mermaid
flowchart TD
    Input[Input Data] --> |owner, repo, pull_number| Orch{Orchestrator}
    
    Orch --> |owner, repo, pull_number| GitR[Git Agent READ]
    GitR --> |pr_details<br/>changed_files<br/>diffs| Orch
    
    Orch --> |owner, repo, pull_number<br/>diffs| LLM[LLM Review Agent]
    LLM --> |review_comments<br/>bugs_found<br/>test_suggestions| Orch
    
    Orch --> |owner, repo, pull_number<br/>bugs| JiraA[Jira Agent]
    JiraA --> |tickets_created| Orch
    
    Orch --> |owner, repo, pull_number<br/>review_comments<br/>unit_tests<br/>jira_id| GitW[Git Agent WRITE]
    GitW --> |comments_posted<br/>commits_made<br/>tags_added| Orch
    
    Orch --> Output[Final State]
    
    style Orch fill:#ff9999,stroke:#333,stroke-width:3px
    style GitR fill:#99ccff,stroke:#333,stroke-width:2px
    style LLM fill:#99ff99,stroke:#333,stroke-width:2px
    style JiraA fill:#ffcc99,stroke:#333,stroke-width:2px
    style GitW fill:#99ccff,stroke:#333,stroke-width:2px
```

## Component Interaction Map

```mermaid
graph TB
    subgraph External["External Systems"]
        GitHub[GitHub API<br/>via MCP]
        Gemini[Google Gemini<br/>LLM API]
        Jira[Jira API<br/>via MCP]
        Github[GitHub API<br/>via MCP]
    end
    
    subgraph Agents["Agent Layer"]
        GitAgent[Git Agent]
        LLMAgent[LLM Review Agent]
        JiraAgent[Jira Agent]
        Gitagent[Git Agent]
    end
    
    subgraph Orchestration["Orchestration Layer"]
        Orchestrator[Orchestrator<br/>LangGraph]
    end
    
    Orchestrator --> GitAgent
    Orchestrator --> LLMAgent
    Orchestrator --> JiraAgent
    Orchestrator --> Gitagent
    
    GitAgent <--> GitHub
    LLMAgent <--> Gemini
    JiraAgent <--> Jira
    Gitagent <--> Github
    
    style Orchestrator fill:#ff9999,stroke:#333,stroke-width:4px
    style GitAgent fill:#99ccff,stroke:#333,stroke-width:2px
    style LLMAgent fill:#99ff99,stroke:#333,stroke-width:2px
    style JiraAgent fill:#ffcc99,stroke:#333,stroke-width:2px
```

## State Management

```mermaid
stateDiagram-v2
    [*] --> OrchestratorInit: Start
    
    OrchestratorInit --> GitRead: Initialize State
    
    state GitRead {
        [*] --> ConnectMCP
        ConnectMCP --> FetchPR
        FetchPR --> FetchFiles
        FetchFiles --> ExtractDiffs
        ExtractDiffs --> [*]
    }
    
    GitRead --> LLMReview: Pass Diffs
    
    state LLMReview {
        [*] --> AnalyzeCode
        AnalyzeCode --> GenerateReview
        GenerateReview --> IdentifyBugs
        IdentifyBugs --> SuggestTests
        SuggestTests --> [*]
    }
    
    LLMReview --> JiraTickets: Pass Bugs
    
    state JiraTickets {
        [*] --> ConnectJira
        ConnectJira --> CreateTickets
        CreateTickets --> [*]
    }
    
    JiraTickets --> GitWrite: Pass Ticket IDs
    
    state GitWrite {
        [*] --> PostComments
        PostComments --> CommitTests
        CommitTests --> TagPR
        TagPR --> [*]
    }
    
    GitWrite --> [*]: Complete
```

## Legend

- **Red** = Orchestrator (Main coordinator)
- **Blue** = Git Agent (GitHub integration)
- **Green** = LLM Review Agent (AI analysis)
- **Orange** = Jira Agent (Ticket management)

## Key Data Structures

### OrchestratorState
```
{
  owner: str
  repo: str
  pull_number: int
  git_read_result: {pr_details, changed_files, diffs}
  llm_review_result: {comments, tests, bugs}
  jira_result: {tickets_created}
  git_write_result: {comments_posted, commits_made, tags_added}
}
```

### GitAgentState
```
{
  owner, repo, pull_number
  client: MCP Client
  pr_details, changed_files, diffs  (READ)
  review_comments, unit_tests, jira_id  (WRITE)
  comments_posted, commits_made, tags_added  (OUTPUT)
}
```

### LLMReviewAgentState
```
{
  owner, repo, pull_number
  diffs  (INPUT)
  llm_analysis
  review_comments, bugs_found, test_suggestions  (OUTPUT)
}
```

### JiraAgentState
```
{
  owner, repo, pull_number
  bugs  (INPUT)
  jira_client
  tickets_created  (OUTPUT)
}
```